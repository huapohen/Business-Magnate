"""Combine only fully finished supplemental books, then rebuild the five-part text.

Run build_supplement.py first. This command refuses incomplete supplements.
Old source/alignment data remain untouched and retain their original line numbering.
"""
from pathlib import Path
import hashlib
import json
import re

WORK = Path(__file__).resolve().parent
OUT = WORK.parent
OLD = OUT / '.translation'
config = json.loads((WORK / 'config.json').read_text())
progress = json.loads((WORK / 'progress.json').read_text())
assert progress['status'] == 'complete'
assert progress['completed_parts'] == [p['number'] for p in config['parts']]
assert not progress['remaining_parts']
old_config = json.loads((OLD / 'book_config.json').read_text())
groups = json.loads((OLD / 'paragraph_groups.json').read_text())
old_source = (OUT.parent / 'input/胡雪岩.txt').read_bytes()
assert hashlib.sha256(old_source).hexdigest() == old_config['source_sha256']
old_lines = old_source.decode().splitlines()

records_by_part, old_coverage = {}, []
for part in old_config['parts']:
    num = part['number']
    records = json.loads((OLD / f'part_{num:03}_alignment.json').read_text())
    for r in records:
        a, b = r['source_start_line'], r['source_end_line']
        old_coverage.extend(n for n in range(a, b + 1) if old_lines[n - 1].strip())
        if 'adaptation' not in r:
            source_text = ''.join(old_lines[n - 1].strip() for n in range(a, b + 1) if old_lines[n - 1].strip())
            assert r['source_heading_prefix'] + r['zh'] == source_text
    bundled, pending = [], []
    for r in records:
        pending.append(r)
        if r['source_end_line'] in groups[str(num)]:
            first = pending[0]
            section = old_config['sections'].get(str(first['source_start_line']))
            if section:
                bundled.append({'zh': section['zh'], 'en': section['en'], 'heading': True})
            bundled.append({'zh': ''.join(x['zh'] for x in pending), 'en': ' '.join(x['en'] for x in pending),
                            'heading': False, 'adapted': any('adaptation' in x for x in pending)})
            pending = []
    assert not pending
    records_by_part[num] = bundled
assert old_coverage == [n for n, line in enumerate(old_lines, 1) if line.strip()]

for part in config['parts']:
    n = part['number']
    source_file = WORK / config['books'][part['book']]['source_file']
    assert hashlib.sha256(source_file.read_bytes()).hexdigest() == config['books'][part['book']]['sha256']
    rs = json.loads((WORK / f'part_{n:03}_alignment.json').read_text())
    records_by_part[n] = [{'zh': r['zh'], 'en': r['en'], 'heading': r['is_heading'], 'adapted': r['adapted']} for r in rs]


def render_pair(stem, english_title, chinese_title, numbers, with_old=False):
    items = []
    en = ['HU XUEYAN\nBy Gao Yang', english_title]
    zh = ['胡雪岩｜中英对照版\n原著：高阳', chinese_title + '｜' + english_title,
          '阅读说明：按完整语义段落排列，每段中文后接同一段英文；两版英文正文一致。下载站水印与少量疑字的处理见各批说明。',
          '本书是中文小说的英文译读材料。阅读、完形、段落衔接、翻译与表达积累的学习提示另列在文末，不混入小说正文。']
    if with_old:
        en.append('This edition combines translations of all five parts present in the supplied files. It is not a certification that the source texts are free of omissions or transcription errors.')
        zh.append('本版合并所提供文件中的五部文本。原文两稿同源且有错字、缺失章号，译完所提供正文不等于已与出版物逐字校勘。')
    adapted = any(r.get('adapted') for n in numbers for r in records_by_part[n])
    if adapted:
        en.append('Adaptation note: sexualized passages involving minors are rendered as non-graphic narrative summaries in both editions. The affected passages are documented in the translator’s notes.')
        zh.append('改写说明：涉及未成年人物的性描写在两版中作非露骨改写；这些段落不是未经改动的原文或逐字全译，范围见文末说明。')
    volume_headers = {1: ('平步青云（上）', 'A Swift Rise to Prominence — Volume I'),
                      18: ('平步青云（中）', 'A Swift Rise to Prominence — Volume II'),
                      39: ('平步青云（下）', 'A Swift Rise to Prominence — Volume III'),
                      103: ('红顶商人', 'The Red-Topped Merchant'),
                      64: ('灯火楼台', 'Towers of Light'),
                      152: ('萧瑟洋场', 'The Desolate Foreign Settlement'),
                      81: ('烟消云散', 'Vanishing into Thin Air')}
    for n in numbers:
        if with_old and n in volume_headers:
            z, e = volume_headers[n]
            en.append(e)
            zh.append(z + '｜' + e)
        for r in records_by_part[n]:
            en.append(r['en'])
            zh.append(r['zh'] + ('｜' if r['heading'] else '\n\n') + r['en'])
            items.append(r)
    en.append('END OF THE SUPPLIED TEXT')
    zh.append('所提供正文结束')
    zh.append('译者说明与学习提示（以下不属于小说原文）')
    for n in numbers:
        folder = OLD if n <= 102 else WORK
        part = next(p for p in (old_config['parts'] if n <= 102 else config['parts']) if p['number'] == n)
        zh.append(part['file_stem'] + '\n\n' + (folder / f'part_{n:03}_notes.txt').read_text().strip())
    english, bilingual = '\n\n'.join(en) + '\n', '\n\n'.join(zh) + '\n'
    assert not re.search(r'[\u3400-\u9fff]', english)
    assert not re.search(r'\[(?:B\d+-)?P\d+\]|中文：|English:', english + bilingual)
    ec = zc = 0
    for r in items:
        needle = '\n\n' + r['en'] + '\n'
        ep = english.find(needle, ec)
        assert ep >= 0
        ec = ep + len(needle) - 1
        needle = '\n\n' + r['zh'] + ('｜' if r['heading'] else '\n\n') + r['en'] + '\n'
        zp = bilingual.find(needle, zc)
        assert zp >= 0
        zc = zp + len(needle) - 1
    result = []
    for suffix, text in [('_纯英文.txt', english), ('_中英对照.txt', bilingual)]:
        p = OUT / (stem + suffix)
        p.write_text(text)
        result.append({'path': str(p), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()})
    return result


outputs = []
for key in ['red', 'desolate']:
    ns = [p['number'] for p in config['parts'] if p['book'] == key]
    book = config['books'][key]
    outputs.extend(render_pair(f"{ns[0]:03}_{book['title']}_完整本", book['english_title'], book['title'], ns))
order = list(range(1, 64)) + list(range(103, 152)) + list(range(64, 81)) + list(range(152, 179)) + list(range(81, 103))
assert len(order) == len(set(order)) == 178
outputs.extend(render_pair('胡雪岩', 'The Five-Part Supplied Text', '五部所提供文本合并版', order, with_old=True))
(WORK / 'combined_audit.json').write_text(json.dumps({'status': 'complete', 'story_order': order, 'outputs': outputs,
    'old_source_coverage_verified': True, 'bilingual_english_identity_verified': True,
    'source_completeness_limitations_disclosed': True}, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'complete_combined_outputs': outputs}, ensure_ascii=False))
