from pathlib import Path
import json
import re
import hashlib
import unicodedata

WORK = Path(__file__).resolve().parent
OUT = WORK.parent
ORIGINAL = OUT.parent / '.translation/part_001_alignment.json'
BILINGUAL = OUT.parent / '001_平步青云（上）_简介_楔子_第一章_中英对照.txt'
STEM = '001_平步青云（上）_简介_楔子_第一章'

def compact(s):
    return re.sub(r'\s+', '', s)

def content_chars(s):
    return ''.join(c for c in s if not c.isspace() and not unicodedata.category(c).startswith('P'))

def load_and_validate():
    originals = json.loads(ORIGINAL.read_text())
    existing_text = compact(BILINGUAL.read_text())
    for lang in ['zh', 'en']:
        position = 0
        for number, original in enumerate(originals, 1):
            fragment = compact(original[lang])
            start = existing_text.find(fragment, position)
            assert start >= 0, (number, lang, 'Not found in current bilingual edition')
            position = start + len(fragment)
    aligned = []
    for part in 'abc':
        aligned.extend(json.loads((WORK / f'aligned_{part}.json').read_text()))
    assert [x['paragraph_index'] for x in aligned] == list(range(1, len(originals) + 1))
    diagnostics = []
    for row, orig in zip(aligned, originals):
        i = row['paragraph_index']
        pairs = row['pairs']
        assert pairs, f'Empty paragraph {i}'
        for lang in ['zh', 'en']:
            assert compact(''.join(p['source_' + lang] for p in pairs)) == compact(orig[lang]), f'Source coverage mismatch {i} {lang}'
        for j, pair in enumerate(pairs):
            assert all(isinstance(pair[k], str) and pair[k].strip() for k in ['source_zh','source_en','zh','en']), (i, j, 'Empty string')
            for lang in ['zh','en']:
                assert pair[lang] == pair['source_' + lang].strip(), (i, j, lang, 'Text or punctuation changed')
            assert not re.search(r'\[P\d+\]|中文[：:]|English:', pair['zh']+'\n'+pair['en']), (i, j, 'Label')
            assert not re.search(r'[\u3400-\u9fff\ufffd\ue000-\uf8ff]', pair['en']), (i, j, 'Unexpected English character')
            if pair['en'].strip() != pair['source_en'].strip():
                diagnostics.append({'paragraph': i, 'pair': j+1, 'source_en': pair['source_en'], 'display_en': pair['en']})
    return originals, aligned, diagnostics

def render(originals, aligned, english_first=False):
    title = '胡雪岩 · 平步青云（上）\n简介 · 楔子 · 第一章\n' + ('逐句英中对照' if english_first else '逐句中英对照') + '\n原著：高阳'
    blocks = [title]
    heading_map = {'内容简介':'内容简介｜SYNOPSIS', '楔子':'楔子｜PROLOGUE', '一':'第一章｜CHAPTER ONE'}
    for orig, row in zip(originals, aligned):
        heading = orig.get('source_heading_prefix')
        if heading:
            blocks.append(heading_map.get(heading, heading))
        lines = []
        for pair in row['pairs']:
            order = ['en','zh'] if english_first else ['zh','en']
            lines.append('\n'.join(pair[k].strip() for k in order))
        blocks.append('\n\n'.join(lines))
    return '\n\n\n'.join(blocks) + '\n'

def main():
    originals, aligned, diagnostics = load_and_validate()
    for english_first in [False, True]:
        name = STEM + ('_逐句英中对照.txt' if english_first else '_逐句中英对照.txt')
        (OUT / name).write_text(render(originals, aligned, english_first))
    total = sum(len(r['pairs']) for r in aligned)
    (OUT / '阅读说明.txt').write_text(
        '本次样稿包含内容简介、楔子及《平步青云（上）》第一章全文。\n\n'
        '逐句中英对照：中文在前，英文紧随其后，适合先做中译英再核对。\n'
        '逐句英中对照：英文在前，中文紧随其后，适合先做英译中再核对。\n'
        '两份文件使用完全相同的句对，仅调整呈现顺序；句对之间空一行，原段落之间增加空行。\n\n'
        '本次仅对现有中英对照版进行分句和排版，正文中英文的文字、标点及先后顺序均保持不变，没有重译或润色。\n'
        '按语义切分原有句子或长句中的对应分句；原译中一句对应多句、或局部语序交叉的地方，保留在同一组，避免错配。由于保留原标点，有的中文分句会以逗号结尾，跨句引号也保留原来的开合位置。\n'
        '中文用字沿用所给原文，仍可能含扫描识别错误。\n'
        '人物、官职和历史单位沿用原译；本样稿中的中文是小说原文，不能视为英译汉练习的唯一标准答案。\n'
    )
    (WORK / 'sentence_alignment.json').write_text(json.dumps(aligned,ensure_ascii=False,indent=2)+'\n')
    verification = {
        'input': str(ORIGINAL),
        'input_sha256': hashlib.sha256(ORIGINAL.read_bytes()).hexdigest(),
        'paragraphs':len(originals),
        'pairs_including_book_heading':total,
        'full_source_coverage': True,
        'existing_bilingual_file':str(BILINGUAL),
        'existing_bilingual_sha256':hashlib.sha256(BILINGUAL.read_bytes()).hexdigest(),
        'both_languages_and_punctuation_unchanged':True,
        'all_original_paragraphs_found_in_existing_edition_in_order':True,
        'english_display_adjustments':diagnostics,
        'files':[{ 'name':p.name, 'bytes':p.stat().st_size, 'sha256':hashlib.sha256(p.read_bytes()).hexdigest() } for p in sorted(OUT.glob('*.txt'))]
    }
    (WORK / 'verification.json').write_text(json.dumps(verification,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'paragraphs':len(originals),'pairs':total,'english_display_adjustments':len(diagnostics),'full_source_coverage':True},ensure_ascii=False))

if __name__ == '__main__':
    main()
