import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import plotly.graph_objects as go
from utils.shared import (
    inject_css, render_sidebar, get_data, get_theme, sh, fmt,
    plot_layout, info_box, GOAL_COLORS, GOAL_ICONS
)

st.set_page_config(page_title="Goals – Finance Track", page_icon="🎯",
                   layout="wide", initial_sidebar_state="expanded")
inject_css()
T = get_theme()
data = get_data()

render_sidebar("Goals")

import pandas as pd
gls = data["goals"].copy() if not data["goals"].empty else pd.DataFrame()

st.title("🎯 Financial Goals")

if gls.empty:
    info_box("Add a Goals worksheet with columns: Goal, Target, Current, Deadline")
    st.stop()

for c in ["Target","Current"]:
    if c in gls.columns:
        gls[c] = pd.to_numeric(gls[c], errors="coerce").fillna(0)

tt = gls["Target"].sum()
ts = gls["Current"].sum()
op = (ts/tt)*100 if tt>0 else 0

k1,k2,k3,k4 = st.columns(4)
k1.metric("Total Goals",  str(len(gls)))
k2.metric("Total Target", fmt(tt))
k3.metric("Total Saved",  fmt(ts), f"{op:.1f}% achieved")
k4.metric("Still Needed", fmt(tt-ts))

st.markdown("---")
sh("Overall Progress")
st.progress(int(min(op,100)))
st.caption(f"{fmt(ts)} saved of {fmt(tt)} — {op:.1f}% complete")

st.markdown("---")
sh("Goal Cards")
c1, c2 = st.columns(2)
for i,(_,r) in enumerate(gls.iterrows()):
    p   = (r["Current"]/r["Target"])*100 if r["Target"]>0 else 0
    c   = GOAL_COLORS[i % len(GOAL_COLORS)]
    ico = GOAL_ICONS[i % len(GOAL_ICONS)]
    rem = r["Target"] - r["Current"]
    with (c1 if i%2==0 else c2):
        st.markdown(f"""
        <div style='background:{T["card"]};border:1px solid {c}33;border-radius:14px;
                    padding:20px;margin-bottom:14px'>
          <div style='display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px'>
            <div>
              <div style='font-size:22px;margin-bottom:4px'>{ico}</div>
              <div style='font-size:14px;font-weight:800;color:{T["text"]}'>{r["Goal"]}</div>
              <div style='font-size:11px;color:{T["muted"]};margin-top:2px'>Deadline: {r.get("Deadline","")}</div>
            </div>
            <div style='font-size:28px;font-weight:800;color:{c};line-height:1'>{p:.1f}%</div>
          </div>
          <div style='background:{T["border"]};border-radius:8px;height:8px;overflow:hidden;margin-bottom:10px'>
            <div style='width:{min(p,100):.1f}%;height:100%;
                        background:linear-gradient(to right,{c},{c}88);border-radius:8px'></div>
          </div>
          <div style='display:flex;justify-content:space-between;font-size:12px'>
            <span style='color:{T["muted"]}'>Saved: <b style='color:{T["text"]}'>{fmt(r["Current"])}</b></span>
            <span style='color:{T["muted"]}'>Target: <b style='color:{c}'>{fmt(r["Target"])}</b></span>
          </div>
          <div style='font-size:11px;color:{T["muted"]};margin-top:4px'>
            Remaining: <b style='color:{T["text"]}'>{fmt(rem)}</b>
          </div>
        </div>""", unsafe_allow_html=True)

st.markdown("---")
sh("Progress Chart")
gls["Pct"] = (gls["Current"]/gls["Target"]*100).clip(upper=100)
fig_gc = go.Figure(go.Bar(
    x=gls["Pct"], y=gls["Goal"], orientation="h",
    marker=dict(color=GOAL_COLORS[:len(gls)], line=dict(width=0)),
    text=gls["Pct"].map(lambda x: f"{x:.1f}%"), textposition="inside",
))
lg = plot_layout()
lg["xaxis"] = dict(range=[0,105], ticksuffix="%",
                   gridcolor=T["pgrid"], color=T["ptick"], tickfont=dict(size=11))
fig_gc.update_layout(**lg, height=300)
st.plotly_chart(fig_gc, use_container_width=True)
