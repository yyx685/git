"""Retain original H&E pixels and adapt the MMR figure style to verified inputs.

Requires Python, NumPy, Matplotlib and Pillow. Place this script beside the
unchanged supporting CSV/JSON files or specify --data-dir. Outputs default to
the current directory; --output-dir selects another directory. --he-image can
copy the original H&E JPEG without editing. No statistical tests are performed.
Inferential annotations are read from the previously verified JSON results.
Diagram arrows represent hypotheses only. The H&E image is never generated.
"""
from pathlib import Path
import csv, json, hashlib, shutil, argparse
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib import font_manager
from matplotlib.ticker import MaxNLocator
from PIL import Image

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--data-dir', type=Path, default=Path(__file__).resolve().parent,
                    help='Directory containing the unchanged supporting CSV and JSON files')
parser.add_argument('--output-dir', type=Path, default=Path.cwd(),
                    help='Output directory (default current working directory)')
parser.add_argument('--he-image', type=Path, default=None,
                    help='Optional original H&E JPEG to copy byte for byte as Yuan_fig3.jpg')
args = parser.parse_args()
OUT = args.output_dir.resolve(); OUT.mkdir(parents=True,exist_ok=True)
SOURCE = args.data_dir.resolve()
GROUPS = ['Sham-operated', 'Model', 'Restoration']
COLORS = ['#161616', '#b7b7b7', '#737373']
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
font_manager.findfont('Arial', fallback_to_default=False)
plt.rcParams.update({'font.family':'Arial', 'font.size':9, 'axes.labelsize':9,
 'axes.spines.top':False, 'axes.spines.right':False, 'axes.linewidth':1,
 'xtick.direction':'out', 'ytick.direction':'out', 'pdf.fonttype':42,
 'ps.fonttype':42, 'savefig.facecolor':'white'})

audit = {'purpose':'Retain MMR figure content and visual style with verified quantitative inputs',
 'date':'2026-10-15', 'statistical_tests_performed':False,
 'experimental_images_generated_or_edited':False, 'input_files':{}, 'figures':{},
 'visual_review':'pending'}
for name in ['S1_Data_RVLM_Processed_Values.csv', 'S2_Data_RTqPCR_Animal_Paired_Values.csv',
             'S3_File_RVLM_Statistical_Outputs.json', 'S4_File_RTqPCR_Statistical_Outputs.json']:
    audit['input_files'][name] = {'sha256':sha(SOURCE/name), 'modified':False}

if args.he_image is not None:
    he_image = args.he_image.resolve()
    if he_image != OUT/'Yuan_fig3.jpg':
        shutil.copy2(he_image, OUT/'Yuan_fig3.jpg')
    assert sha(he_image) == sha(OUT/'Yuan_fig3.jpg')
    with Image.open(OUT/'Yuan_fig3.jpg') as im:
        audit['figures']['Yuan_fig3'] = {'source':str(he_image),
          'bytes_identical':True, 'sha256':sha(OUT/'Yuan_fig3.jpg'), 'dimensions':list(im.size),
          'dpi':[float(x) for x in im.info.get('dpi',())],
          'changes':'None; complete supplied H&E composite copied byte for byte.',
          'limits':'Qualitative fields only; animal count, image mapping and scale calibration records not confirmed.'}

with (SOURCE/'S1_Data_RVLM_Processed_Values.csv').open(newline='',encoding='utf-8-sig') as f:
    bio = list(csv.DictReader(f))
with (SOURCE/'S2_Data_RTqPCR_Animal_Paired_Values.csv').open(newline='',encoding='utf-8-sig') as f:
    qpcr = list(csv.DictReader(f))
bio_stats = json.loads((SOURCE/'S3_File_RVLM_Statistical_Outputs.json').read_text())
qpcr_stats = json.loads((SOURCE/'S4_File_RTqPCR_Statistical_Outputs.json').read_text())

def export(fig, stem, record):
    fig.savefig(OUT/(stem+'.pdf'))
    fig.savefig(OUT/(stem+'.svg'))
    fig.savefig(OUT/(stem+'.tif'),dpi=600,pil_kwargs={'compression':'tiff_lzw'})
    plt.close(fig)
    with Image.open(OUT/(stem+'.tif')) as im:
        im.convert('RGB').save(OUT/(stem+'.jpg'),quality=100,subsampling=0,dpi=(600,600),optimize=True)
        record.update({'dimensions':list(im.size),'dpi':[600,600],
          'tiff_sha256':sha(OUT/(stem+'.tif')), 'jpeg_sha256':sha(OUT/(stem+'.jpg'))})
    audit['figures'][stem] = record

def base_panel(ax, arrays, letter, ylabel, title=None):
    for x, group, color in zip(range(3),GROUPS,COLORS):
        a = np.asarray(arrays[group],dtype=float)
        assert len(a)==6 and np.isfinite(a).all()
        ax.bar(x,a.mean(),width=.60,color=color,edgecolor='black',linewidth=1.05,zorder=1)
        ax.errorbar(x,a.mean(),yerr=a.std(ddof=1),fmt='none',color='black',
                    capsize=3.5,linewidth=1.0,zorder=2)
        ax.scatter(x+np.linspace(-.14,.14,6),a,s=17,facecolor='white',
                   edgecolor='black',linewidth=.65,zorder=3)
    ax.set_xticks([0,1,2],['Sham\n(day 28)','Model\n(day 28)','Rest.\n(day 56)'])
    ax.tick_params(axis='x',labelsize=8)
    ax.set_xlim(-.6,2.6);ax.set_ylim(bottom=0)
    ax.set_ylabel(ylabel,labelpad=6)
    ax.yaxis.set_major_locator(MaxNLocator(nbins=5,min_n_ticks=4))
    ax.text(-.19,1.04,letter,transform=ax.transAxes,fontsize=13,fontweight='bold')
    if title: ax.set_title(title,fontstyle='italic',fontsize=12,pad=10)

def bracket(ax,x1,x2,y,label,span):
    h=.018*span
    ax.plot([x1,x1,x2,x2],[y-h,y,y,y-h],color='black',linewidth=1)
    ax.text((x1+x2)/2,y+.012*span,label,ha='center',va='bottom',fontsize=9)

bio_record={'source_visual_style':'lyk mmr期刊.docx Figure 4', 'arrays':{},
 'annotation_source':'S3_File_RVLM_Statistical_Outputs.json, Games–Howell adjusted P values',
 'changes':'Retained black/light-gray/dark-gray bars and sample SD; overlaid six independent values; fluorescence unit corrected to AU; exact source comparisons used.'}
fig,axs=plt.subplots(1,3,figsize=(7.8,3.8))
for ax, endpoint, letter, ylabel in zip(axs,['SOD','MDA','ROS'],'ABC',
    ['SOD (U/mg protein)','MDA (nmol/mg protein)','Protein-normalized fluorescence (AU)']):
    data={g:[float(r['Processed_value']) for r in bio if r['Endpoint']==endpoint and r['Group']==g] for g in GROUPS}
    bio_record['arrays'][endpoint]=data
    for g,a in data.items():
        summary=next(s for s in bio_stats['summaries'] if s['endpoint']==endpoint and s['group']==g)
        assert np.isclose(np.mean(a),summary['mean']) and np.isclose(np.std(a,ddof=1),summary['sd'])
    base_panel(ax,data,letter,ylabel)
    highest=max(max(a) for a in data.values())
    span=highest*1.38
    for i,(g1,g2,x1,x2) in enumerate([('Sham-operated','Model',0,1),('Model','Restoration',1,2)]):
        c=next(c for c in bio_stats['posthoc'] if c['endpoint']==endpoint and c['group_1']==g1 and c['group_2']==g2)
        assert c['p_adjusted']<.001
        bracket(ax,x1,x2,highest+(i*.105+.11)*span,'***',span)
        bio_record.setdefault('annotations',[]).append({'endpoint':endpoint,'groups':[g1,g2],'p':c['p_adjusted'],'label':'***'})
    ax.set_ylim(0,span)
fig.subplots_adjust(left=.075,right=.985,bottom=.19,top=.86,wspace=.49)
bio_record['numeric_arrays_sha256']=hashlib.sha256(json.dumps(bio_record['arrays'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
export(fig,'Yuan_fig1',bio_record)

qpcr_record={'source_visual_style':'lyk mmr期刊.docx Figure 6, corrected using animal-paired Cq data',
 'arrays':{},'annotation_source':'Existing Welch tests on ΔCq, Holm correction over all 18 source comparisons',
 'changes':'Preserved bar+SD design; corrected Nox4 panel using confirmed mRNA values; overlaid six values; exact adjusted P labels replace incorrect source stars.'}
fig,axs=plt.subplots(1,2,figsize=(6.3,3.8))
for ax,target,letter in zip(axs,['Nox1','Nox4'],'AB'):
    data={g:[float(r['normalized_expression']) for r in qpcr if r['target']==target and r['group']==g] for g in GROUPS}
    qpcr_record['arrays'][target]=data
    gene=next(g for g in qpcr_stats['genes'] if g['gene']==target)
    for g,a in data.items():
        summary=next(s for s in gene['groups'] if s['group']==g)['fold_statistics']
        assert np.isclose(np.mean(a),summary['mean']) and np.isclose(np.std(a,ddof=1),summary['sample_sd'])
    base_panel(ax,data,letter,'Relative mRNA abundance',target)
    highest=max(max(a) for a in data.values());span=highest*1.40
    for i,(num,den,x1,x2) in enumerate([('Model','Sham-operated',0,1),('Restoration','Model',1,2)]):
        c=next(c for c in qpcr_stats['comparisons'] if c['gene']==target and c['numerator_group']==num and c['denominator_group']==den)
        p=c['p_holm_18_test_family'];label=f'P = {p:.5f}' if p<.001 else f'P = {p:.4f}'
        bracket(ax,x1,x2,highest+(i*.105+.11)*span,label,span)
        qpcr_record.setdefault('annotations',[]).append({'target':target,'comparison':c['comparison'],'p_holm_18':p,'label':label})
    ax.set_ylim(0,span)
fig.subplots_adjust(left=.105,right=.985,bottom=.19,top=.82,wspace=.38)
qpcr_record['numeric_arrays_sha256']=hashlib.sha256(json.dumps(qpcr_record['arrays'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
export(fig,'Yuan_fig2',qpcr_record)

# Publication vector schematic. All biological connections are hypotheses.
from matplotlib.patches import Ellipse, Rectangle
plt.rcParams['svg.fonttype'] = 'none'
fig, ax = plt.subplots(figsize=(7.5, 4.8))
ax.set_xlim(0, 1080); ax.set_ylim(0, 690); ax.axis('off')
C = {'ink':'#173047', 'text':'#243846', 'muted':'#61717D',
     'green':'#247C70', 'greenfill':'#EDF7F3', 'blue':'#406C98',
     'bluefill':'#EFF4FA', 'line':'#6A7781', 'red':'#C95B46',
     'bone':'#CAD4DC', 'boneedge':'#778E9E', 'pale':'#F7F9FB'}
def txt(x,y,s,fs=9,weight='normal',color=None,ha='center',va='center',**kw):
    return ax.text(x,y,s,fontsize=fs,fontweight=weight,color=color or C['text'],
                   ha=ha,va=va,linespacing=1.23,**kw)
def rect(x,y,w,h,fc,ec,lw=1.0,dashed=False,r=9):
    a=FancyBboxPatch((x,y),w,h,boxstyle=f'round,pad=0,rounding_size={r}',
        linewidth=lw,facecolor=fc,edgecolor=ec,
        linestyle=(0,(4,3)) if dashed else '-',zorder=1)
    ax.add_patch(a);return a
def link(p,q):
    ax.add_patch(FancyArrowPatch(p,q,arrowstyle='-|>',mutation_scale=9,
        linewidth=1.0,color=C['line'],linestyle=(0,(4,3)),zorder=3))
def heading(x,letter,title):
    txt(x,584,letter,10.5,'bold',C['ink'],ha='left')
    txt(x+25,584,title,9.0,'bold',C['ink'],ha='left')

txt(540,658,'Observed regional changes and proposed cardiovascular links',12.4,'bold',C['ink'])
ax.add_patch(Rectangle((215,619),10,10,facecolor=C['greenfill'],edgecolor=C['green'],linewidth=.9))
txt(237,624,'Current measurements',8.1,ha='left')
ax.add_patch(Rectangle((471,619),10,10,facecolor=C['bluefill'],edgecolor=C['blue'],linewidth=.9))
txt(493,624,'Prior report',8.1,ha='left')
link((671,624),(714,624));txt(724,624,'Proposed link',8.1,ha='left')

heading(22,'A','Cervical perturbation')
heading(301,'B','Regional medullary tissue')
heading(778,'C','Proposed functional links')

# Stylized C1/C2 symbol; not an anatomical image or a locator of sampled tissue.
rect(20,283,230,267,C['pale'],'#DCE4EB',.8,r=12)
ax.add_patch(Ellipse((136,470),154,57,facecolor=C['bone'],edgecolor=C['boneedge'],linewidth=1.0,zorder=2))
ax.add_patch(Ellipse((136,470),88,23,facecolor=C['pale'],edgecolor=C['boneedge'],linewidth=.7,zorder=3))
rect(91,368,91,51,C['bone'],C['boneedge'],.9,r=15)
rect(122,412,27,64,C['bone'],C['boneedge'],.9,r=10)
ax.plot([91,68,50],[385,380,392],color=C['boneedge'],linewidth=8,solid_capstyle='round')
ax.plot([181,204,222],[385,380,392],color=C['boneedge'],linewidth=8,solid_capstyle='round')
txt(222,470,'C1',8.5,color=C['muted'])
txt(222,410,'C2',8.5,color=C['muted'])
ax.plot([77,77,91],[453,434,434],color=C['red'],linewidth=3.0,solid_capstyle='round',zorder=5)
ax.plot([75,52],[442,426],color=C['red'],linewidth=.75,zorder=5)
txt(51,416,'Implant',8.0,color=C['red'])
txt(135,342,'Atlantoaxial\njoint disorder',9.2,'bold')
txt(135,300,'Metallic implant model',8.6,color=C['muted'])

# Prior expression finding is explicitly separate from current measurements.
rect(300,492,415,58,C['bluefill'],C['blue'],1.0)
txt(507.5,531,'Ang II / AT1-R expression',9.6,'bold',C['blue'])
txt(507.5,508,'Prior report [13]',8.3,color=C['blue'])

rect(300,283,415,184,C['greenfill'],C['green'],1.2,r=12)
txt(507.5,446,'RVLM and adjacent medullary tissue',9.5,'bold',C['green'])
ax.plot([322,693],[429,429],color='#C7DFD7',linewidth=.8)
txt(507.5,403,'Estimated Nox1 / Nox4 mRNA  ↑',10.0,'bold')
txt(507.5,370,'SOD activity  ↓     MDA  ↑',9.6)
txt(507.5,340,'Probe-associated fluorescence  ↑',9.4)
txt(507.5,305,'Model vs sham  ·  day 28  ·  n = 6/group',8.1,color=C['green'])

# Unmeasured functional relationships use dashed outlines and arrows.
rect(780,486,277,64,'white',C['line'],1.0,True)
txt(918.5,518,'NOX-related\nredox signaling?',9.6,'bold')
rect(780,392,277,62,'white',C['line'],1.0,True)
txt(918.5,423,'Increased\nsympathetic drive?',9.4,'bold')
rect(780,283,277,75,C['bluefill'],C['blue'],1.0)
txt(918.5,331,'Elevated blood pressure',9.6,'bold',C['blue'])
txt(918.5,306,'Prior / shared observations [4,13]',8.0,color=C['blue'])
link((252,374),(296,374))
link((719,521),(775,521))
link((719,400),(775,495))
link((918.5,482),(918.5,459))
link((918.5,388),(918.5,363))

# Separate terminal-cohort timelines; no day-28 animal is shown continuing.
ax.plot([20,1058],[254,254],color='#DCE4EA',linewidth=.8)
txt(22,232,'Sampling design',9.0,'bold',C['ink'],ha='left')
x0,x28,x56=220,605,1008
txt(x0,204,'Day 0',8.5,'bold')
txt(x28,204,'Day 28',8.5,'bold')
txt(x56,204,'Day 56',8.5,'bold')
for yy,label,end in [(172,'Sham',x28),(139,'Model',x28),(106,'Restoration',x56)]:
    txt(22,yy,label,8.6,ha='left')
    ax.plot([x0,end],[yy,yy],color='#9BAAB5',linewidth=1.2,zorder=1)
    ax.scatter([x0],[yy],s=13,color='#667E8F',zorder=3)
    ax.scatter([end],[yy],s=23,marker='s',color=C['green'],zorder=3)
    if label!='Restoration':txt(end+19,yy,'Terminal sampling',8.1,ha='left',color=C['green'])
ax.scatter([x28],[106],s=26,marker='D',color=C['red'],zorder=4)
txt(x28,78,'Implant removal',8.1,color=C['red'])
txt(x56,78,'Terminal sampling',8.1,color=C['green'])
txt(540,31,'Terminal times differ; no time-matched second-surgery sham control.',8.8,color=C['muted'])
fig.subplots_adjust(left=.005,right=.995,bottom=.005,top=.995)
export(fig,'Yuan_fig4',{
 'design_version':'2026-10-16 v2',
 'purpose':'Observed regional changes and proposed cardiovascular links',
 'figure_type':'Conventional editable vector schematic, not an experimental image',
 'all_biological_connections':'Dashed arrows denote hypotheses, not established mediation',
 'evidence_labels':['Current measurements','Prior report','Proposed link'],
 'current_observations':'Day28 model vs sham: lower SOD, higher MDA, probe-associated fluorescence and estimated Nox1/Nox4 mRNA',
 'sampling_design':'Three independent terminal-cohort timelines; sham/model day28, restoration day56 after day28 implant removal',
 'experimental_data_or_images_generated':False})


audit['output_files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in OUT.iterdir() if p.suffix in ('.jpg','.tif','.pdf','.svg')}
(OUT/'Figure_Preparation_Audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2))
print(json.dumps({'output':str(OUT),'files':sorted(audit['output_files']),'arrays_sha256':{k:v.get('numeric_arrays_sha256') for k,v in audit['figures'].items()}},indent=2))
