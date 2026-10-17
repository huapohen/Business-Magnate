from pathlib import Path
import json,hashlib,re
base=Path('/Users/lwblx/huapohen/agent/automation/2026/03_10/2/17');out=base/'output/.source-audit/remaining'
oldp=base/'input/胡雪岩.txt';newp=base/'input/《胡雪岩》(共五部).txt'
a=oldp.read_text();b=newp.read_text();al=a.splitlines(keepends=True);bl=b.splitlines(keepends=True)
def offset(ls,line):return sum(map(len,ls[:line-1]))
patches=[]
for title,insert_line,st,en in [('红顶商人',26916,26936,31724),('萧瑟洋场',32482,35140,38004)]:
 ss=offset(bl,st);ee=offset(bl,en+1);pos=offset(al,insert_line)
 patches.append({'title':title,'old_start':pos,'old_end':pos,'old_before_line':insert_line,'new_start':ss,'new_end':ee,'new_lines_inclusive':[st,en],'source_text':b[ss:ee],'note':'正文原样截取，含内嵌网页广告及粘连章标题。应用前应清除明确广告并分离标题；本文件不擅自补造原始坏字。'})
root={'offset_definition':'Unicode character offsets in pathlib.Path.read_text(encoding="utf-8") with universal newline normalization; offsets are NOT bytes. Half-open [start,end).','old_sha256_bytes':hashlib.sha256(oldp.read_bytes()).hexdigest(),'new_sha256_bytes':hashlib.sha256(newp.read_bytes()).hexdigest(),'insertions':patches,'old_text_content_insertions':[],'content_insertions_note':'灯火楼台/烟消云散对齐未发现可确认为旧稿大段缺文的新独有正文；灯火新独有较长短语主要版本措辞，建议列异文不强行拼入。'}
(out/'insertions.json').write_text(json.dumps(root,ensure_ascii=False,indent=2))
# A clear dialog ordering repair supported by the other file; optional, separate from added content.
st=offset(al,29271);en=offset(al,29274)
old=a[st:en]
replacement='    “今天下半天就走。”\n\n    “喔，那我要把交代蓉斋的话告诉你，第一，今年丝的市面不大好，养蚕人家，今年这个年，恐怕很难过，你叫他关照柜台上，看货稍微放宽些。”\n'
optional={'description':'旧稿对话错序（不是缺文）：将误夹在“养蚕”二字之间的回答复位，保留全部正文词句。新稿33204、33206行支持此顺序。','old_start':st,'old_end':en,'old_lines_inclusive':[29271,29273],'expected_old':old,'replacement':replacement,'new_evidence_lines':[33204,33206]}
(out/'optional_dialogue_repair.json').write_text(json.dumps(optional,ensure_ascii=False,indent=2))
new_heads={}
for title,st,en in [('红顶商人',26936,31724),('萧瑟洋场',35140,38004)]:
 new_heads[title]=[{'line':i+1,'heading':m.group(),'inline':not bl[i].strip().startswith(m.group())} for i in range(st-1,en) if (m:=re.search('第[一二三四五六七八九十]+章',bl[i]))]
(out/'new_chapters.json').write_text(json.dumps(new_heads,ensure_ascii=False,indent=2))
report='''核验范围：旧《灯火楼台》《烟消云散》全文与新稿对应部；新《红顶商人》《萧瑟洋场》内部章节及边界。\n\n比对方法：删除空白、标点，仅保留汉字、字母、数字；唯一40字锚点+最长递增链对齐，锚点间用逐字符SequenceMatcher细比。差异JSON保留原文精确字符位置、行号及前后锚点。\n\n1. 灯火楼台：旧26945–32481，新31732–35135。旧124643个规范化字符，新124662，匹配122628；最大单独差块35字系新稿卷尾网站广告。没有发现整段、整章缺文。约1902个细差块包含OCR异字、标点/英文缺失及版本措辞。新稿并不普遍更优：新31904错序“古老爷…贵东家是怎么关照你的”在旧27209顺序正确；新32694少了旧28465“玄…黄…”两句；新若干英文地名也省略。旧29271–29273有对话错序，新33204/33206正确，可选补丁单列。\n\n2. 烟消云散：旧32484–40926，新38012–46479。旧171412、新171645，匹配171400。旧独有12个英文字符即William/Billy（旧38127、新43672附近）；新多出的主要是网站广告和章标题字样，未发现正文段落缺漏。旧应保留。\n\n3. 红顶商人：新26936–31724完整呈现第一至第十一章，第九章在30790行末粘连“－高阳－红顶商人第九章###”，正文在随后行；不是少了第九章。末段31724明确收束第一次借外债并提示后续结局。此为章节结构/边界核验，不等于逐字与纸书比对认证。\n\n4. 萧瑟洋场：新35140–38004含第一至第七章；第二至第七章标题分别粘连35514、36216、36590、36832、37186、37404行正文开头。第一章从螺蛳太太的心境及胡老太太生日承接旧灯火末尾信用/排场议论；第七章末瑞香婚事礼成，与之后烟消云散开篇上海市面更坏的叙事阶段相接。无可据此认定的内部整章缺失，但无法仅靠单一新稿证明逐字无漏。\n\n5. 新萧瑟原始乱码仍存：35198行“赵孟钭郑…”一串含四个私用区字；36052、36172、36186行同一私用区字U+E41D；36742行“墨”后U+E421。均在两份文本不重叠的正文区，不能用旧稿校正，不应猜写。\n\n合并建议：保留旧稿全部两部正文，补入新红顶及萧瑟，按上述内嵌标题恢复章分隔，清除明确网站广告；书名齐全与逐字校勘完整须区分。\n'''
(out/'audit.txt').write_text(report)
print('saved',len(patches),'insertions; source offsets',[(p['title'],p['old_start'],p['new_start'],p['new_end']) for p in patches])
