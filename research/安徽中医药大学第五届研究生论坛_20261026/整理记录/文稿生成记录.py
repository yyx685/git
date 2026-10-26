from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from lxml import etree as E
from copy import deepcopy
import hashlib,json,re,shutil
TMP=Path('/tmp/codex-forum-20261026')
ROOT=Path('/Users/yyx/Desktop/git/git/research/安徽中医药大学第五届研究生论坛_20261026')
SOURCE=Path('/Users/yyx/Desktop/附件1论文投稿格式规范.docx')
NAME='硕士－针灸推拿学院－针灸推拿学－袁英祥－2025203212013'
ROOT.mkdir(parents=True,exist_ok=True)
AUTHOR=ROOT/'整理记录';AUTHOR.mkdir(exist_ok=True)
RES=AUTHOR/'来源';RES.mkdir(exist_ok=True)
FIGS=AUTHOR/'插图';FIGS.mkdir(exist_ok=True)
shutil.copyfile(SOURCE,RES/SOURCE.name)
shutil.copyfile(TMP/'content.json',AUTHOR/'论坛稿内容.json')
d=json.loads((TMP/'content.json').read_text())
with ZipFile(SOURCE) as z:parts={n:z.read(n) for n in z.namelist()}
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships','wp':'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing','a':'http://schemas.openxmlformats.org/drawingml/2006/main','pic':'http://schemas.openxmlformats.org/drawingml/2006/picture'}
def tag(k):pre,local=k.split(':');return '{'+NS[pre]+'}'+local
def el(k,attrs=None,text=None):
 x=E.Element(tag(k))
 for a,v in (attrs or {}).items():x.set(tag(a) if ':' in a else a,str(v))
 if text is not None:x.text=text
 return x
def add(parent,k,attrs=None,text=None):x=el(k,attrs,text);parent.append(x);return x
def xml(x):return E.tostring(x,xml_declaration=True,encoding='UTF-8',standalone=True)
root=E.fromstring(parts['word/document.xml']);body=root.find('w:body',NS)
original_paras=body.findall('w:p',NS)
def textof(p):return ''.join(p.itertext())
sample={}
for p in original_paras:
 t=''.join(p.xpath('.//w:t/text()',namespaces=NS))
 if t=='博士研究生':sample['level']=deepcopy(p)
 elif t=='中医学':sample['discipline']=deepcopy(p)
 elif t=='×××××的机制研究':sample['title']=deepcopy(p)
 elif t=='张×× 李×× 王××*':sample['authors']=deepcopy(p)
 elif t.startswith('摘要：'):sample['abstract']=deepcopy(p)
 elif t.startswith('关键词：'):sample['keywords']=deepcopy(p)
 elif t=='（正文内容）':sample['body']=deepcopy(p)
 elif t=='1 一级标题':sample['h1']=deepcopy(p)
 elif t=='1.1 二级标题':sample['h2']=deepcopy(p)
 elif t=='参考文献':sample['refs']=deepcopy(p)
sect=deepcopy(body.find('w:sectPr',NS))
for c in list(body):body.remove(c)
# written numerical requirements override incidental reference geometry
pg=sect.find('w:pgSz',NS);pg.set(tag('w:w'),'11906');pg.set(tag('w:h'),'16838')
mar=sect.find('w:pgMar',NS)
for k,v in {'top':1440,'bottom':1440,'left':1417,'right':1417,'gutter':0}.items():mar.set(tag('w:'+k),str(v))
cols=sect.find('w:cols',NS);cols.set(tag('w:num'),'1')
# doc grid in reference would otherwise turn 1.5 spacing into larger fixed snapping
if sect.find('w:docGrid',NS) is not None:sect.remove(sect.find('w:docGrid',NS))
def properties(p):
 pr=p.find('w:pPr',NS)
 if pr is None:pr=el('w:pPr');p.insert(0,pr)
 return pr
def setprop(pr,k,attrs=None):
 old=pr.find('w:'+k,NS)
 if old is not None:pr.remove(old)
 return add(pr,'w:'+k,attrs)
def run(p,text,size=21,bold=False,italic=False,sup=False):
 r=add(p,'w:r');rp=add(r,'w:rPr')
 add(rp,'w:rFonts',{'w:ascii':'Times New Roman','w:hAnsi':'Times New Roman','w:eastAsia':'宋体','w:cs':'Times New Roman'})
 add(rp,'w:sz',{'w:val':size});add(rp,'w:szCs',{'w:val':size});add(rp,'w:color',{'w:val':'000000'});add(rp,'w:lang',{'w:val':'en-US','w:eastAsia':'zh-CN'})
 if bold:add(rp,'w:b')
 if italic:add(rp,'w:i')
 if sup:add(rp,'w:vertAlign',{'w:val':'superscript'})
 add(r,'w:t',{'{http://www.w3.org/XML/1998/namespace}space':'preserve'} if False else None,text)
 r[-1].set('{http://www.w3.org/XML/1998/namespace}space','preserve')
 return r
PAT=re.compile(r'(\[\d+(?:[,-]\d+)*\]|2\^（−ΔCq）|Nox[14]|(?<![A-Za-z])P(?=[＜＝<=>≥≤]))')
def rich(p,t,size=21,bold=False,refs=True):
 pos=0
 for m in PAT.finditer(t):
  if m.start()>pos:run(p,t[pos:m.start()],size,bold)
  z=m.group()
  if z.startswith('['):run(p,('\u2060'+z) if refs else z,size,bold,sup=refs)
  elif z.startswith('2^'):run(p,'2',size,bold);run(p,'−ΔCq',size,bold,sup=True)
  else:run(p,z,size,bold,italic=True)
  pos=m.end()
 if pos<len(t):run(p,t[pos:],size,bold)
def para(t='',role='body',size=21,bold=False,align=None,indent=None,before=0,after=0,line=360,keep=False,pagebreak=False,refs=True):
 p=deepcopy(sample.get(role,sample['body']))
 # retain source paragraph pattern, replace editable contents and intentional role props
 for a in list(p.attrib):del p.attrib[a]
 for c in list(p):
  if c.tag!=tag('w:pPr'):p.remove(c)
 pr=properties(p)
 for c in list(pr):
  if c.tag in [tag('w:rPr'),tag('w:pageBreakBefore'),tag('w:pStyle'),tag('w:keepNext'),tag('w:keepLines'),tag('w:ind'),tag('w:jc')]:pr.remove(c)
 setprop(pr,'spacing',{'w:before':before,'w:after':after,'w:line':line,'w:lineRule':'auto'})
 setprop(pr,'snapToGrid',{'w:val':'0'})
 setprop(pr,'widowControl',{'w:val':'1'})
 if indent is None:indent=(role in ('body','abstract','keywords'))
 setprop(pr,'ind',{'w:firstLine':'420' if indent else '0','w:left':'0','w:right':'0'})
 if align:setprop(pr,'jc',{'w:val':align})
 if keep:setprop(pr,'keepNext');setprop(pr,'keepLines')
 if pagebreak:setprop(pr,'pageBreakBefore')
 if role=='title':setprop(pr,'pStyle',{'w:val':'Title'})
 if role in ('h1','h2'):setprop(pr,'outlineLvl',{'w:val':'0' if role=='h1' else '1'})
 rich(p,t,size,bold,refs=refs)
 body.append(p)
 return p
# default title style, all text in black; inherit no decorated rule
styles=E.fromstring(parts['word/styles.xml'])
for st in styles.findall('w:style',NS):
 if st.get(tag('w:styleId')) in ('Normal','Title','FootnoteText','FootnoteReference'):
  rp=st.find('w:rPr',NS)
  if rp is None:rp=add(st,'w:rPr')
  for c in list(rp):
   if c.tag in (tag('w:rFonts'),tag('w:color'),tag('w:sz')):rp.remove(c)
  add(rp,'w:rFonts',{'w:ascii':'Times New Roman','w:hAnsi':'Times New Roman','w:eastAsia':'宋体'})
  add(rp,'w:color',{'w:val':'000000'});add(rp,'w:sz',{'w:val':'24' if st.get(tag('w:styleId'))=='Title' else '21'})
  pp=st.find('w:pPr',NS)
  if pp is not None:
   for c in list(pp):
    if c.tag in (tag('w:pBdr'),tag('w:shd')):pp.remove(c)
# Ensure Title exists, source may have localized style ID
if not styles.xpath('./w:style[@w:styleId="Title"]',namespaces=NS):
 st=add(styles,'w:style',{'w:type':'paragraph','w:styleId':'Title'});add(st,'w:name',{'w:val':'Title'});add(st,'w:basedOn',{'w:val':'Normal'})
 rp=add(st,'w:rPr');add(rp,'w:rFonts',{'w:ascii':'Times New Roman','w:hAnsi':'Times New Roman','w:eastAsia':'宋体'});add(rp,'w:b');add(rp,'w:sz',{'w:val':'24'});add(rp,'w:color',{'w:val':'000000'})
para('硕士研究生','level',28,True,align='left',indent=False,line=240,keep=True)
para('中医学','discipline',28,True,align='left',indent=False,line=240,keep=True)
para('',indent=False,line=240,keep=True)
para(d['title'],'title',24,True,align='center',indent=False,before=0,after=80,keep=True)
p=para('','authors',align='center',indent=False,keep=True)
for i,(name,aff) in enumerate(d['authors']):
 if i:run(p,' ')
 run(p,name);run(p,aff,sup=True)
r=add(p,'w:r');rp=add(r,'w:rPr');add(rp,'w:vertAlign',{'w:val':'superscript'});add(rp,'w:rFonts',{'w:ascii':'Times New Roman','w:hAnsi':'Times New Roman','w:eastAsia':'宋体'});add(rp,'w:sz',{'w:val':'21'});add(r,'w:footnoteReference',{'w:id':'1','w:customMarkFollows':'1'});add(r,'w:t',text='†')
for a in d['affiliations']:para(a,align='center',indent=False,keep=True)
p=para('','abstract',before=80);run(p,'摘要：',bold=True);rich(p,d['abstract'])
p=para('','keywords');run(p,'关键词：',bold=True);rich(p,'；'.join(d['keywords']))
for t in d['intro']:para(t)
# images + relationships
rels=E.fromstring(parts['word/_rels/document.xml.rels'])
RELNS='http://schemas.openxmlformats.org/package/2006/relationships'
def picture(n):
 f=d['figures'][str(n)]
 src=Path('/Users/yyx/Desktop/git/git/research/Physiological_Research_Original_Article_完整重写稿_20261020/Figures')/f['source']
 fname=f'forum_fig{n}.jpg';parts['word/media/'+fname]=src.read_bytes();shutil.copyfile(src,FIGS/f'图{n}.jpg')
 rid='rIdForumImage'+str(n)
 rr=E.SubElement(rels,'{'+RELNS+'}Relationship');rr.set('Id',rid);rr.set('Type',NS['r']+'/image');rr.set('Target','media/'+fname)
 from PIL import Image
 im=Image.open(src);width=15.8 if n==1 else 15.0
 cx=round(width/2.54*914400);cy=round(cx*im.height/im.width)
 p=para('',indent=False,align='center',before=60,keep=True)
 r=add(p,'w:r');drawing=add(r,'w:drawing');inline=add(drawing,'wp:inline',{'distT':'0','distB':'0','distL':'0','distR':'0'})
 add(inline,'wp:extent',{'cx':cx,'cy':cy});add(inline,'wp:effectExtent',{'l':0,'t':0,'r':0,'b':0});add(inline,'wp:docPr',{'id':n,'name':'Figure '+str(n),'descr':f['title']})
 cn=add(inline,'wp:cNvGraphicFramePr');add(cn,'a:graphicFrameLocks',{'noChangeAspect':1})
 g=add(inline,'a:graphic');gd=add(g,'a:graphicData',{'uri':NS['pic']});pic=add(gd,'pic:pic');nv=add(pic,'pic:nvPicPr');add(nv,'pic:cNvPr',{'id':n,'name':fname});add(nv,'pic:cNvPicPr');bf=add(pic,'pic:blipFill');add(bf,'a:blip',{'r:embed':rid});stretch=add(bf,'a:stretch');add(stretch,'a:fillRect');sp=add(pic,'pic:spPr');xf=add(sp,'a:xfrm');add(xf,'a:off',{'x':0,'y':0});add(xf,'a:ext',{'cx':cx,'cy':cy});geom=add(sp,'a:prstGeom',{'prst':'rect'});add(geom,'a:avLst')
 para(f['title'],size=21,bold=True,align='center',indent=False,keep=True)
 para(f['caption'],size=21,indent=False,after=60)
for s in d['sections']:
 para(s['heading'],'h1',bold=True,indent=False,before=100,keep=True)
 for t in s.get('paragraphs',[]):para(t)
 for sub in s.get('subsections',[]):
  para(sub['heading'],'h2',bold=True,indent=False,before=60,keep=True)
  for t in sub['paragraphs']:para(t)
  if sub.get('figure'):picture(sub['figure'])
para(d['publication'],before=80)
para('利益冲突：作者声明无利益冲突。')
para(d['ai'])
para(d['contact'])
# References receive a real page break. Contact stays at article end after references.
contactp=body[-1];body.remove(contactp)
para('参考文献','refs',bold=True,indent=False,line=240,pagebreak=True,keep=True)
for i,t in enumerate(d['references'],1):
 p=para(f'[{i}] '+t,indent=False,line=240,after=70,refs=False)
 pr=properties(p);setprop(pr,'ind',{'w:left':'420','w:hanging':'420'})
body.append(contactp)
body.append(sect)
# genuine footnote after last author; custom mark avoids duplicate affiliation marker
notes=E.fromstring(parts['word/footnotes.xml'])
for n in list(notes):
 if int(n.get(tag('w:id'),'0'))>0:notes.remove(n)
n=add(notes,'w:footnote',{'w:id':'1'});p=el('w:p');n.append(p);pr=add(p,'w:pPr');add(pr,'w:spacing',{'w:after':0,'w:line':240,'w:lineRule':'auto'});add(pr,'w:jc',{'w:val':'left'});run(p,d['fund'])
ct=E.fromstring(parts['[Content_Types].xml']);CT='http://schemas.openxmlformats.org/package/2006/content-types'
if not ct.xpath('./*[local-name()="Default"][@Extension="jpg"]'):
 x=E.SubElement(ct,'{'+CT+'}Default');x.set('Extension','jpg');x.set('ContentType','image/jpeg')
parts.update({'word/document.xml':xml(root),'word/styles.xml':xml(styles),'word/footnotes.xml':xml(notes),'word/_rels/document.xml.rels':xml(rels),'[Content_Types].xml':xml(ct)})
# Metadata is intentionally replaced; retain opaque source parts byte-for-byte.
core=E.fromstring(parts['docProps/core.xml']);DCT='http://purl.org/dc/elements/1.1/'
for k,t in [('title',d['title']),('creator','袁英祥'),('subject','安徽中医药大学第五届研究生学术论坛')]:
 node=core.find('{'+DCT+'}'+k)
 if node is None:node=E.SubElement(core,'{'+DCT+'}'+k)
 node.text=t
parts['docProps/core.xml']=xml(core)
# plain-text transcript of finished article with same numerical values
md=['# '+d['title'],'','硕士研究生｜中医学（针灸推拿学方向）','学号：2025203212013','袁英祥¹ 杨斌² 何宗保¹ 吕有奎² 吴子建¹*','']+d['affiliations']+['',d['fund'],'','摘要：'+d['abstract'],'','关键词：'+'；'.join(d['keywords']),'']+d['intro']
for s in d['sections']:
 md+=['','## '+s['heading'],'']+s.get('paragraphs',[])
 for sub in s.get('subsections',[]):
  md+=['','### '+sub['heading'],'']+sub['paragraphs']
  if sub.get('figure'):
   f=d['figures'][str(sub['figure'])];md+=['','!['+f['title']+'](插图/图'+str(sub['figure'])+'.jpg)',f['title'],f['caption']]
md+=['',d['publication'],'利益冲突：作者声明无利益冲突。',d['ai'],'','## 参考文献','']+[f'[{i}] {t}' for i,t in enumerate(d['references'],1)]+['',d['contact']]
(AUTHOR/'论坛稿.md').write_text('\n\n'.join(md))
# approximate Word mixed-script count; Chinese chars and western words, refs count separately
narr=[d['title'],d['abstract'],'；'.join(d['keywords'])]+d['intro']
for s in d['sections']:
 narr+=[s['heading']]+s.get('paragraphs',[])
 for ss in s.get('subsections',[]):narr+=[ss['heading']]+ss['paragraphs']
alltexts=[''.join(p.xpath('.//w:t/text()',namespaces=NS)) for p in body.findall('w:p',NS)]
alltexts+=[d['fund']]
def counts(ts):
 t='\n'.join(ts);c=len(re.findall('[\u3400-\u9fff]',t));eng=len(re.findall(r'[A-Za-z0-9]+(?:[.\-–][A-Za-z0-9]+)*',t));return {'中文汉字':c,'英文数字词':eng,'混排估算字数':c+eng,'非空白字符':len(re.sub(r'\s','',t))}
count={'主叙述不含图注文献声明':counts(narr),'全文含图注文献声明':counts(alltexts),'摘要非空白字符':len(re.sub(r'\s','',d['abstract']))}
(AUTHOR/'字数核对.json').write_text(json.dumps(count,ensure_ascii=False,indent=2))
app=E.fromstring(parts['docProps/app.xml']);EP='http://schemas.openxmlformats.org/officeDocument/2006/extended-properties'
for k,t in [('Words',str(count['全文含图注文献声明']['混排估算字数'])),('Characters',str(count['全文含图注文献声明']['非空白字符']))]:
 x=app.find('{'+EP+'}'+k)
 if x is not None:x.text=t
parts['docProps/app.xml']=xml(app)
final=ROOT/(NAME+'.docx')
with ZipFile(final,'w',ZIP_DEFLATED) as z:
 for name,b in parts.items():z.writestr(name,b)
# record exact package preservation
with ZipFile(SOURCE) as z:
 changes=[n for n in z.namelist() if parts.get(n)!=z.read(n)]
 inventory=[{'part':n,'bytes':len(z.read(n)),'sha256':hashlib.sha256(z.read(n)).hexdigest(),'classification':'editable' if n in changes else 'preserve-only'} for n in z.namelist()]
(AUTHOR/'模板包结构核对.json').write_text(json.dumps({'changed':changes,'source_inventory':inventory,'new_parts':[x for x in parts if x not in [a['part'] for a in inventory]]},ensure_ascii=False,indent=2))
print(final);print(json.dumps(count,ensure_ascii=False))
