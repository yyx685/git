"""Plot the main figures from the unchanged supporting data CSV files.

Requires Python, NumPy, and Matplotlib. Run from any directory. The data are
located beside this script; vector PDFs are saved in ../Figures. Each point is
one provided value, with deterministic horizontal offsets for visibility;
black marks show the arithmetic mean and sample SD (ddof=1). No statistical
hypotheses are tested and no P values or significance symbols are generated.
Observation order is not an animal identifier or a cross-assay pairing key.
"""
from pathlib import Path
import csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

BASE=Path(__file__).resolve().parent
FIGURES=BASE.parent/'Figures'
FIGURES.mkdir(exist_ok=True)
plt.rcParams.update({
    'font.family':'DejaVu Sans','font.size':9,'axes.labelsize':9,
    'axes.spines.top':False,'axes.spines.right':False,'axes.linewidth':0.8,
    'xtick.direction':'out','ytick.direction':'out',
    'pdf.fonttype':42,'ps.fonttype':42,'savefig.facecolor':'white',
})
GROUPS=['Sham-operated','Model','Restoration']
COLORS=['#35618d','#b44c4e','#557b65']


def panel(ax, data_by_group, letter, ylabel, title=None):
    for index, group in enumerate(GROUPS):
        values=np.asarray(data_by_group[group],dtype=float)
        if values.size!=6 or not np.isfinite(values).all():
            raise ValueError(f'Expected six finite values for {group}')
        offsets=np.linspace(-0.13,0.13,len(values))
        ax.scatter(index+offsets,values,s=24,color=COLORS[index],
                   edgecolors='white',linewidth=0.45,zorder=3)
        ax.errorbar(index,values.mean(),yerr=values.std(ddof=1),fmt='_',
                    markersize=16,color='black',capsize=3,linewidth=1,zorder=2)
    ax.set_xticks([0,1,2],['Sham','Model','Rest.'])
    ax.set_xlim(-0.4,2.4)
    ax.set_ylim(bottom=0)
    ax.set_ylabel(ylabel)
    ax.text(-0.20,1.04,letter,transform=ax.transAxes,fontweight='bold',fontsize=12)
    if title:
        ax.set_title(title,fontstyle='italic',fontsize=11,pad=10)

with (BASE/'S1_Data_RVLM_Processed_Values.csv').open(encoding='utf-8-sig',newline='') as handle:
    biochemistry=list(csv.DictReader(handle))
fig,axes=plt.subplots(1,3,figsize=(7.0,3.3))
for ax,endpoint,letter,ylabel in zip(axes,['SOD','MDA','ROS'],'ABC',[
        'SOD (U/mg protein)','MDA (nmol/mg protein)',
        'Protein-normalized fluorescence (AU)']):
    panel(ax,{group:[float(row['Processed_value']) for row in biochemistry
                     if row['Endpoint']==endpoint and row['Group']==group]
              for group in GROUPS},letter,ylabel)
fig.subplots_adjust(left=0.08,right=0.985,top=0.88,bottom=0.17,wspace=0.54)
fig.savefig(FIGURES/'Fig1.pdf',metadata={'Title':'Medullary redox-related measurements'})
plt.close(fig)

with (BASE/'S2_Data_RTqPCR_Animal_Paired_Values.csv').open(encoding='utf-8-sig',newline='') as handle:
    qpcr=list(csv.DictReader(handle))
fig,axes=plt.subplots(1,2,figsize=(6.0,3.3))
for ax,target,letter in zip(axes,['Nox1','Nox4'],'AB'):
    panel(ax,{group:[float(row['normalized_expression']) for row in qpcr
                     if row['target']==target and row['group']==group]
              for group in GROUPS},letter,'Relative mRNA abundance',target)
fig.subplots_adjust(left=0.11,right=0.985,top=0.85,bottom=0.17,wspace=0.43)
fig.savefig(FIGURES/'Fig2.pdf',metadata={'Title':'Nox1 and Nox4 relative mRNA abundance'})
plt.close(fig)
print('Saved two vector figures from unchanged data; no statistical inference was performed.')
