"""Recreate experiment figures from the supplied numeric records (no model runs)."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.lines import Line2D
from matplotlib.ticker import LogLocator, NullFormatter

import argparse
ROOT=Path(__file__).resolve().parents[1];D=ROOT/'data'
parser=argparse.ArgumentParser();parser.add_argument('--output', type=Path, required=True)
OUT=parser.parse_args().output;OUT.mkdir(parents=True, exist_ok=True)
for p in (Path(__file__).parent/'fonts').glob('*.ttf'):font_manager.fontManager.addfont(str(p))
plt.rcParams.update({'font.family':'serif','font.serif':['Tinos','Times New Roman','DejaVu Serif'],
 'mathtext.fontset':'stix','font.size':9,'axes.labelsize':9,'axes.titlesize':9,
 'xtick.labelsize':8,'ytick.labelsize':8,'legend.fontsize':8,'axes.linewidth':.8,
 'pdf.fonttype':42,'svg.fonttype':'none','figure.facecolor':'white','axes.facecolor':'white'})
BLUE='#3077ae';GREEN='#43856b';ORANGE='#cf681e';GREY='#686b70'
NAMES={}
AUDIT=[]
def clean(ax,which='y'):
    ax.spines[['top','right']].set_visible(False);ax.set_axisbelow(True)
    ax.grid(axis=which,color='#d6dadd',lw=.6,ls=':');ax.tick_params(length=3,width=.8)
def bottom(fig,ax,s,dy=.11):
    b=ax.get_position();fig.text((b.x0+b.x1)/2,b.y0-dy,s,ha='center',va='top',fontsize=9.5)
def save(fig,stem):
    fig.canvas.draw();ren=fig.canvas.get_renderer();outside=[]
    hidden_ticks=set()
    for ax in fig.axes:
        for axis,lim in [(ax.xaxis,ax.get_xlim()),(ax.yaxis,ax.get_ylim())]:
            lo,hi=sorted(lim)
            for tick in axis.get_major_ticks()+axis.get_minor_ticks():
                if not lo<=tick.get_loc()<=hi:hidden_ticks.update([tick.label1,tick.label2])
    for t in fig.findobj(match=plt.Text):
        if t in hidden_ticks or not t.get_text().strip() or not t.get_visible():continue
        b=t.get_window_extent(ren)
        if b.x0< -3 or b.x1>fig.bbox.x1+3 or b.y0< -3 or b.y1>fig.bbox.y1+3:outside.append(t.get_text())
    AUDIT.append({'figure':stem,'outside_canvas':outside})
    for ext in ['pdf','svg','png']:fig.savefig(OUT/f'{stem}.{ext}',bbox_inches='tight',pad_inches=.035,dpi=220)
    plt.close(fig)

def supplement_config():
    bank=pd.read_csv(D/'candidate_subset.csv');upd=pd.read_csv(D/'adaptation_updates.csv');cal=pd.read_csv(D/'margin_calibration.csv')
    print('Configuration columns',bank.columns.tolist(),cal.columns.tolist())
    fig,axs=plt.subplots(1,3,figsize=(7.1,2.6));fig.subplots_adjust(left=.08,right=.99,top=.96,bottom=.31,wspace=.5)
    x=bank.candidate_records.to_numpy();y=bank.forecast_mse.to_numpy()*100
    axs[0].plot(x,y,'o-',color=BLUE,markersize=4,lw=1);axs[0].set_xlabel('Candidate records');axs[0].set_xticks(x);axs[0].set_ylabel(r'MSE ($\times10^{-2}$)')
    axs[1].plot(upd.adaptation_steps,upd.forecast_mse*100,'s-',color=GREEN,markersize=4,lw=1);axs[1].set_xlabel('Adaptation updates');axs[1].set_ylabel(r'MSE ($\times10^{-2}$)')
    losscol='cal_MSE';taucol='minimum_improvement'
    axs[2].plot(cal[taucol],cal[losscol]*100,'o-',color=BLUE,lw=1,markersize=4);axs[2].axvline(.05,color=ORANGE,ls='--',lw=.8);axs[2].set_xlabel(r'Relative margin $\tau$');axs[2].set_ylabel(r'Calibration MSE ($\times10^{-2}$)');axs[2].set_xticks([0,.1,.2])
    for ax,t in zip(axs,['(a) Candidate subset','(b) Update count','(c) Margin calibration']):clean(ax);bottom(fig,ax,t,.20)
    save(fig,'figS1')


supplement_config()
