from pathlib import Path
import re,json,difflib,unicodedata,hashlib
ROOT=Path('/Users/lwblx/huapohen/agent/automation/2026/03_10/2/17')
OUT=ROOT/'output/.source-audit/pingbu'
old=(ROOT/'input/胡雪岩.txt').read_text()
new=(ROOT/'input/《胡雪岩》(共五部).txt').read_text()
config=json.loads((ROOT/'output/.translation/book_config.json').read_text())
old_pre={int(k):v['prefix'] for k,v in config['sections'].items() if 11<=int(k)<=26905 and v['prefix']}
new_inline={k+23:v for k,v in old_pre.items() if k>=20425}
def norm(s): return ''.join(c for c in unicodedata.normalize('NFKC',s) if c.isalnum())
def lines(s,which):
 records=[]
 for i,raw in enumerate(s.splitlines(),1):
  if which=='old' and not(11<=i<=26905) or which=='new' and not(8<=i<=26928): continue
  if which=='old' and i==27: continue
  txt=raw.strip()
  if which=='new' and re.fullmatch('第[一二三四五六七八九十]+章',txt): continue
  prefix=(old_pre if which=='old' else new_inline).get(i)
  if prefix:
   assert txt.startswith(prefix),(which,i,txt[:20],prefix)
   txt=txt[len(prefix):]
  n=norm(txt)
  if n: records.append({'line':i,'raw':raw,'norm':n})
 return records
A=lines(old,'old');B=lines(new,'new')
sm=difflib.SequenceMatcher(None,[x['norm'] for x in A],[x['norm'] for x in B],autojunk=False)
diffs=[]; matched=0
for tag,a,b,c,d in sm.get_opcodes():
 if tag=='equal': matched+=sum(len(x['norm']) for x in A[a:b]); continue
 aa=''.join(x['norm'] for x in A[a:b]);bb=''.join(x['norm'] for x in B[c:d])
 cm=difflib.SequenceMatcher(None,aa,bb,autojunk=False)
 for ct,i,j,k,l in cm.get_opcodes():
  if ct=='equal': matched+=j-i
 diffs.append({'kind':tag,'old_lines':[x['line'] for x in A[a:b]],'new_lines':[x['line'] for x in B[c:d]],'old_norm':aa,'new_norm':bb,'old_raw':'\n'.join(x['raw'] for x in A[a:b]),'new_raw':'\n'.join(x['raw'] for x in B[c:d]),'char_diff':[{'kind':ct,'old':aa[i:j],'new':bb[k:l],'old_pos':[i,j],'new_pos':[k,l]} for ct,i,j,k,l in cm.get_opcodes() if ct!='equal']})
report={'method':'Whole first book including prologue; per-line NFKC, alphanumeric only, omit known chapter heading prefixes and wrapper title; exact line alignment with autojunk=False; every unmatched span refined character-wise. No OCR or semantic substitutions silently normalized.','old_sha256':hashlib.sha256((ROOT/'input/胡雪岩.txt').read_bytes()).hexdigest(),'new_sha256':hashlib.sha256((ROOT/'input/《胡雪岩》(共五部).txt').read_bytes()).hexdigest(),'old_lines':len(A),'new_lines':len(B),'old_norm_chars':sum(len(x['norm']) for x in A),'new_norm_chars':sum(len(x['norm']) for x in B),'matched_norm_chars':matched,'diffs':diffs}
(OUT/'comparison.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='diffs'},ensure_ascii=False,indent=2))
print('diff blocks',len(diffs))
for x in diffs:
 print(x['kind'],x['old_lines'],x['new_lines'],[(c['kind'],c['old'],c['new']) for c in x['char_diff']])
