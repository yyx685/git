"""Reproduce the descriptive archived blood-pressure figure from its source CSVs.

Requires Python, Matplotlib, and Pillow. Run from any directory; inputs and
output are located beside this script by default. Optional --data-dir and
--output-dir arguments override these paths. Source rows are display records, not
verified independent animals. This script performs no statistical inference.
"""
from pathlib import Path
from collections import defaultdict
import csv
import argparse
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--data-dir',type=Path,default=Path(__file__).resolve().parent)
parser.add_argument('--output-dir',type=Path,default=None)
args=parser.parse_args()
BASE=args.data_dir.resolve()
OUTPUT=args.output_dir.resolve() if args.output_dir else Path(__file__).resolve().parent
OUTPUT.mkdir(parents=True,exist_ok=True)
from matplotlib import font_manager
font_manager.findfont('Arial',fallback_to_default=False)
records = defaultdict(dict)
with (BASE/'S3_Data_Archived_BP_Recorded_Values.csv').open(encoding='utf-8-sig',newline='') as handle:
    for item in csv.DictReader(handle):
        key=item['source_record_key'];block=item['source_block']
        if key not in records[block]:records[block][key]=[None]*5
        raw=item['value_recorded']
        records[block][key][int(item['week'])]=None if raw=='' else float(raw)

restoration={}
with (BASE/'S4_Data_Archived_BP_Entered_Summaries.csv').open(encoding='utf-8-sig',newline='') as handle:
    for item in csv.DictReader(handle):
        if item['group_label_as_recorded']=='复位组' and item['value_recorded']!='':
            week=int(item['time_label'].removesuffix('W'))
            restoration[week]=float(item['value_recorded'])

plt.rcParams.update({'font.family':'Arial','pdf.fonttype':42,'ps.fonttype':42,'font.size':11,'axes.titlesize':12,'axes.labelsize':11,
                     'axes.spines.top':False,'axes.spines.right':False,'axes.linewidth':1.0,
                     'xtick.direction':'out','ytick.direction':'out','savefig.facecolor':'white'})
fig,axes=plt.subplots(2,2,figsize=(8.4,7.4))
blocks=[('model','Model label','#376D93'),('control','Control label','#7C6F86'),
        ('sham','Sham-operation label','#527E70')]
for index,(block,title,color) in enumerate(blocks):
    ax=axes.flat[index];rows=list(records[block].values())
    for rowindex,values in enumerate(rows):
        offset=(rowindex-(len(rows)-1)/2)*0.009
        ax.plot([w+offset for w in range(5)],
                [float('nan') if v is None else v for v in values],
                '-o',color=color,alpha=0.62,linewidth=0.72,markersize=3.6,markeredgewidth=0)
    counts=[sum(r[w] is not None for r in rows) for w in range(5)]
    ax.set_title(title,loc='left',fontweight='bold',pad=11)
    ax.text(-0.15,1.065,'ABC'[index],transform=ax.transAxes,fontweight='bold',fontsize=17)
    ax.set_xlim(-0.25,4.25);ax.set_ylim(55,180);ax.set_xticks(range(5))
    ax.set_xlabel('Week (as recorded)');ax.set_ylabel('Recorded pressure (mmHg)')
    ax.text(0,-0.26,f"Source rows: {len(rows)}   Values/week: "+', '.join(map(str,counts)),
            transform=ax.transAxes,fontsize=8.5,color='#444444')
    ax.grid(axis='y',color='#E4E4E4',linewidth=0.6)

ax=axes.flat[3];weeks=sorted(restoration)
ax.scatter(weeks,[restoration[w] for w in weeks],s=48,color='#A77539',edgecolor='white',linewidth=0.6,zorder=3)
ax.set_title('Restoration label',loc='left',fontweight='bold',pad=11)
ax.text(-0.15,1.065,'D',transform=ax.transAxes,fontweight='bold',fontsize=17)
ax.set_xlim(4.75,8.25);ax.set_ylim(55,180);ax.set_xticks([5,6,7,8])
ax.set_xlabel('Week (as recorded)');ax.set_ylabel('Recorded pressure (mmHg)')
ax.text(0,-0.23,'Four entered summaries\nAnimal n and dispersion unavailable',
        transform=ax.transAxes,fontsize=8.5,color='#444444',linespacing=1.3,va='top')
ax.grid(axis='y',color='#E4E4E4',linewidth=0.6)
fig.subplots_adjust(left=0.1,right=0.985,bottom=0.12,top=0.94,wspace=0.35,hspace=0.52)
figure_path=OUTPUT/'S2_Fig_Archived_BP_Records.tif'
fig.savefig(OUTPUT/'Supplementary_Fig_S2.pdf',metadata={'Title':'Descriptive archived blood-pressure records'})
fig.savefig(figure_path,dpi=600,pil_kwargs={'compression':'tiff_lzw'})
with Image.open(figure_path) as rendered:
    rgb=rendered.convert('RGB')
rgb.save(figure_path,compression='tiff_lzw',dpi=(600,600))
plt.close(fig)
print('Saved descriptive archive figure; no inferential statistics were performed.')
