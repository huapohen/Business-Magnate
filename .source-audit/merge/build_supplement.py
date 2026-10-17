from pathlib import Path
import hashlib
import json
import re
import unicodedata

BASE = Path(__file__).resolve().parents[3]
OLD = BASE / 'input/胡雪岩.txt'
NEW = BASE / 'input/《胡雪岩》(共五部).txt'
OUT = BASE / 'output/胡雪岩_中文补全版.txt'
AUDIT = BASE / 'output/.source-audit/merge'


def sha(b):
    return hashlib.sha256(b).hexdigest()


old_bytes, new_bytes = OLD.read_bytes(), NEW.read_bytes()
old, new = OLD.read_text(encoding='utf-8'), NEW.read_text(encoding='utf-8')
old_lines, new_lines = old.splitlines(keepends=True), new.splitlines(keepends=True)
assert len(old_lines) == 40928 and len(new_lines) == 46480
manifest = json.loads((AUDIT.parent / 'source_manifest.json').read_text())
assert sha(old_bytes) == manifest[OLD.name]['sha256']
assert sha(new_bytes) == manifest[NEW.name]['sha256']

changes = []


def new_book(title, start_line, end_line, chapter_count):
    source = ''.join(new_lines[start_line - 1:end_line])
    # The start is the first chapter, after the repeated download-site preamble.
    assert source.startswith('第一章')
    body, n_ads = re.subn(r'^更多精彩好书，更多原创手机电子书，请登陆请看小说网--Www\.qinkan\.net\s*$', '', source, flags=re.M)
    assert n_ads == 1
    pattern = r'－高阳－' + re.escape(title) + r'(第[一二三四五六七八九十]+章)'
    body, n_headings = re.subn(pattern, lambda m: '\n\n' + m.group(1) + '\n\n', body)
    assert n_headings == (1 if title == '红顶商人' else 6)
    n_markers = body.count('###')
    body = body.replace('###', '')
    watermarks = {}
    for token in ['[奇qinkan.net书]', 'www奇Qisuu书com网', '奇书-整理-提供下载', '16ks.com一路在线看书']:
        if token in body:
            watermarks[token] = body.count(token)
            body = body.replace(token, '')
    assert sum(watermarks.values()) == 7
    headings = re.findall(r'^第[一二三四五六七八九十]+章\s*$', body, flags=re.M)
    assert len(headings) == chapter_count
    body = re.sub(r'\n{3,}', '\n\n', body).strip() + '\n\n'
    result = '    胡雪岩全传——' + title + '\n\n' + body
    changes.append({'action': 'insert_book', 'title': title,
                    'source_file': str(NEW), 'source_lines': [start_line, end_line],
                    'chapter_headings': len(headings), 'chapter_headings_separated': n_headings,
                    'site_footer_removed': n_ads, 'hash_markers_removed': n_markers,
                    'embedded_watermarks_removed': watermarks,
                    'inserted_text_sha256': sha(result.encode()), 'inserted_characters': len(result)})
    return result


red = new_book('红顶商人', 26936, 31727, 11)
harbour = new_book('萧瑟洋场', 35140, 38007, 7)
inserts = {
    9279: '    胡雪岩全传——平步青云（中）\n\n',
    17695: '    胡雪岩全传——平步青云（下）\n\n',
    26916: '\n' + red,
    32482: '\n' + harbour,
}
assert old_lines[9278].lstrip().startswith('十二到新城')
assert old_lines[17694].lstrip().startswith('二十二当天')
assert old_lines[26915].strip() == '内容简介'
assert old_lines[32481].strip() == '胡雪岩全传──烟消云散'
changes += [{'action': 'insert_volume_heading', 'before_old_line': n, 'text': inserts[n].strip(),
             'basis': '联经新校版目录：中卷12–21章，下卷22–31章'} for n in [9279, 17695]]

# Only unequivocal single-character errors confirmed by the parallel source.
repairs = {353: ('精神夏', '精神复'), 1469: ('三有龄辩', '王有龄辩'), 3529: ('在五有龄当然', '在王有龄当然')}
dialogue = json.loads((AUDIT.parent / 'remaining/optional_dialogue_repair.json').read_text())
assert ''.join(old_lines[29270:29273]) == dialogue['expected_old']
corrected_dialogue_lines = dialogue['replacement'].splitlines(keepends=True)
assert len(corrected_dialogue_lines) == 3
line_repairs = {29271: corrected_dialogue_lines[0], 29273: corrected_dialogue_lines[2]}
changes.append({'action': 'restore_dialogue_order', 'old_lines': [29271, 29273],
                'basis_new_lines': [33204, 33206], 'before': dialogue['expected_old'], 'after': dialogue['replacement']})
pieces, spans = [], []
pos = 0
for line_number, original_line in enumerate(old_lines, 1):
    if line_number in inserts:
        addition = inserts[line_number]
        pieces.append(addition)
        spans.append({'type': 'insertion', 'before_old_line': line_number, 'start': pos, 'end': pos + len(addition)})
        pos += len(addition)
    line = line_repairs.get(line_number, original_line)
    if line_number in repairs:
        before, after = repairs[line_number]
        assert line.count(before) == 1
        line = line.replace(before, after)
        changes.append({'action': 'correct_character', 'old_line': line_number, 'before': before, 'after': after,
                        'basis': 'parallel text in the supplied new file'})
    pieces.append(line)
    spans.append({'type': 'old_line', 'old_line': line_number, 'start': pos, 'end': pos + len(line)})
    pos += len(line)
result = ''.join(pieces)

# Reverse the edits to prove that no original line has been deleted or reordered.
reconstructed = []
for span in spans:
    if span['type'] == 'old_line':
        line = result[span['start']:span['end']]
        if span['old_line'] in line_repairs:
            assert line == line_repairs[span['old_line']]
            line = old_lines[span['old_line'] - 1]
        if span['old_line'] in repairs:
            before, after = repairs[span['old_line']]
            assert line.count(after) == 1
            line = line.replace(after, before)
        reconstructed.append(line)
assert ''.join(reconstructed) == old
assert result.count(red) == 1 and result.count(harbour) == 1
assert OLD.read_bytes() == old_bytes and NEW.read_bytes() == new_bytes
OUT.write_bytes(result.encode('utf-8'))
assert OUT.read_bytes().decode('utf-8') == result

unresolved = []
for n, line in enumerate(result.splitlines(), 1):
    for i, c in enumerate(line):
        if unicodedata.category(c) == 'Co':
            unresolved.append({'output_line': n, 'code_point': f'U+{ord(c):04X}', 'context': line[max(0, i - 25):i + 35]})

audit = {'output_file': str(OUT), 'output_sha256': sha(OUT.read_bytes()),
         'source_sha256': {OLD.name: sha(old_bytes), NEW.name: sha(new_bytes)},
         'changes': changes, 'original_lines_preserved_and_reversible': True,
         'input_files_unchanged': True, 'unresolved_private_use_characters': unresolved,
         'limitations': ['No paper-edition collation; chapter 24 heading is absent from both supplied first-book texts.',
                         'Original OCR and punctuation differences were not comprehensively corrected.']}
(AUDIT / 'merge_audit.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2) + '\n')
(AUDIT / 'source_map.json').write_text(json.dumps(spans, ensure_ascii=False, separators=(',', ':')) + '\n')
print(json.dumps({'output': str(OUT), 'bytes': OUT.stat().st_size, 'changes': changes,
                  'original_preserved': True, 'unresolved_private_use_count': len(unresolved)}, ensure_ascii=False, indent=2))
