"""Render verified, contiguous translations into two editions and individual installments."""
from pathlib import Path
import hashlib
import json
import re

WORK = Path(__file__).resolve().parent
OUT = WORK.parent
SOURCE = OUT.parent / 'input' / '胡雪岩.txt'
config = json.loads((WORK / 'book_config.json').read_text())
raw = SOURCE.read_bytes()
source = raw.decode('utf-8')
lines = source.splitlines()
assert hashlib.sha256(raw).hexdigest() == config['source_sha256'], 'Source changed; reconcile before rendering.'
parts = sorted(config['parts'], key=lambda p: p['number'])
assert [p['number'] for p in parts] == list(range(1, len(parts) + 1))
assert parts[0]['start_line'] == 1
for previous, current in zip(parts, parts[1:]):
    assert previous['end_line'] + 1 == current['start_line'], 'Gap or overlap between installments.'

all_records = []
all_covered = []
per_part = []
for part in parts:
    number = part['number']
    records = []
    covered = []
    override_path = WORK / f'part_{number:03}_safety_overrides.json'
    overrides = json.loads(override_path.read_text()) if override_path.exists() else {}
    used_overrides = set()
    tsv = WORK / f'part_{number:03}.tsv'
    for index, row in enumerate(tsv.read_text().splitlines(), 1):
        span, english = row.split('\t', 1)
        limits = [int(n) for n in span.split('-')]
        a, b = limits[0], limits[-1]
        assert part['start_line'] <= a <= b <= part['end_line']
        nonempty = [n for n in range(a, b + 1) if lines[n - 1].strip()]
        assert nonempty
        covered.extend(nonempty)
        chinese = ''.join(lines[n - 1].strip() for n in nonempty)
        section = config['sections'].get(str(a))
        prefix = section['prefix'] if section else ''
        if prefix:
            assert chinese.startswith(prefix)
            chinese = chinese[len(prefix):]
        source_digest = hashlib.sha256(chinese.encode('utf-8')).hexdigest()
        adaptation = overrides.get(span)
        if adaptation:
            assert isinstance(adaptation.get('zh'), str) and adaptation['zh'].strip(), span
            assert isinstance(adaptation.get('reason'), str) and adaptation['reason'].strip(), span
            chinese = adaptation['zh'].strip()
            used_overrides.add(span)
        assert english.strip() and not re.search(r'[\u3400-\u9fff]', english)
        record = {'id': f'P{index:03}', 'global_id': f'B{number:03}-P{index:03}',
                  'part': number, 'source_start_line': a, 'source_end_line': b,
                  'source_heading_prefix': prefix, 'zh': chinese, 'en': english}
        if adaptation:
            record['adaptation'] = {'type': 'non_graphic', 'reason': adaptation['reason'],
                                    'source_text_sha256': source_digest}
        records.append(record)
    expected = [n for n in range(part['start_line'], part['end_line'] + 1) if lines[n - 1].strip()]
    assert covered == expected, f'Coverage mismatch in part {number}'
    assert used_overrides == set(overrides), f'Unmatched adaptation ranges in part {number}'
    all_covered.extend(covered)
    all_records.extend(records)
    per_part.append((part, records))

end = parts[-1]['end_line']
full = end == len(lines)
expected_all = [n for n in range(1, end + 1) if lines[n - 1].strip()]
assert all_covered == expected_all

english_intro = 'HU XUEYAN\nBy Gao Yang\nEnglish Translation'
chinese_intro = '胡雪岩｜中英对照版\n原著：高阳\nHU XUEYAN — BILINGUAL EDITION'
status_en = ('Translation of the complete supplied text.' if full else
             'TRANSLATION IN PROGRESS\nCurrently translated through ' + config['current_end_en'] + '. The rest of the novel has not yet been translated.')
status_zh = ('所提供原文已全部译完。' if full else
             '【全书翻译进行中】\n目前译至' + config['current_end_zh'] + '。以下是已完成部分，不是全书完成版。')
common_note_zh = ('阅读说明：按完整语义段落组织，每段中文之后紧接对应英文；连续短对话及相关叙述合并阅读。正文不加段落编号或语言标签。中文用字保留，疑似识别错误见译者说明。两版英文内容完全一致。')
adaptation_note_zh = ('改写说明：涉及未成年人物的性描写已在中英两版中作非露骨改写，保留安全的情节信息；这些段落不能视为未经改动的原文或逐字全译，具体范围见文末译者说明。')
adaptation_note_en = ('Adaptation note: sexualized passages involving a minor have been rendered as non-graphic narrative summaries in both editions. These passages are adapted rather than translated in full detail; their locations are documented in the bilingual edition.')

def has_adaptations(records):
    return any('adaptation' in record for record in records)

def reading_note(records):
    if has_adaptations(records):
        return common_note_zh.replace('中文用字保留，', '除下述改写范围外，中文用字保留，')
    return common_note_zh

group_config = json.loads((WORK / 'paragraph_groups.json').read_text())

def paragraph_groups(records):
    groups = []
    pending = []
    for record in records:
        ends = group_config.get(str(record['part']))
        assert ends is not None, f"Missing reviewed paragraph boundaries for part {record['part']}"
        if pending:
            assert pending[0]['part'] == record['part'], 'Paragraph crosses installment boundary'
            assert str(record['source_start_line']) not in config['sections'], 'Paragraph crosses a chapter heading'
        pending.append(record)
        if record['source_end_line'] in ends:
            groups.append(pending)
            pending = []
    assert not pending, 'Unclosed final paragraph'
    assert [r['global_id'] for group in groups for r in group] == [r['global_id'] for r in records]
    for number in {r['part'] for r in records}:
        found = [group[-1]['source_end_line'] for group in groups if group[0]['part'] == number]
        assert found == group_config[str(number)], f'Invalid paragraph boundary in part {number}'
    return groups

def paragraph_text(group):
    return ''.join(r['zh'] for r in group), ' '.join(r['en'] for r in group)

def add_records(en_parts, zh_parts, records, combined=False):
    for group in paragraph_groups(records):
        first = group[0]
        section = config['sections'].get(str(first['source_start_line']))
        if section:
            en_parts.append(section['en'])
            zh_parts.append(section['zh'] + '｜' + section['en'])
        chinese, english = paragraph_text(group)
        en_parts.append(english)
        zh_parts.append(chinese + '\n\n' + english)

def save_pair(en_path, zh_path, en_parts, zh_parts, records, combined=False):
    en_path.write_text('\n\n'.join(en_parts) + '\n', encoding='utf-8')
    zh_path.write_text('\n\n'.join(zh_parts) + '\n', encoding='utf-8')
    en = en_path.read_text()
    zh = zh_path.read_text()
    assert not re.search(r'[\u3400-\u9fff]', en)
    forbidden = r'\[(?:B\d+-)?P\d+\]|中文：|English:'
    assert not re.search(forbidden, en + zh), 'Visible alignment markers or language labels remain'
    en_cursor = zh_cursor = 0
    for group in paragraph_groups(records):
        chinese, english = paragraph_text(group)
        en_needle = '\n\n' + english + '\n'
        zh_needle = '\n\n' + chinese + '\n\n' + english + '\n'
        en_pos = en.find(en_needle, en_cursor)
        zh_pos = zh.find(zh_needle, zh_cursor)
        assert en_pos >= 0 and zh_pos >= 0, group[0]['global_id']
        en_cursor = en_pos + len(en_needle) - 1
        zh_cursor = zh_pos + len(zh_needle) - 1
    for record in records:
        original = ''.join(line.strip() for line in lines[record['source_start_line']-1:record['source_end_line']] if line.strip())
        if 'adaptation' in record:
            prefix = record['source_heading_prefix']
            normalized = original[len(prefix):] if prefix else original
            assert hashlib.sha256(normalized.encode('utf-8')).hexdigest() == record['adaptation']['source_text_sha256']
            override_path = WORK / f"part_{record['part']:03}_safety_overrides.json"
            span = str(record['source_start_line'])
            if record['source_end_line'] != record['source_start_line']:
                span += '-' + str(record['source_end_line'])
            approved = json.loads(override_path.read_text())[span]
            assert record['zh'] == approved['zh'].strip()
        else:
            assert record['source_heading_prefix'] + record['zh'] == original

output_files = []
for part, records in per_part:
    number = part['number']
    notes = (WORK / f'part_{number:03}_notes.txt').read_text()
    en_parts = [english_intro, f"INSTALLMENT {number:03}\n" + part['title_en'],
                'This installment is part of an ongoing translation. Paragraphs correspond to those in the bilingual edition.']
    zh_parts = [chinese_intro, f"第{number:03}批：" + part['title_zh'],
                f"原文范围：第{part['start_line']}—{part['end_line']}行（含空行）。本文件仅含这一批，不是全书译完版。", reading_note(records)]
    if has_adaptations(records):
        en_parts.append(adaptation_note_en)
        zh_parts.append(adaptation_note_zh)
    add_records(en_parts, zh_parts, records)
    en_parts.append(f'END OF INSTALLMENT {number:03}')
    zh_parts.append(f'本批正文结束｜END OF INSTALLMENT {number:03}')
    zh_parts.append(notes.strip())
    en_path = OUT / (part['file_stem'] + '_纯英文.txt')
    zh_path = OUT / (part['file_stem'] + '_中英对照.txt')
    save_pair(en_path, zh_path, en_parts, zh_parts, records)
    (WORK / f'part_{number:03}_alignment.json').write_text(json.dumps(records, ensure_ascii=False, indent=2) + '\n')
    output_files.extend([str(en_path), str(zh_path)])

combined_en = [english_intro, status_en,
               'The translation follows the supplied Chinese text. Paragraphs correspond to those in the bilingual edition.']
combined_zh = [chinese_intro, status_zh, reading_note(all_records),
               '本书是中文小说的英文译读材料，不是原生英语名著。阅读、完形、段落衔接、翻译与表达积累的提示另列在文末，不混入小说正文。']
if has_adaptations(all_records):
    combined_en.append(adaptation_note_en)
    combined_zh.append(adaptation_note_zh)
add_records(combined_en, combined_zh, all_records, combined=True)
combined_en.append('END OF THE SUPPLIED TEXT' if full else 'END OF THE TRANSLATION COMPLETED SO FAR\nThe novel continues beyond this point.')
combined_zh.append('全书正文结束' if full else '【已完成译文到此结束，原书下文尚待续译】')
combined_zh.append('各批文本说明与学习提示（以下均为译者说明，不属于小说原文）')
for part, records in per_part:
    combined_zh.append(f"第{part['number']:03}批：{part['title_zh']}\n\n" + (WORK / f"part_{part['number']:03}_notes.txt").read_text().strip())
combined_en_path = OUT / '胡雪岩_纯英文.txt'
combined_zh_path = OUT / '胡雪岩_中英对照.txt'
supplement_work = OUT / '.translation-supplement'
has_completed_supplement = (supplement_work / 'combined_audit.json').exists()
if not has_completed_supplement:
    save_pair(combined_en_path, combined_zh_path, combined_en, combined_zh, all_records, combined=True)
word_count = sum(len(re.findall(r"[A-Za-z]+(?:['’-][A-Za-z]+)*", record['en'])) for record in all_records)
completed_chars = sum(len(line) for line in source.splitlines(keepends=True)[:end])
manifest = {
    'source_file': str(SOURCE), 'source_sha256': hashlib.sha256(raw).hexdigest(),
    'source_total_characters': len(source), 'source_total_lines': len(lines),
    'source_total_nonempty_lines': sum(bool(line.strip()) for line in lines),
    'status': 'complete' if full else 'in_progress',
    'completed_part': len(parts), 'completed_source_lines_including_trailing_blank': [1, end],
    'completed_source_nonempty_lines': len(all_covered),
    'completed_source_characters_including_whitespace': completed_chars,
    'source_character_coverage_percent': round(100 * completed_chars / len(source), 3),
    'aligned_translation_units': len(all_records), 'reading_paragraph_pairs': len(paragraph_groups(all_records)), 'english_word_count_approx': word_count,
    'non_graphic_adapted_paragraphs': [{'part': r['part'], 'source_start_line': r['source_start_line'],
                                      'source_end_line': r['source_end_line'], 'reason': r['adaptation']['reason']}
                                     for r in all_records if 'adaptation' in r],
    'next_source_line': None if full else end + 1,
    'next_source_opening': None if full else lines[end].strip(),
    'combined_outputs': [str(combined_en_path), str(combined_zh_path)],
    'installment_outputs': output_files,
    'remaining_work': None if full else 'Translate the remaining source in order, maintain names and terminology, review the translation, and rebuild both complete editions.',
    'checks_passed': ['source SHA-256 unchanged', 'contiguous and exhaustive source coverage within translated range',
                      'Chinese source preserved after whitespace normalization and heading separation, except documented non-graphic adaptations',
                      'English-only edition contains no Chinese characters', 'identical English in both editions',
                      'reviewed semantic paragraphs cover all translation units in order', 'no visible paragraph identifiers or language labels']
}
(WORK / 'progress.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({k:manifest[k] for k in ['status','completed_part','completed_source_lines_including_trailing_blank',
    'source_character_coverage_percent','aligned_translation_units','reading_paragraph_pairs','english_word_count_approx','next_source_line','combined_outputs','checks_passed']},ensure_ascii=False,indent=2))

# Once the two missing books are integrated, rebuilding the old source must
# preserve the five-part combined editions. Each renderer validates its inputs.
if has_completed_supplement:
    import subprocess
    import sys
    for script in ('build_supplement.py', 'combine_complete.py'):
        subprocess.run([sys.executable, str(supplement_work / script)], check=True)
