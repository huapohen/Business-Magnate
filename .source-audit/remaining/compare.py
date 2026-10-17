from pathlib import Path
from bisect import bisect_left
import re,json,difflib
base=Path('/Users/lwblx/huapohen/agent/automation/2026/03_10/2/17')
out=base/'output/.source-audit/remaining'
old=(base/'input/胡雪岩.txt').read_text()
new=(base/'input/《胡雪岩》(共五部).txt').read_text()
def prep(t,a,z):
 lines=t.splitlines(keepends=True);start=sum(map(len,lines[:a-1]));end=sum(map(len,lines[:z]));s=t[start:end]
 chars=[];poss=[]
 for m in re.finditer('[\\u3400-\\u9fffA-Za-z0-9]',s):chars.append(m.group());poss.append(start+m.start())
 return ''.join(chars),poss

def cmp(name,ar,br):
 a,ap=prep(old,*ar);b,bp=prep(new,*br)
 # exact unique anchors sampled each 20 chars
 hits=[]
 for i in range(0,len(a)-40,20):
  token=a[i:i+40];j=b.find(token)
  if j>=0 and b.find(token,j+1)<0:hits.append((i,j))
 tails=[];ti=[];prev=[]
 for i,(x,y) in enumerate(hits):
  p=bisect_left(tails,y);prev.append(ti[p-1] if p else -1)
  if p==len(tails):tails.append(y);ti.append(i)
  else:tails[p]=y;ti[p]=i
 idx=ti[-1]; anchors=[]
 while idx>=0:anchors.append(hits[idx]);idx=prev[idx]
 anchors=anchors[::-1]; merged=[]
 for x,y in anchors:
  if merged and x<=merged[-1][0]+merged[-1][2] and x-y==merged[-1][0]-merged[-1][1]:
   px,py,n=merged[-1];merged[-1]=(px,py,x+40-px)
  elif not merged or (x>=merged[-1][0]+merged[-1][2] and y>=merged[-1][1]+merged[-1][2]):merged.append((x,y,40))
 res=[];ex=ey=0;eq=0
 for x,y,n in merged+[(len(a),len(b),0)]:
  sm=difflib.SequenceMatcher(None,a[ex:x],b[ey:y],autojunk=False)
  for op,i,j,k,l in sm.get_opcodes():
   i+=ex;j+=ex;k+=ey;l+=ey
   if op=='equal':eq+=j-i;continue
   def desc(t,ps,i,j):
    if i==j:return {'normalized_start':i,'normalized_end':j,'char_count':0,'text':''}
    st=ps[i];en=ps[j-1]+1
    return {'normalized_start':i,'normalized_end':j,'char_start':st,'char_end':en,'line_start':t.count('\n',0,st)+1,'line_end':t.count('\n',0,en)+1,'char_count':j-i,'text':t[st:en]}
   res.append({'op':op,'old':desc(old,ap,i,j),'new':desc(new,bp,k,l),'old_before':a[max(0,i-30):i],'old_after':a[j:j+30],'new_before':b[max(0,k-30):k],'new_after':b[l:l+30]})
  eq+=n;ex=x+n;ey=y+n
 record={'name':name,'ranges':[ar,br],'normalized_lengths':[len(a),len(b)],'equal':eq,'differences':res}
 (out/(name+'.json')).write_text(json.dumps(record,ensure_ascii=False,indent=2))
 print(name,len(a),len(b),'equal',eq,'diffs',len(res),'large',sum(max(d['old']['char_count'],d['new']['char_count'])>=25 for d in res))
 for d in res:
  if max(d['old']['char_count'],d['new']['char_count'])>=25:
   print(d['op'],'old',d['old'].get('line_start'),d['old'].get('line_end'),d['old']['char_count'],'new',d['new'].get('line_start'),d['new'].get('line_end'),d['new']['char_count'],'oldtext',repr(d['old']['text'][:160]),'newtext',repr(d['new']['text'][:160]))
cmp('灯火楼台',(26945,32481),(31732,35135))
cmp('烟消云散',(32484,40926),(38012,46479))
