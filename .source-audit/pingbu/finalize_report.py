# -*- coding: utf-8 -*-
from pathlib import Path
import json,re,hashlib
from audit_pingbu import A,B,ROOT,OUT,old_pre,norm
oldbytes=(ROOT/'input/胡雪岩.txt').read_bytes(); newbytes=(ROOT/'input/《胡雪岩》(共五部).txt').read_bytes()
def positions(raw):
 bs=0;cs=0;r={}
 for i,l in enumerate(raw.splitlines(keepends=True),1):
  r[i]={'line_1based':i,'byte_offset_0based':bs,'decoded_char_offset_0based':cs}
  bs+=len(l);cs+=len(l.decode('utf-8'))
 return r
op=positions(oldbytes);np=positions(newbytes)
Amap={r['line']:r for r in A}
chapters=[]
for i,p in old_pre.items():
 if i==11: continue
 if i not in Amap: continue
 key=Amap[i]['norm'][:60]
 hits=[r for r in B if key in r['norm']]
 assert len(hits)==1,(i,p,len(hits))
 n=hits[0]['line']
 chapters.append({'chapter_number_label':p,'old_start':op[i],'new_start':np[n],'prefix_in_old':p,'prefix_in_new':p if i>=20425 else '', 'opening_anchor':Amap[i]['norm'][:40]})
report={
 'conclusion':'旧新《平步青云》全文规范化对齐后无成段正文增删；旧稿已覆盖上中下范围，误留（上）总标题。两稿共享第二十四章分界缺失，不能据此单独证明与纸本完全无遗漏。',
 'boundaries':chapters,
 'volume_boundaries':{'上':{'old_start_line':11,'old_last_body_line':9277,'new_start_line':8,'new_last_body_line':9280},'中':{'old_start_line':9279,'old_last_body_line':17693,'new_start_line':9284,'new_last_body_line':17714},'下':{'old_start_line':17695,'old_last_body_line':26905,'new_start_line':17718,'new_last_body_line':26928}},
 'safe_typo_fixes':[{'old_line':353,'old':'精神夏','new':'精神复','new_line':348},{'old_line':1469,'old':'三有龄','new':'王有龄','new_line':1454},{'old_line':3529,'old':'在五有龄','new':'在王有龄','new_line':3518}],
 'unresolved_variant':{'old_line':439,'new_line':432,'old':'你是科甲出身','new':'我是科甲出身','recommendation':'保留旧稿，未凭出版文本独立确认'},
 'heading_24':{'old_search_interval_lines':[18987,20424],'new_search_interval_lines':[19012,20447],'status':'两文件均未找到分界；无新增文字可据以补题；不强行猜分界'},
 'normalization_statistics':{'old_alphanumeric_chars':589043,'new_alphanumeric_chars':589163,'matched_alphanumeric_chars':589039,'changed_single_chars':4,'new_watermark_insertions':13,'new_watermark_alphanumeric_chars':120,'line_join_events':9,'body_insertions_or_deletions_excluding_watermarks':0},
 'references':[
 {'url':'https://store.linkingbooks.com.tw/product/18458602','publisher':'聯經','edition':'胡雪巖（新校版）（中） ISBN 9789570854275','catalog':'第十二章至第二十一章','evidence':'网页检索完整目录与第十二章选文起首，和本地章节对应'},
 {'url':'https://www.kingstone.com.tw/basic/2800000215699/?actid=basic_ver','publisher':'聯經（目录由金石堂载录）','edition':'胡雪巖（新校版）（下） ISBN 9789570854282','catalog':'第二十二章至第三十一章'},
 {'url':'https://www.kingstone.com.tw/basic/2018630179827/?actid=r2510001_1&lid=book_class3_jid','publisher':'聯經（目录由金石堂载录）','edition':'胡雪巖（新校版）（上） ISBN 9789570854268','catalog':'楔子、第一章至第十一章'}],
 'limitations':['两稿高度同源，差异对齐不能发现双方共同缺失。','目录和卷首选文证明卷次范围，未对照纸本全部正文，不称出版级完整校本。','规范化对齐忽略标点和空白，不能据此评定标点质量。','字节偏移按实际UTF-8原文件；字符偏移按原始换行解码，非read_text换行转换后索引。'],
 'input_sha256':{'old':hashlib.sha256(oldbytes).hexdigest(),'new':hashlib.sha256(newbytes).hexdigest()}}
(OUT/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
text='''《平步青云》新旧稿核验结论\n\n已对楔子至第三十一章末全文比较，而非抽样。去除已定位的章节题号及标点空白后，旧稿589,043个汉字/字母数字，新稿589,163个；共同字符589,039个。所有差异已经逐一列入comparison.json：4个单字异文，13处新稿网站水印（共120个规范化字符），9处换行合并。除网站水印外，没有正文新增、删段或调序。\n\n旧稿标为“平步青云（上）”，实际延续至第三十一章，包含上、中、下范围。可据同版出版目录分为：上册楔子至第十一章；中册第十二至二十一章；下册第二十二至三十一章。旧中册起首9279行，下册起首17695行。新中册正文起首9284行，下册起首17718行。\n\n两稿都缺第二十四章的明确标题；第二十三章标题之后到第二十五章标题之前的全部规范化正文相同。故不能用新稿补出第二十四章分界，也不能排除共同漏文。建议先保留连续正文并在核验说明中标注待校，不猜写章节分界。\n\n新稿并非23章以后全部没有题号。第二十五至三十一章的题号与正文首句黏在一起，可按旧稿已有题号准确分开；第二十四章题号则两稿均未找到。\n\n3处可从新稿订正的旧稿明显错字：353行“精神夏”改“精神复”（下行接“振”），1469行“三有龄”改“王有龄”，3529行“在五有龄”改“在王有龄”。439行“你是科甲出身”与新稿“我是科甲出身”尚待第三方文本确认，建议保留旧文。\n\n本审计证明两份本地文本第一部内容一致及具备三册范围，不能替代与正版纸本逐字校对；两稿高度同源，不能据相互吻合承诺绝无共同缺页或OCR错误。没有修改输入文件。\n'''
(OUT/'核验说明.txt').write_text(text)
print('wrote summary.json and 核验说明.txt')
