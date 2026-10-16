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
                    help='Optional original H&E JPEG to copy byte for byte as Yuan_fig1.jpg')
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
    if he_image != OUT/'Yuan_fig1.jpg':
        shutil.copy2(he_image, OUT/'Yuan_fig1.jpg')
    assert sha(he_image) == sha(OUT/'Yuan_fig1.jpg')
    with Image.open(OUT/'Yuan_fig1.jpg') as im:
        audit['figures']['Yuan_fig1'] = {'source':str(he_image),
          'bytes_identical':True, 'sha256':sha(OUT/'Yuan_fig1.jpg'), 'dimensions':list(im.size),
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
export(fig,'Yuan_fig2',bio_record)

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
export(fig,'Yuan_fig3',qpcr_record)

# Conventional vector diagram; no experimental image generation or manipulation.
fig,ax=plt.subplots(figsize=(10,5.7));ax.set_xlim(0,10);ax.set_ylim(0,5.7);ax.axis('off')
def box(x,y,w,h,text,fc,ec,fs=10,bold=False):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.10,rounding_size=0.12',
                               linewidth=1.3,facecolor=fc,edgecolor=ec,zorder=1))
    ax.text(x+w/2,y+h/2,text,ha='center',va='center',fontsize=fs,
            fontweight='bold' if bold else 'normal',linespacing=1.25,zorder=2)
def proposed(start,end,labelpos):
    ax.add_patch(FancyArrowPatch(start,end,arrowstyle='->',mutation_scale=11,
                  linewidth=1.1,color='#606060',linestyle=(0,(4,3)),zorder=3))
    ax.text(*labelpos,'Proposed',ha='center',va='center',fontsize=8,color='#4b4b4b',
            bbox={'facecolor':'white','edgecolor':'none','pad':1},zorder=4)
ax.text(5,5.44,'Proposed hypothesis — causal links not established',ha='center',va='center',
        fontsize=15,fontweight='bold')
box(.15,3.20,2.12,1.40,'Atlantoaxial\njoint disorder\n\nMetallic implant model','#edf3fb','#5079a3',10,True)
box(2.95,1.08,4.05,3.76,'','#edf7ee','#548462')
ax.text(4.975,4.48,'Ventrolateral medullary blocks\ncontaining RVLM and adjacent tissue',
        ha='center',va='center',fontsize=11,fontweight='bold')
box(3.25,3.36,3.45,.57,'Prior report\nAng II / AT1R expression','#ffffff','#8cae94',10)
box(3.25,2.16,3.45,.74,'Current regional observations\nNox1 / Nox4 mRNA estimates\nSOD, MDA and probe fluorescence','#ffffff','#8cae94',10)
box(3.25,1.27,3.45,.48,'Possible redox-sensitive neural regulation\nMechanism not tested here','#ffffff','#8cae94',9)
box(7.72,2.15,2.05,1.36,'Sympathetic outflow /\nblood-pressure regulation\n\nFunctional mediation\nnot established here','#fcf0e8','#bd7146',10,True)
box(.15,.85,2.12,1.54,'Implant removal: day 28\nRestoration: day 56\nOther groups: day 28\n\nTime/second-surgery\nconfounding remains\nNo reversal established','#fff8e8','#c19b3b',10)
proposed((2.37,3.90),(2.95,3.90),(2.65,4.10))
proposed((4.975,3.26),(4.975,3.00),(5.43,3.13))
proposed((4.975,2.06),(4.975,1.85),(5.44,1.98))
proposed((7.10,2.85),(7.62,2.85),(7.36,3.05))
proposed((1.21,2.49),(1.21,3.10),(1.21,2.78))
ax.text(5,.30,'All dashed arrows denote untested hypotheses. No serum findings or therapeutic reversal are asserted.',
        ha='center',va='center',fontsize=9,color='#404040')
fig.subplots_adjust(left=.015,right=.985,bottom=.01,top=.99)
export(fig,'Yuan_fig4',{'source_visual_style':'lyk mmr期刊.docx Figure 7, original left–center–right box arrangement',
 'all_connections':'Dashed arrows labelled Proposed',
 'content_changes':['Removed unmatched serum-results box','Removed partially reverses assertion',
  'Distinguished previous Ang II/AT1R report from current regional redox and mRNA observations',
  'Regional block includes adjacent tissue; no pure-RVLM specificity asserted',
  'Displayed day28/day56 and second-surgery confounding'],
 'experimental_data_or_images_generated':False})

audit['output_files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in OUT.iterdir() if p.suffix in ('.jpg','.tif','.pdf','.svg')}
(OUT/'Figure_Preparation_Audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2))
print(json.dumps({'output':str(OUT),'files':sorted(audit['output_files']),'arrays_sha256':{k:v.get('numeric_arrays_sha256') for k,v in audit['figures'].items()}},indent=2))
