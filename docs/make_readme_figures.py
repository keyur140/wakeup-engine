# Wake-up Engine: finding forgotten science that already solves today's problems
# Author: KEYUR SHAILESHKUMAR PATEL
# ORCID: https://orcid.org/0009-0008-5261-043X
# Affiliations: (1) MSc Artificial Intelligence student, Department of Computer Science,
#               Brunel University London, UK; (2) Independent researcher
# Note: Conducted independently; not an official Brunel University London project.
# License: MIT (see LICENSE)
"""Make the README charts in docs/figures/ from the exploratory run results.

  python docs/make_readme_figures.py
"""
import json, sys
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
P=Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent; R=P/"runs/20261120T194454Z_explore_23274f/results"; O=P/"docs/figures"
s=json.load(open(R/"summary.json")); g=json.load(open(R/"gate.json"))
BLUE="#257de0"; ORANGE="#f47230"; AQUA="#00b894"; GREY="#b4b4b4"; T1="#191919"; T2="#666666"; GRID="#e6e6e6"
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":12,"axes.edgecolor":GRID,"axes.labelcolor":T2,"xtick.color":T2,"ytick.color":T2,"axes.spines.top":False,"axes.spines.right":False})
FOOT="KEYUR SHAILESHKUMAR PATEL · ORCID 0009-0008-5261-043X · exploratory run 20261120T194454Z_explore_23274f (development items only)"
def bars(ax, labels, vals, colors, fmt, ymax):
    b=ax.bar(labels, vals, color=colors, width=0.62, edgecolor="white", linewidth=2)
    for r,v,t in zip(b,vals,fmt): ax.text(r.get_x()+r.get_width()/2, v+ymax*0.015, t, ha="center", va="bottom", color=T1, fontsize=12, fontweight="bold")
    ax.set_ylim(0,ymax); ax.yaxis.grid(True,color=GRID,lw=1); ax.set_axisbelow(True); ax.tick_params(length=0)
def save(fig,name):
    fig.text(0.01,-0.03,FOOT,fontsize=8,color=T2); fig.savefig(O/name,dpi=200,facecolor="white",bbox_inches="tight"); plt.close(fig)
# 1 back-test
mt={m["method"]:m for m in s["backtest"]["method_table"]}
order=["random","bm25","dense","hybrid","engine"]; names=["Random","Keyword\n(BM25)","Meaning\n(dense)","Hybrid\nsearch","Wake-up\nEngine"]
v=[mt[m]["hit@10"]*100 for m in order]; n=s["backtest"]["primary"]["n"]
fig,ax=plt.subplots(figsize=(9,5.2))
bars(ax,names,v,[GREY,GREY,GREY,AQUA,BLUE],[f"{round(x*n/100)}/{n}" for x in v],50)
ax.axhline(1,color=ORANGE,ls="--",lw=2); ax.text(4.45,2.2,"luck = 1%",color=ORANGE,ha="right",fontsize=11,fontweight="bold")
ax.set_ylabel("Found in top 10 of 1,000 (%)")
ax.set_title("Back-test: how often each method finds the hidden paper",loc="left",color=T1,fontsize=15,fontweight="bold",pad=14)
save(fig,"fig1_backtest_hit10.png")
# 2 MRR
v=[mt[m]["MRR"] for m in order]
fig,ax=plt.subplots(figsize=(9,5.2)); bars(ax,names,v,[GREY,GREY,GREY,AQUA,BLUE],[f"{x:.3f}" for x in v],0.32)
ax.set_ylabel("MRR (higher = nearer the top)")
ax.set_title("Back-test: how high the hidden paper is ranked (MRR)",loc="left",color=T1,fontsize=15,fontweight="bold",pad=14)
save(fig,"fig2_backtest_mrr.png")
# 3 forward
t=s["forward"]["tests"]; hb=s["forward"]["hits_by_group"]
v=[t["H2_engine_vs_pool_random"]["mean_treat"],t["H2_engine_vs_pool_random"]["mean_control"],t["H3_engine_vs_global_random"]["mean_control"]]
fig,ax=plt.subplots(figsize=(9,5.2))
bars(ax,["Engine picks","Random from the\nsame search pool","Random old\npapers"],v,[BLUE,AQUA,GREY],[f"{x:.2f}  ({hb[k][0]}/{hb[k][1]} hits)" for x,k in zip(v,["engine","pool_random","global_random"])],5)
ax.set_ylabel("Mean usefulness score, 3 blind AI judges (1-5)")
ax.set_title("Forward test (4 practice problems): are the engine's picks useful?",loc="left",color=T1,fontsize=15,fontweight="bold",pad=14)
save(fig,"fig3_forward_ratings.png")
# 4 gate
lab={"engine":"Engine\nqwen3.8-27b","judge_gptoss120":"Judge\ngpt-oss-120b","judge_gptoss20":"Judge\ngpt-oss-20b","judge_allam":"Judge\nALLaM-2-7b"}
v=[x["auc"] for x in g]
fig,ax=plt.subplots(figsize=(9,5.2)); bars(ax,[lab[x["model_name"]] for x in g],v,[BLUE,AQUA,AQUA,AQUA],[f"{x:.2f} ✓" for x in v],1.0)
ax.axhline(0.5,color=ORANGE,ls="--",lw=2); ax.text(3.45,0.40,"coin flip = 0.50",color=ORANGE,ha="right",fontsize=11,fontweight="bold",bbox=dict(facecolor="white",edgecolor=ORANGE,boxstyle="round,pad=0.3"))
ax.set_ylabel("AUC (real answer beats decoy)")
ax.set_title("Known-answer gate: every AI model passed before it was trusted",loc="left",color=T1,fontsize=15,fontweight="bold",pad=14)
save(fig,"fig4_gate_auc.png")
print("ok")
