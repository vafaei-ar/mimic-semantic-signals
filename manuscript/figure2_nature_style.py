from __future__ import annotations
import html, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"manuscript"/"figure2_nature_style_data.json"
OUTDIR=ROOT/"outputs"/"manuscript"
OUTDIR.mkdir(parents=True,exist_ok=True)
OUT=OUTDIR/"Figure_2_nature_style.svg"
D=json.loads(DATA.read_text(encoding="utf-8"))

W,H=1830,1500
BLUE="#2B6EA6"; DARK="#202428"; MID="#6A7076"; LIGHT="#B7BDC2"; PALE="#F3F5F7"; WHITE="#FFFFFF"

def e(s): return html.escape(str(s))
def text(x,y,s,cls="txt",anchor="start",extra=""): return f'<text x="{x}" y="{y}" class="{cls}" text-anchor="{anchor}" {extra}>{e(s)}</text>'
def line(x1,y1,x2,y2,cls="axis",extra=""): return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" class="{cls}" {extra}/>'
def circle(x,y,r,fill,stroke=DARK,sw=1.2): return f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
def wrap(s,width):
    words=s.split(); out=[]; cur=[]
    for w in words:
        if len(" ".join(cur+[w]))<=width: cur.append(w)
        else:
            if cur: out.append(" ".join(cur))
            cur=[w]
    if cur: out.append(" ".join(cur))
    return out

svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="183mm" height="150mm" viewBox="0 0 {W} {H}">',
     f'<rect width="{W}" height="{H}" fill="{WHITE}"/>',
"""<style>
text{font-family:Arial,Helvetica,sans-serif;fill:#202428}
.panel{font-size:8pt;font-weight:700}.head{font-size:7pt;font-weight:700}.txt{font-size:5.8pt}.small{font-size:5.3pt}.tiny{font-size:4.8pt}
.axis{stroke:#596067;stroke-width:0.65}.zero{stroke:#596067;stroke-width:0.8;stroke-dasharray:5 4}.grid{stroke:#E1E5E8;stroke-width:0.5}.sep{stroke:#D9DEE2;stroke-width:0.55}
.primary{stroke:#2B6EA6;stroke-width:2.0;fill:none}.secondary{stroke:#B5BBC0;stroke-width:0.85;fill:none}
</style>"""]

# Panel A: comparator decomposition
ax0,ax1=65,875; ay0,ay1=65,690
svg.append(text(24,34,"a","panel")); svg.append(text(62,34,"Semantic increment attenuates as the structured comparator becomes richer","head"))
sub_h=155; top=95
yr=(-0.010,0.025)
def xA(i): return ax0+145+i*180
def yA(v,base): return base+sub_h-28-(v-yr[0])/(yr[1]-yr[0])*(sub_h-55)
for idx,(outcome,reps) in enumerate(D["comparator_decomposition"]["outcomes"].items()):
    base=top+idx*180
    svg.append(text(ax0,base+18,outcome,"txt"))
    for t in [-0.01,0,0.01,0.02]:
        yy=yA(t,base); svg.append(line(ax0+145,yy,ax1-15,yy,"zero" if t==0 else "grid"))
        svg.append(text(ax0+132,yy+4,f"{t:+.02f}" if t!=0 else "0","tiny","end"))
    for vals in reps[1:]:
        pts=" ".join(f"{xA(i):.1f},{yA(v,base):.1f}" for i,v in enumerate(vals))
        svg.append(f'<polyline points="{pts}" class="secondary"/>')
        for i,v in enumerate(vals): svg.append(circle(xA(i),yA(v,base),3.5,WHITE,LIGHT,0.9))
    vals=reps[0]; pts=" ".join(f"{xA(i):.1f},{yA(v,base):.1f}" for i,v in enumerate(vals))
    svg.append(f'<polyline points="{pts}" class="primary"/>')
    for i,v in enumerate(vals): svg.append(circle(xA(i),yA(v,base),5,BLUE,BLUE,1))
    if idx==2:
        for i,k in enumerate(["A","B","C","D"]): svg.append(text(xA(i),base+sub_h+8,k,"small","middle"))
svg.append(text(ax0+18,575,"Primary partition","tiny")); svg.append(line(ax0+112,571,ax0+150,571,"primary"))
svg.append(text(ax0+215,575,"Other frozen partitions","tiny")); svg.append(line(ax0+340,571,ax0+378,571,"secondary"))
# level definitions
defs=[("A","34 structured physiology/lab/urine"),("B","+ treatment/support"),("C","+ documentation behaviour"),("D","+ note context (availability, age, category)")]
for i,(k,lab) in enumerate(defs):
    x=ax0+40+i*198
    svg.append(text(x,625,k,"head","middle"))
    lines=wrap(lab,26)
    for j,ln in enumerate(lines): svg.append(text(x,644+j*14,ln,"tiny","middle"))
svg.append(text(28,365,"ΔAUROC","small","middle",'transform="rotate(-90 28 365)"'))
svg.append(text(ax0+2,685,"Post-registration exploratory; five frozen patient-grouped partitions; no new bootstrap.","tiny"))

# Panel B: common logistic representation comparison
bx0,bx1=960,1785; by0,by1=65,690
svg.append(text(920,34,"b","panel")); svg.append(text(958,34,"High-dimensional TF-IDF retains a small increment in the same logistic family","head"))
xmin,xmax=-0.010,0.008
def sx(v): return bx0+165+(v-xmin)/(xmax-xmin)*(bx1-bx0-205)
svg.append(line(sx(0),110,sx(0),585,"zero"))
for t in [-0.01,-0.005,0,0.005]:
    x=sx(t); svg.append(line(x,585,x,593,"axis")); svg.append(text(x,612,f"{t:+.3f}" if t else "0","tiny","middle"))
svg.append(text((sx(xmin)+sx(xmax))/2,640,"ΔAUROC within common L2-logistic model family","small","middle"))
series=[("Open-Jev",DARK,"circle"),("TF-IDF",BLUE,"square"),("Open-Jev after TF-IDF",MID,"diamond")]
for i,(lab,col,shape) in enumerate(series):
    x=bx0+70+i*205; y=85
    if shape=="circle": svg.append(circle(x,y,5,col,col,1))
    elif shape=="square": svg.append(f'<rect x="{x-5}" y="{y-5}" width="10" height="10" fill="{col}" stroke="{col}"/>')
    else: svg.append(f'<polygon points="{x},{y-6} {x+6},{y} {x},{y+6} {x-6},{y}" fill="{col}" stroke="{col}"/>')
    svg.append(text(x+12,y+4,lab,"tiny"))
for oi,row in enumerate(D["logistic_representation"]["outcomes"]):
    y=180+oi*130
    svg.append(text(bx0,y+4,row["outcome"],"txt"))
    vals=[row["openjev"],row["tfidf"],row["openjev_after_tfidf"]]
    offs=[-22,0,22]
    for (lab,col,shape),v,off in zip(series,vals,offs):
        yy=y+off; x=sx(v)
        if shape=="circle": svg.append(circle(x,yy,5,col,col,1))
        elif shape=="square": svg.append(f'<rect x="{x-5}" y="{yy-5}" width="10" height="10" fill="{col}" stroke="{col}"/>')
        else: svg.append(f'<polygon points="{x},{yy-6} {x+6},{yy} {x},{yy+6} {x-6},{yy}" fill="{col}" stroke="{col}"/>')
        svg.append(text(x+10,yy+4,f"{v:+.4f}","tiny"))
svg.append(text(bx0,675,"Registered secondary comparison; TF-IDF uses up to 10,000 features.","tiny"))

# divider
svg.append(line(24,725,1806,725,"sep"))

# Panel C: alignment audit
cx0,cx1=65,980; cy0,cy1=770,1450
svg.append(text(24,760,"c","panel")); svg.append(text(62,760,"Label-free audit: matched construct-state correlations exceed shuffled references","head"))
xmin,xmax=-0.04,0.20
def cx(v): return cx0+365+(v-xmin)/(xmax-xmin)*(cx1-cx0-390)
svg.append(line(cx(0),815,cx(0),1370,"zero"))
for t in [-0.04,0,0.05,0.10,0.15,0.20]:
    x=cx(t); svg.append(line(x,1370,x,1378,"axis")); svg.append(text(x,1398,f"{t:.2f}","tiny","middle"))
svg.append(text((cx(xmin)+cx(xmax))/2,1430,"Spearman ρ","small","middle"))
# legend
svg.append(circle(cx0+365,790,5,BLUE,BLUE,1)); svg.append(text(cx0+378,794,"Real score-state association","tiny"))
svg.append(circle(cx0+600,790,5,WHITE,MID,1)); svg.append(text(cx0+613,794,"Between-patient shuffled reference","tiny"))
last=None; y=840
for r in D["alignment"]:
    if last is not None and r["outcome"]!=last:
        svg.append(line(cx0,y-15,cx1,y-15,"sep")); y+=12
    if r["outcome"]!=last:
        svg.append(text(cx0,y+3,r["outcome"],"txt")); last=r["outcome"]; y+=23
    svg.append(text(cx0+135,y+4,r["pair"],"tiny"))
    xr,xs=cx(r["real"]),cx(r["shuffled"])
    svg.append(line(min(xr,xs),y,max(xr,xs),y,"grid"))
    svg.append(circle(xs,y,4.2,WHITE,MID,1))
    svg.append(circle(xr,y,4.8,BLUE,BLUE,1))
    y+=34
svg.append(text(cx0,1448,"Post-registration integrity audit; outcome labels were not read.","tiny"))

# Panel D: note-available subgroup
dx0,dx1=1080,1785; dy0,dy1=770,1450
svg.append(text(1040,760,"d","panel")); svg.append(text(1078,760,"No stable incremental gain among note-available patients","head"))
ymin,ymax=-0.022,0.032
def dy(v): return 1305-(v-ymin)/(ymax-ymin)*450
svg.append(line(dx0+45,dy(0),dx1-25,dy(0),"zero"))
for t in [-0.02,-0.01,0,0.01,0.02,0.03]:
    yy=dy(t); svg.append(line(dx0+40,yy,dx0+48,yy,"axis")); svg.append(text(dx0+32,yy+4,f"{t:+.02f}" if t else "0","tiny","end"))
xs=[1190,1425,1660]
for i,row in enumerate(D["note_available"]["outcomes"]):
    x=xs[i]
    svg.append(text(x,860,row["outcome"],"txt","middle"))
    svg.append(text(x,880,f"n={row['n']:,}; events={row['cases']}","tiny","middle"))
    deltas=row["deltas"]
    jit=[-18,-9,0,9,18]
    for j,(v,jx) in enumerate(zip(deltas,jit)):
        if j==0: svg.append(circle(x+jx,dy(v),5.5,BLUE,BLUE,1))
        else: svg.append(circle(x+jx,dy(v),4.5,WHITE,MID,1))
svg.append(text(1050,1080,"ΔAUROC","small","middle",'transform="rotate(-90 1050 1080)"'))
svg.append(text(dx0+50,1345,"● primary frozen partition","tiny"))
svg.append(text(dx0+260,1345,"○ four additional frozen partitions","tiny"))
svg.append(text(dx0+50,1380,"Frozen full-cohort OOF predictions restricted to eligible-note rows; no subgroup refitting.","tiny"))
svg.append(text(dx0+50,1402,"Post-registration exploratory.","tiny"))

svg.append('</svg>')
OUT.write_text("\n".join(svg),encoding="utf-8")
print(json.dumps({"status":"completed","svg":str(OUT.relative_to(ROOT))},indent=2))
