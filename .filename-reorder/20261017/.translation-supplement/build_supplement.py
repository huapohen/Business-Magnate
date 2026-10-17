"""Render checked source-aligned supplemental translations without touching old outputs."""
from pathlib import Path
import hashlib
import json
import re

WORK = Path(__file__).resolve().parent
OUT = WORK.parent
config = json.loads((WORK / 'config.json').read_text())
sources = {}
for key, book in config['books'].items():
    data = (WORK / book['source_file']).read_bytes()
    assert hashlib.sha256(data).hexdigest() == book['sha256'], key
    sources[key] = data.decode('utf-8').splitlines()


def clean(text):
    for token in config['source_cleanup_tokens']:
        text = text.replace(token, '')
    return text


all_parts, outputs, adaptations = [], [], []
for part in config['parts']:
    number = part['number']
    tsv = WORK / f'part_{number:03}.tsv'
    notes = WORK / f'part_{number:03}_notes.txt'
    if not tsv.exists() or not notes.exists():
        continue
    book = config['books'][part['book']]
    lines = sources[part['book']]
    headings = {n for n, title in book['chapters']}
    opath = WORK / f'part_{number:03}_safety_overrides.json'
    overrides = json.loads(opath.read_text()) if opath.exists() else {}
    used, coverage, records = set(), [], []
    for row in tsv.read_text().splitlines():
        if not row.strip():
            continue
        span, en = row.split('\t', 1)
        assert re.fullmatch(r'\d+(?:-\d+)?', span), (number, span)
        ns = list(map(int, span.split('-')))
        first, last = ns[0], ns[-1]
        assert part['start_line'] <= first <= last <= part['end_line'], (number, span)
        included = [n for n in range(first, last + 1) if lines[n - 1].strip()]
        assert included, (number, span)
        assert not any(n in headings for n in included[1:]), (number, span)
        heading = first in headings
        if heading:
            assert first == last, (number, span)
        coverage.extend(included)
        raw = ''.join(lines[n - 1].strip() for n in included)
        zh = clean(raw)
        assert en.strip() and not re.search(r'[\u3400-\u9fff]', en), (number, span)
        override = overrides.get(span)
        if override:
            assert override.get('zh', '').strip() and override.get('reason', '').strip()
            zh = override['zh'].strip()
            used.add(span)
            adaptations.append({'part': number, 'span': span, 'reason': override['reason']})
        records.append({'source_span': span, 'source_start_line': first, 'source_end_line': last,
                        'is_heading': heading, 'zh': zh, 'en': en.strip(),
                        'source_sha256': hashlib.sha256(raw.encode()).hexdigest(),
                        'source_cleanup_applied': raw != clean(raw), 'adapted': bool(override)})
    expected = [n for n in range(part['start_line'], part['end_line'] + 1) if lines[n - 1].strip()]
    assert coverage == expected, ('missing or duplicate source lines', number)
    assert used == set(overrides), ('unmatched safety overrides', number)
    title_en = book['english_title']
    en_blocks = ['HU XUEYAN\nBy Gao Yang', title_en,
                 f"Chapter {part['chapter']} — Part {part['part_in_chapter']} of {part['parts_in_chapter']}"]
    zh_blocks = ['胡雪岩｜中英对照版\n原著：高阳', book['title'] + '｜' + title_en,
                 f"{part['chapter_heading']}（本章第{part['part_in_chapter']}部分，共{part['parts_in_chapter']}部分）",
                 '阅读说明：每段中文后接对应英文；两版英文正文一致。下载站水印已清除，原始疑字在文末说明。']
    if overrides:
        en_blocks.append('Adaptation note: sexualized passages involving minors are presented as non-graphic narrative summaries. These passages are adapted, not translated in full detail.')
        zh_blocks.append('改写说明：涉及未成年人物的性描写已在两版中作非露骨改写，保留安全情节信息，具体范围见文末说明。')
    for record in records:
        en_blocks.append(record['en'])
        if record['is_heading']:
            zh_blocks.append(record['zh'] + '｜' + record['en'])
        else:
            zh_blocks.append(record['zh'] + '\n\n' + record['en'])
    zh_blocks.append('译者说明与学习提示（不属于小说正文）\n\n' + notes.read_text().strip())
    en_text, zh_text = '\n\n'.join(en_blocks) + '\n', '\n\n'.join(zh_blocks) + '\n'
    forbidden = r'\[(?:B\d+-)?P\d+\]|中文：|English:'
    assert not re.search(forbidden, en_text + zh_text), number
    assert not re.search(r'[\u3400-\u9fff]', en_text), number
    en_cursor = zh_cursor = 0
    for record in records:
        needle = '\n\n' + record['en'] + '\n'
        pos = en_text.find(needle, en_cursor)
        assert pos >= 0, (number, record['source_span'])
        en_cursor = pos + len(needle) - 1
        needle = ('\n\n' + record['zh'] + ('｜' if record['is_heading'] else '\n\n') + record['en'] + '\n')
        pos = zh_text.find(needle, zh_cursor)
        assert pos >= 0, (number, record['source_span'])
        zh_cursor = pos + len(needle) - 1
    for suffix, text in [('_纯英文.txt', en_text), ('_中英对照.txt', zh_text)]:
        target = OUT / (part['file_stem'] + suffix)
        target.write_text(text)
        outputs.append(str(target))
    (WORK / f'part_{number:03}_alignment.json').write_text(json.dumps(records, ensure_ascii=False, indent=2) + '\n')
    all_parts.append({'number': number, 'book': part['book'], 'chapter': part['chapter'],
                      'source_lines': [part['start_line'], part['end_line']],
                      'source_characters': part['characters'], 'reading_paragraphs': sum(not r['is_heading'] for r in records),
                      'english_words': sum(len(re.findall(r"[A-Za-z]+(?:['’\u2010-][A-Za-z]+)*", r['en'])) for r in records)})

done = {p['number'] for p in all_parts}
full = len(all_parts) == len(config['parts'])
manifest = {'status': 'complete' if full else 'in_progress', 'completed_parts': sorted(done),
            'remaining_parts': [p['number'] for p in config['parts'] if p['number'] not in done],
            'total_parts': len(config['parts']), 'parts': all_parts, 'outputs': outputs,
            'source_character_coverage_percent': round(100 * sum(p['source_characters'] for p in all_parts) / sum(p['characters'] for p in config['parts']), 3),
            'non_graphic_adaptations': adaptations,
            'checks_passed': ['Source hashes unchanged', 'Every nonempty line covered exactly once within each completed part',
                              'English text identical in both editions', 'No visible paragraph IDs or language labels',
                              'English-only outputs contain no CJK', 'Source text preserved apart from documented watermark cleanup and safety adaptations']}
(WORK / 'progress.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'completed_parts': sorted(done), 'total_parts': len(config['parts']),
                  'coverage_percent': manifest['source_character_coverage_percent'],
                  'outputs': len(outputs)}, ensure_ascii=False))
