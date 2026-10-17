"""Adapt the MMR figure style to the verified quantitative inputs.

Requires Python, NumPy, Matplotlib and Pillow. Place this script beside the
unchanged supporting CSV/JSON files or specify --data-dir. Outputs default to
the current directory; --output-dir selects another directory.
No statistical tests are performed.
Inferential annotations are read from the previously verified JSON results.
"""
from pathlib import Path
import csv, json, hashlib, argparse
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.ticker import MaxNLocator
from PIL import Image

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--data-dir', type=Path, default=Path(__file__).resolve().parent,
                    help='Directory containing the unchanged supporting CSV and JSON files')
parser.add_argument('--output-dir', type=Path, default=Path.cwd(),
                    help='Output directory (default current working directory)')
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
 'date':'2026-10-17', 'statistical_tests_performed':False,
 'experimental_images_generated_or_edited':False, 'input_files':{}, 'figures':{},
 'visual_review':'pending'}
for name in ['S1_Data_RVLM_Processed_Values.csv', 'S2_Data_RTqPCR_Animal_Paired_Values.csv',
             'S3_File_RVLM_Statistical_Outputs.json', 'S4_File_RTqPCR_Statistical_Outputs.json']:
    audit['input_files'][name] = {'sha256':sha(SOURCE/name), 'modified':False}

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
    ax.set_xticks([0,1,2],['Sham\n(week 4)','Model\n(week 4)','Rest.\n(week 8)'])
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
 'changes':'Retained black/light-gray/dark-gray bars and sample SD; overlaid six source records (reported biological n=6); fluorescence unit corrected to AU; exact source comparisons used.'}
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
 'changes':'Preserved bar+SD design; retained Cq-derived Nox4 assay estimates; target specificity is unconfirmed; overlaid six values; star annotations use exact Holm-adjusted P thresholds; sampling labels use weeks.'}
fig,axs=plt.subplots(1,2,figsize=(6.3,3.8))
for ax,target,letter in zip(axs,['Nox1','Nox4'],'AB'):
    data={g:[float(r['normalized_expression']) for r in qpcr if r['target']==target and r['group']==g] for g in GROUPS}
    qpcr_record['arrays'][target]=data
    gene=next(g for g in qpcr_stats['genes'] if g['gene']==target)
    for g,a in data.items():
        summary=next(s for s in gene['groups'] if s['group']==g)['fold_statistics']
        assert np.isclose(np.mean(a),summary['mean']) and np.isclose(np.std(a,ddof=1),summary['sample_sd'])
    base_panel(ax,data,letter,'Normalized RT-qPCR estimate',target)
    highest=max(max(a) for a in data.values());span=highest*1.40
    for i,(num,den,x1,x2) in enumerate([('Model','Sham-operated',0,1),('Restoration','Model',1,2)]):
        c=next(c for c in qpcr_stats['comparisons'] if c['gene']==target and c['numerator_group']==num and c['denominator_group']==den)
        p=c['p_holm_18_test_family'];label='***' if p<.001 else '**' if p<.01 else '*' if p<.05 else 'ns'
        bracket(ax,x1,x2,highest+(i*.105+.11)*span,label,span)
        qpcr_record.setdefault('annotations',[]).append({'target':target,'comparison':c['comparison'],'p_holm_18':p,'label':label})
    ax.set_ylim(0,span)
fig.subplots_adjust(left=.105,right=.985,bottom=.19,top=.82,wspace=.38)
qpcr_record['numeric_arrays_sha256']=hashlib.sha256(json.dumps(qpcr_record['arrays'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
export(fig,'Yuan_fig2',qpcr_record)

audit['output_files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in OUT.iterdir() if p.suffix in ('.jpg','.tif','.pdf','.svg')}
(OUT/'Figure_Preparation_Audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2))
print(json.dumps({'output':str(OUT),'files':sorted(audit['output_files']),'arrays_sha256':{k:v.get('numeric_arrays_sha256') for k,v in audit['figures'].items()}},indent=2))
