"""Rebuild the paper's experimental figures from the released CSV files.

Figure 5 uses the original overall-performance plotting function with the
current data and reviewed axis limits. Figures 6, 7 and 9 use the accepted
compact/style-restoration drawing functions. Figure 8 uses its reviewed
source-sensitivity drawing code. No model training or resampling is done.
"""
from __future__ import annotations
import argparse, csv, hashlib, math
from collections import Counter
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.ticker import FormatStrFormatter, MultipleLocator
from matplotlib.patches import Patch
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for font in (HERE / 'fonts').glob('*.ttf'):
    font_manager.fontManager.addfont(str(font))

FIGURE_SIZE = (6.62, 4.38)
METHODS = ('PT+FT', 'MeDeT-style', 'Scratch50', 'Meta+NAS-lite',
           'Zero-shot NAS', 'Zero-shot NAS+FT', 'H-Meta-NAS-based', 'MSA-DTI (ours)')
COLORS = ('#6e8fb3', '#8db8b0', '#c6c2bd', '#d9a25f', '#c77979', '#b39bbc', '#8f99a6', '#4f7f5c')
CANVAS_SIZES = {'fig6': (6.0, 3.0)}

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def rows(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def panel_data(path):
    records = rows(path)
    expected = ['PT+FT', 'MeDeT-style', 'Scratch50', 'Meta+NAS-lite',
                'Zero-shot NAS', 'Zero-shot NAS+FT', 'H-Meta-NAS-based', 'MSA-DTI']
    if [r['Method'] for r in records] != expected:
        raise ValueError('Unexpected method order in overall.csv')
    specifications = [
      ('MAE','MAE',(0,17.0),(0,4,8,12)),
      ('MSE','MSE',(0,3.8),(0.0,0.8,1.6,2.4,3.2)),
      ('Worst-10% error','Worst10',(0,16),(0,4,8,12,16)),
      ('CVaR90','CVaR90',(0,40),(0,10,20,30,40)),
    ]
    return tuple((title, tuple(float(r[key])*100 for r in records), lim, ticks)
                 for title,key,lim,ticks in specifications)

def save(fig, folder, stem, provenance=None):
    folder.mkdir(parents=True, exist_ok=True)
    metadata = {'Title': stem, 'Author': 'MSA-DTI figure reporting', 'CreationDate': None, 'ModDate': None}
    fig.savefig(folder / (stem + '.pdf'), metadata=metadata, facecolor='white')
    fig.savefig(folder / (stem + '.svg'), facecolor='white')
    fig.savefig(folder / (stem + '.png'), dpi=600, facecolor='white')
    plt.close(fig)

def _save(fig, output_dir, stem, *, tight=False, semantic=None):
    output_dir.mkdir(parents=True, exist_ok=True)
    crop = {'bbox_inches': 'tight', 'pad_inches': .03} if tight else {}
    fig.patch.set_facecolor('white')
    for axis in fig.axes:
        axis.set_facecolor('white')
    metadata = {'Title':stem, 'Author':'Released deterministic reporting code',
                'Subject':'Public CSV figure reconstruction', 'CreationDate':None, 'ModDate':None}
    fig.savefig(output_dir / (stem + '.pdf'), metadata=metadata, facecolor='white', edgecolor='none', transparent=False, **crop)
    fig.savefig(output_dir / (stem + '.svg'), facecolor='white', edgecolor='none', transparent=False, **crop)
    fig.savefig(output_dir / (stem + '.png'), dpi=600, facecolor='white', edgecolor='none', transparent=False, **crop)
    plt.close(fig)
    return {'status':'PASS'}


def build_figure(canonical_results: str | Path):
    """Build the frozen-layout Figure 5 from the canonical result row."""
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8.0,
            "axes.labelsize": 8.5,
            "xtick.labelsize": 7.5,
            "ytick.labelsize": 7.5,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )
    fig, axes = plt.subplots(2, 2, figsize=FIGURE_SIZE)
    fig.subplots_adjust(left=0.180, right=0.970, bottom=0.180, top=0.840, wspace=0.620, hspace=0.720)

    y = np.arange(len(METHODS))
    for index, (ax, (panel, values, xlim, ticks)) in enumerate(zip(axes.flat, panel_data(canonical_results))):
        bars = ax.barh(y, values, height=0.68, color=COLORS, edgecolor="#5d5d5d", linewidth=0.55)
        bars[-1].set_hatch("//")
        ax.set_yticks(y, METHODS)
        ax.invert_yaxis()
        ax.set_xlim(*xlim)
        ax.set_xticks(ticks)
        ax.xaxis.grid(True, linestyle=":", color="#d7d7d7", linewidth=0.55)
        ax.set_axisbelow(True)
        ax.tick_params(axis="both", length=4, width=0.8, pad=2)
        for spine in ax.spines.values():
            spine.set_linewidth(0.8)
            spine.set_color("black")
        for label in ax.get_yticklabels():
            if label.get_text() == "MSA-DTI (ours)":
                label.set_fontweight("bold")

        offset = (xlim[1] - xlim[0]) * 0.030
        for pos, value in enumerate(values):
            ax.text(
                value + offset,
                pos,
                f"{value:.3f}",
                va="center",
                ha="left",
                clip_on=True,
                fontsize=7.0,
                fontweight="bold" if pos == len(values) - 1 else "normal",
            )
        ax.set_xlabel(r"Error ($\times 10^{-2}$); lower is better", labelpad=6)
        ax.text(0.5, -0.50, f"({chr(ord('a') + index)}) {panel}", transform=ax.transAxes, ha="center", va="top", fontsize=8.0)

    legend_handles = [
        Patch(facecolor=color, edgecolor="#5d5d5d", linewidth=0.55, hatch="//" if method == "MSA-DTI (ours)" else "", label=method)
        for method, color in zip(METHODS, COLORS)
    ]
    fig.legend(
        handles=(legend_handles[0], legend_handles[1], legend_handles[2], legend_handles[3], legend_handles[4], legend_handles[5], legend_handles[7], legend_handles[6]),
        ncol=4,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.995),
        frameon=False,
        fontsize=7.5,
        handlelength=1.35,
        handleheight=0.7,
        handletextpad=0.55,
        columnspacing=1.45,
        borderaxespad=0.0,
    )
    return fig


def _read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"Empty figure data: {path}")
    return rows


def _style() -> None:
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["DejaVu Serif", "Tinos", "Times New Roman"],
            "mathtext.fontset": "stix",
            "font.size": 9.0,
            "axes.titlesize": 9.0,
            "axes.labelsize": 9.0,
            "xtick.labelsize": 8.0,
            "ytick.labelsize": 8.0,
            "legend.fontsize": 7.7,
            "axes.linewidth": 0.8,
            "lines.linewidth": 1.1,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
        }
    )


def plot_fig6(data_dir: Path, output_dir: Path) -> dict[str, Any]:
    rows = _read(data_dir / "fig6_paired_instantiation_data.csv")
    if len(rows) != 120:
        raise ValueError("Fig. 6 requires exactly 120 paired cases")
    categories = (
        ("beneficial alternative", "Beneficial alternative", "#0072B2", "o"),
        ("reference retained", "Reference retained", "#666666", "s"),
        ("harmful alternative", "Harmful alternative", "#D55E00", "X"),
    )
    counts = Counter(row["selection_category"] for row in rows)
    _style()
    fig, axes = plt.subplots(1, 2, figsize=CANVAS_SIZES["fig6"])
    fig.subplots_adjust(left=0.085, right=0.985, top=0.78, bottom=0.25, wspace=0.14)
    for ax, reference_key, proposed_key in (
        (axes[0], "pt_ft_mse", "proposed_mse"),
        (axes[1], "pt_ft_worst10", "proposed_worst10"),
    ):
        values = [100.0 * float(row[key]) for row in rows for key in (reference_key, proposed_key)]
        upper = max(values) * 1.055
        ax.plot((0, upper), (0, upper), color="#222222", lw=0.75, ls=(0, (3, 2)), zorder=1)
        for key, label, color, marker in categories:
            subset = [row for row in rows if row["selection_category"] == key]
            ax.scatter(
                [100.0 * float(row[reference_key]) for row in subset],
                [100.0 * float(row[proposed_key]) for row in subset],
                s=19 if marker != "X" else 27,
                marker=marker,
                facecolors="white" if marker != "X" else color,
                edgecolors=color,
                linewidths=0.8,
                label=f"{label} ({counts[key]})",
                zorder=2,
            )
        ax.set_xlim(0, upper)
        ax.set_ylim(0, upper)
        ax.set_aspect("equal", adjustable="box")
        ax.set_xlabel(r"PT+FT ($\times 10^{-2}$)")
        ax.set_ylabel(r"MSA-DTI ($\times 10^{-2}$)")
        ax.grid(color="#E1E1E1", lw=0.45, ls=(0, (2, 2)))
        ax.spines[["top", "right"]].set_visible(False)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=3, frameon=False, bbox_to_anchor=(0.5, 0.985))
    fig.canvas.draw()
    for ax, title in zip(axes, ("(a) Test MSE", "(b) Test Worst-10% error")):
        position = ax.get_position()
        fig.text(position.x0 + position.width / 2, 0.035, title, ha="center")
    return _save(fig, output_dir, "fig6", tight=True)


def style():
    plt.rcParams.update({'font.family':'serif','font.serif':['Tinos'],'mathtext.fontset':'stix',
        'font.size':9,'axes.labelsize':9,'axes.titlesize':9,'xtick.labelsize':8,'ytick.labelsize':8,
        'legend.fontsize':7.6,'axes.linewidth':.8,'lines.linewidth':1.25,'pdf.fonttype':42,
        'ps.fonttype':42,'figure.facecolor':'white','axes.facecolor':'white','savefig.facecolor':'white'})


def canvas(w,h):return plt.figure(figsize=(w/72,h/72))


def pdfaxis(fig, w,h,x0,y0,x1,y1):
    return fig.add_axes([x0/w,(h-y1)/h,(x1-x0)/w,(y1-y0)/h])


def forest(data, folder, fixture=False):
    rr=rows(data);style();w,h=467.69099,177.5294;fig=canvas(w,h)
    axes=[pdfaxis(fig,w,h,77.160,2.160,256.008,134.136),pdfaxis(fig,w,h,321.008,2.160,461.531,134.136)]
    xmax=30 if fixture else 70
    for i,(ax,panel,color,marker) in enumerate(zip(axes,['H/K','Center type' if fixture else 'Deployment budget'],['#1f77b4','#43a581'],['o','s'])):
        r=[x for x in rr if x['panel']==panel];means=np.array([float(x['gain_percent']) for x in r]);lo=np.array([float(x['ci_low_percent']) for x in r]);hi=np.array([float(x['ci_high_percent']) for x in r]);y=np.arange(len(r))[::-1]
        assert np.all(lo>=0) and np.all(hi<=xmax),'Axis must include every CI'
        ax.errorbar(means,y,xerr=np.vstack([means-lo,hi-means]),fmt=marker,color=color,mfc=color,mec=color,markersize=5,markeredgewidth=1,capsize=3,lw=1.25)
        for yi,m in zip(y,means):ax.annotate(str(Decimal(str(m)).quantize(Decimal('.1'),rounding=ROUND_HALF_UP)),(m,yi),xytext=(3,3),textcoords='offset points',color=color,va='bottom',fontsize=7.2)
        labels=[]
        for x in r:
            if i==0:
                hh,kk=x['group'].split(', ');labels.append('$'+hh+r',\ '+kk+'$'+f" (n={x.get('cases','30')})")
            else:labels.append(('Type '+x['group'] if fixture else x['group'])+f" (n={x.get('cases','120')})")
        ax.set_yticks(y,labels);ax.set_ylim(-.08*(len(r)-1),1.15*(len(r)-1));ax.set_xlim(0,xmax);ax.xaxis.set_major_locator(MultipleLocator(5 if fixture else 10))
        ax.set_xlabel('MSE reduction relative to PT+FT (%)',labelpad=4)
        ax.grid(axis='x',color='#d9d9d9',lw=.6,ls=':');ax.set_axisbelow(True);ax.spines[['top','right']].set_visible(False)
        ax.tick_params(axis='both',width=.8,length=3.5,pad=4)
    for x,caption in [(166.584,'(a) Horizon and support size'),(391.2695,'(b) Target center type' if fixture else '(b) Deployment budget')]:fig.text(x/w,5.0/h,caption,ha='center',va='bottom',fontsize=8.4)
    save(fig,folder,'fig7',dict(source_mode='original PDF style restored; matching historical script not recovered',data_sha256=sha(data),all_ci_visible=True,x_limits=[0,xmax],uncertainty='existing ancestor-VM bootstrap intervals, no resampling'))


def resource(data, folder, fixture=False):
    filt=rows(data/('fig8_candidate_filtering_data.csv' if fixture else 'filtering.csv'))
    select=rows(data/('fig8_architecture_selection_data.csv' if fixture else 'selection.csv'))
    budgets=[r['budget_tier'] for r in filt]
    if fixture:
        names=list(dict.fromkeys(r['model_configuration'] for r in select));matrix=np.array([[float(next(r['selection_rate'] for r in select if r['model_configuration']==name and r['budget_tier']==b)) for b in budgets] for name in names])*100
    else:
        model_ids=['A55','A56','A57 (C1)','A57 (PT)','A1','A6','A13']
        names=['A55 (reference)','A56','A57-C1','A57-PT','A1','A6','A13']
        matrix=np.array([[float(next(r['selection_rate'] for r in select if r['model_configuration']==q and r['budget_tier']==b)) for b in budgets] for q in model_ids])*100
    assert np.allclose(matrix.sum(axis=0),100)
    style();w,h=454.0,156.5;fig=canvas(w,h)
    a=pdfaxis(fig,w,h,26,18,152,116);b=pdfaxis(fig,w,h,223,18,403,116);c=pdfaxis(fig,w,h,411,18,415,116)
    xx=np.arange(3);width=.34
    for delta,values,fill,edge,label in [(-width/2,[float(r['initialized_candidates_per_case']) for r in filt],'#bdbdbd','#666666','Candidates before filtering'),(width/2,[float(r['feasible_candidates_per_case_mean']) for r in filt],'#4c78a8','#3a5f85','Feasible candidates')]:
        bars=a.bar(xx+delta,values,width,color=fill,edgecolor=edge,linewidth=.7,label=label);a.bar_label(bars,fmt='%.0f',padding=2,fontsize=7.2)
    ticks=[r['budget_tier'].title()+f"\n(n={r['case_count']})" for r in filt]
    a.set_xticks(xx,ticks);a.set_ylim(0,8.4);a.set_yticks(range(9));a.set_ylabel('Candidates per case',labelpad=4)
    a.set_axisbelow(True);a.grid(axis='y',color='#d9d9d9',lw=.6,ls=':');a.spines[['top','right']].set_visible(False)
    a.legend(frameon=False,ncol=2,loc='lower left',bbox_to_anchor=(-.04,1.04),borderaxespad=0,handlelength=1,handletextpad=.5,columnspacing=1.2,fontsize=7.6)
    vmax=50
    assert matrix.max()<=vmax,'Do not silently saturate new values'
    im=b.imshow(matrix,cmap='GnBu',vmin=0,vmax=vmax,aspect='auto',interpolation='nearest')
    b.set_xticks(xx,ticks);b.set_yticks(range(len(names)),names)
    for i in range(len(names)):
        for j in range(3):b.text(j,i,f'{matrix[i,j]:.1f}%',ha='center',va='center',fontsize=7.2,color='white' if matrix[i,j]>=vmax*.55 else '#333333')
    cb=fig.colorbar(im,cax=c,ticks=range(0,vmax+1,10));cb.set_label('Selection rate (%)',labelpad=4)
    for ax in [a,b,c]:ax.tick_params(axis='both',width=.8,length=3.5,pad=4)
    for ax,caption in [(a,'(a) Candidate filtering'),(b,'(b) Final model selection')]:fig.text(ax.get_position().x0+ax.get_position().width/2,4.3/h,caption,ha='center',va='bottom',fontsize=8.4)
    save(fig,folder,'fig9',dict(source_mode='original PDF style restored; matching historical script not recovered',data_sha256={p.name:sha(p) for p in [data/('fig8_candidate_filtering_data.csv' if fixture else 'filtering.csv'),data/('fig8_architecture_selection_data.csv' if fixture else 'selection.csv')]},model_records=names,colormap='GnBu',color_limits=[0,vmax],all_candidates_counted=True))


def plot_fig8(source_csv, output_dir):
    data = pd.read_csv(source_csv).set_index("variant")
    if not data.index.is_unique or len(data) != 6:
        raise ValueError("Expected six source-sensitivity conditions")
    plt.rcParams.update({
        "font.family": "serif", "font.serif": ["Tinos"], "mathtext.fontset": "stix",
        "font.size": 9, "axes.labelsize": 9, "axes.titlesize": 9,
        "xtick.labelsize": 8, "ytick.labelsize": 8,
        "axes.linewidth": .8, "lines.linewidth": 1.25,
        "pdf.fonttype": 42, "ps.fonttype": 42,
        "figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white",
    })
    width, height = 464.0, 177.5
    fig = plt.figure(figsize=(width / 72, height / 72))


    def axes_at(left, top, right, bottom):
        return fig.add_axes([left / width, (height - bottom) / height,
                             (right - left) / width, (bottom - top) / height])


    left = axes_at(40, 10, 222, 127)
    right = axes_at(270, 10, 452, 127)
    blue, green = "#1f77b4", "#43a581"
    sizes = np.array([5, 10, 15, 20])
    seeds = [2904, 2905, 2906]
    pool_mse = np.array([data.loc[f"source{n}_seed2904", "MSE"] for n in sizes]) * 100
    seed_mse = np.array([data.loc[f"source20_seed{s}", "MSE"] for s in seeds]) * 100

    pool_line, = left.plot(sizes, pool_mse, color=blue, marker="o", markersize=5,
                           linewidth=1.35, zorder=3)
    left.set(xlim=(4.2, 20.8), ylim=(0, 1.05),
             xlabel="Source-training VMs", ylabel=r"MSE ($\times 10^{-2}$)")
    left.set_xticks(sizes)
    left.set_yticks(np.arange(0, 1.01, .2))
    left.yaxis.set_major_formatter(FormatStrFormatter("%.1f"))
    left.grid(axis="y", color="#d9d9d9", linewidth=.6, linestyle=":")
    for x, value in zip(sizes, pool_mse):
        right_of_point = x in sizes[:2]
        left.annotate(f"{value:.4f}", (x, value), xytext=(5 if right_of_point else 0, 5),
                      textcoords="offset points", ha="left" if right_of_point else "center", va="bottom",
                      fontsize=7.2, color=blue,
                      bbox=dict(facecolor="white", edgecolor="none", pad=.15))

    positions = np.arange(3)
    seed_points, = right.plot(seed_mse, positions, linestyle="none", marker="s",
                              color=green, markersize=5.5, zorder=3)
    right.set(xlim=(.44, .48), ylim=(2.4, -.4), xlabel=r"MSE ($\times 10^{-2}$)")
    right.set_xticks([.44, .45, .46, .47, .48])
    right.xaxis.set_major_formatter(FormatStrFormatter("%.2f"))
    right.set_yticks(positions, [str(s) for s in seeds])
    right.grid(axis="x", color="#d9d9d9", linewidth=.6, linestyle=":")
    for value, y in zip(seed_mse, positions):
        right.annotate(f"{value:.4f}", (value, y), xytext=(6, 0),
                       textcoords="offset points", ha="left", va="center",
                       fontsize=7.2, color=green,
                       bbox=dict(facecolor="white", edgecolor="none", pad=.15))

    for ax, title in [(left, "(a) Source-pool size"),
                      (right, "(b) Source-training seed")]:
        ax.set_axisbelow(True)
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(width=.8, length=3.5, pad=4)
        position = ax.get_position()
        fig.text(position.x0 + position.width / 2, 5 / height, title,
                 fontsize=8.4, ha="center", va="bottom")

    save(fig, output_dir, "fig8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'generated_figures',
                        help='Output directory; manuscript figures are not overwritten')
    args = parser.parse_args()
    data, out = ROOT/'data', args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    fig = build_figure(data/'overall.csv')
    for ax in fig.axes:
        ax.set_xlabel(ax.get_xlabel().replace('; lower is better',''), labelpad=6)
    save(fig, out, 'fig5')
    plot_fig6(data, out)
    forest(data/'subgroups.csv', out)
    plot_fig8(data/'source_sensitivity.csv', out)
    resource(data, out)
    print('Generated Figures 5-9 in', out)

if __name__ == '__main__':
    main()
