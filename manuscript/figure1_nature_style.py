from __future__ import annotations
import html, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "manuscript" / "figure1_nature_style_data.json"
OUTDIR = ROOT / "outputs" / "manuscript"
OUTDIR.mkdir(parents=True, exist_ok=True)
OUT = OUTDIR / "Figure_1_nature_style.svg"

D = json.loads(DATA.read_text(encoding="utf-8"))

W, H = 1830, 1680
XMIN, XMAX = -0.032, 0.032

BLUE = "#2B6EA6"
DARK = "#202428"
MID = "#5F666D"
LIGHT = "#AEB5BC"
PALE = "#EEF2F5"
PALE2 = "#F6F8FA"
BAND = "#E8EDF1"
WHITE = "#FFFFFF"

def e(s): return html.escape(str(s))
def text(x,y,s,cls="txt",anchor="start",extra=""):
    return f'<text x="{x}" y="{y}" class="{cls}" text-anchor="{anchor}" {extra}>{e(s)}</text>'
def line(x1,y1,x2,y2,cls="axis",extra=""):
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" class="{cls}" {extra}/>'
def rect(x,y,w,h,cls="box",rx=10,extra=""):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" class="{cls}" {extra}/>'
def circle(x,y,r,fill,stroke=DARK,sw=1.5):
    return f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
def polygon(points,fill=WHITE,stroke=DARK,sw=1.5):
    pts=" ".join(f"{x},{y}" for x,y in points)
    return f'<polygon points="{pts}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
def wrap(s, width):
    words=s.split(); out=[]; cur=[]
    for w in words:
        if len(" ".join(cur+[w])) <= width:
            cur.append(w)
        else:
            if cur: out.append(" ".join(cur))
            cur=[w]
    if cur: out.append(" ".join(cur))
    return out
def multiline(x,y,lines,cls="small",anchor="start",dy=16):
    out=[]
    for i,ln in enumerate(lines):
        out.append(text(x,y+i*dy,ln,cls,anchor))
    return out
def arrow(x1,y1,x2,y2):
    return line(x1,y1,x2,y2,"arrow",f'marker-end="url(#arrow)"')

svg=[]
svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="183mm" height="168mm" viewBox="0 0 {W} {H}">')
svg.append("""<defs>
<marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto" markerUnits="strokeWidth">
<path d="M0,0 L8,4 L0,8 z" fill="#5F666D"/></marker>
</defs>""")
svg.append(f'<rect width="{W}" height="{H}" fill="{WHITE}"/>')
svg.append("""<style>
text{font-family:Arial,Helvetica,sans-serif;fill:#202428}
.panel{font-size:8pt;font-weight:700}
.head{font-size:7pt;font-weight:700}
.txt{font-size:6.2pt}
.small{font-size:5.6pt}
.tiny{font-size:5pt}
.axistext{font-size:5.4pt}
.group{font-size:6.2pt;font-weight:700}
.box{fill:#F6F8FA;stroke:#D4D9DE;stroke-width:0.65}
.boxblue{fill:#EEF5FA;stroke:#BFCFDC;stroke-width:0.65}
.boxaccent{fill:#F8FAFB;stroke:#2B6EA6;stroke-width:0.9}
.axis{stroke:#535A60;stroke-width:0.65}
.zero{stroke:#535A60;stroke-width:0.8;stroke-dasharray:5 4}
.ci{stroke:#5F666D;stroke-width:1.0}
.ciprimary{stroke:#2B6EA6;stroke-width:1.25}
.sep{stroke:#D9DEE2;stroke-width:0.55}
.arrow{stroke:#5F666D;stroke-width:0.8;fill:none}
</style>""")

# Panel a
svg.append(text(24,34,"a","panel"))
svg.append(text(62,34,"Preregistered design: semantic-score augmentation at a fixed 12-hour ICU landmark","head"))

boxes=[
    (35,70,250,315,"Cohort"),
    (320,70,220,315,"Landmark"),
    (575,70,285,315,"Narrative input"),
    (895,70,310,315,"Eight typed scores"),
    (1240,70,255,315,"Model comparison"),
    (1530,70,265,315,"Outcomes")
]
for x,y,w,h,title in boxes:
    cls="boxaccent" if title=="Model comparison" else "box"
    svg.append(rect(x,y,w,h,cls))
    svg.append(text(x+16,y+28,title,"head"))

# cohort
multiline(52,128,["MIMIC-III adult","MetaVision ICU stays"],"txt",dy=20); svg+=multiline(52,190,["Still in ICU at 12 h","NICU excluded"],"small",dy=18)
# landmark
svg.append(line(345,175,515,175,"axis"))
svg.append(circle(430,175,6,DARK,DARK,1))
svg.append(line(430,130,430,210,"zero"))
svg.append(text(350,230,"ICU admission","small")); svg.append(text(430,230,"12 h","small","middle"))
svg.append(text(430,250,"prediction landmark","tiny","middle"))
# narrative
svg+=multiline(592,120,["Single latest eligible","bedside note before","the landmark"],"txt",dy=20)
svg+=multiline(592,205,["Primary corpus removes","prespecified endpoint /","treatment expressions"],"small",dy=18)
svg.append(text(592,282,"Chunk if needed","small"))
# semantic scores
constructs=D["design"]["semantic_constructs"]
for i,name in enumerate(constructs):
    col=i//4; row=i%4
    x=912+col*145; y=120+row*50
    svg.append(circle(x,y-5,4,BLUE,BLUE,0))
    lines=wrap(name,21)
    svg+=multiline(x+12,y,lines,"small",dy=14)
svg.append(text(912,330,"Yes/no decision score per construct","tiny"))
# model
svg+=multiline(1258,118,["Rich comparator"],"head")
svg+=multiline(1258,150,["34 physiology / lab / urine","+ treatment/support","+ documentation behaviour","+ note context"],"small",dy=18)
svg.append(text(1370,270,"vs","head","middle"))
svg+=multiline(1258,302,["Rich comparator","+ 8 semantic scores"],"head",dy=20)
# outcomes
svg+=multiline(1547,118,["Next 12 h"],"head")
for i,(name,n,cases) in enumerate([
    ("Invasive ventilation",11116,279),("RRT",19395,314),("ICU death",19811,214)
]):
    yy=155+i*60
    svg.append(text(1547,yy,name,"txt"))
    svg.append(text(1547,yy+19,f"n={n:,}; events={cases}","tiny"))
svg+=multiline(1547,350,["CareVue ICU-death","replication reported separately"],"tiny",dy=15)

for i in range(len(boxes)-1):
    x1=boxes[i][0]+boxes[i][2]+8; x2=boxes[i+1][0]-8
    svg.append(arrow(x1,225,x2,225))

# divider
svg.append(line(24,425,1806,425,"sep"))

# Panel b
svg.append(text(24,468,"b","panel"))
svg.append(text(62,468,"Registered estimates and prespecified sensitivities cluster near zero","head"))

PLOT_X0, PLOT_X1 = 815, 1715
def sx(v):
    return PLOT_X0 + (v-XMIN)/(XMAX-XMIN)*(PLOT_X1-PLOT_X0)

svg.append(text(PLOT_X0+50,500,"Worse with semantic scores  ←","tiny"))
svg.append(text(PLOT_X1-50,500,"→  Better with semantic scores","tiny","end"))
svg.append(line(sx(0),520,sx(0),1460,"zero"))

ticks=[-0.03,-0.02,-0.01,0,0.01,0.02,0.03]
for t in ticks:
    x=sx(t)
    svg.append(line(x,1460,x,1470,"axis"))
    lab="0" if t==0 else f"{t:+.02f}"
    svg.append(text(x,1492,lab,"axistext","middle"))
svg.append(text((PLOT_X0+PLOT_X1)/2,1524,"ΔAUROC (semantic scores minus comparator)","axistext","middle"))

rows=D["forest"]
groups=["Invasive ventilation","Renal replacement therapy","ICU death"]
mde={"Invasive ventilation":D["planning_magnitude"]["ventilation"],"Renal replacement therapy":D["planning_magnitude"]["rrt"],"ICU death":D["planning_magnitude"]["death_metavision"]}

y=540
row_h=27
gap=20
positions=[]
for g in groups:
    grot=[r for r in rows if r["group"]==g]
    top=y-3
    bottom=y+row_h*len(grot)-10
    # planning magnitude band for the outcome group
    xlo=sx(-mde[g]); xhi=sx(mde[g])
    svg.append(f'<rect x="{xlo:.1f}" y="{top:.1f}" width="{xhi-xlo:.1f}" height="{bottom-top:.1f}" fill="{BAND}" opacity="0.72"/>')
    svg.append(text(38,y-10,g,"group"))
    svg.append(text(38,y+8,f"pre-analysis 80% detectable Δ≈{mde[g]:.3f}","tiny"))
    y+=20
    for r in grot:
        positions.append((r,y))
        svg.append(text(245,y+4,r["analysis"],"small"))
        est,lo,hi=r["estimate"],r["lo"],r["hi"]
        ci_cls="ciprimary" if r["kind"]=="primary" else "ci"
        svg.append(line(sx(lo),y,sx(hi),y,ci_cls))
        svg.append(line(sx(lo),y-5,sx(lo),y+5,ci_cls))
        svg.append(line(sx(hi),y-5,sx(hi),y+5,ci_cls))
        xm=sx(est)
        kind=r["kind"]
        if kind=="primary":
            svg.append(circle(xm,y,6,BLUE,BLUE,1))
        elif kind=="control":
            svg.append(polygon([(xm,y-6),(xm+6,y),(xm,y+6),(xm-6,y)],WHITE,DARK,1.2))
        elif kind=="replication":
            svg.append(f'<rect x="{xm-5}" y="{y-5}" width="10" height="10" fill="{MID}" stroke="{MID}" stroke-width="1"/>')
        elif kind=="timing":
            svg.append(polygon([(xm,y-6),(xm+6,y+5),(xm-6,y+5)],WHITE,MID,1.1))
        elif kind=="endpoint":
            svg.append(f'<rect x="{xm-5}" y="{y-5}" width="10" height="10" fill="{WHITE}" stroke="{MID}" stroke-width="1.1"/>')
        else:
            svg.append(circle(xm,y,5,WHITE,MID,1.1))
        y+=row_h
    svg.append(line(38,y-13,1790,y-13,"sep"))
    y+=gap

# legend / footnote
ly=1570
svg.append(circle(60,ly,5,BLUE,BLUE,1)); svg.append(text(75,ly+4,"Primary","tiny"))
svg.append(circle(210,ly,5,WHITE,MID,1.1)); svg.append(text(225,ly+4,"Sensitivity","tiny"))
svg.append(polygon([(375,ly-5),(380,ly+4),(370,ly+4)],WHITE,MID,1.1)); svg.append(text(392,ly+4,"Timing","tiny"))
svg.append(polygon([(510,ly-6),(516,ly),(510,ly+6),(504,ly)],WHITE,DARK,1.2)); svg.append(text(528,ly+4,"Shuffled control","tiny"))
svg.append(f'<rect x="685" y="{ly-5}" width="10" height="10" fill="{MID}" stroke="{MID}" stroke-width="1"/>'); svg.append(text(703,ly+4,"CareVue replication","tiny"))
svg.append(text(1000,ly+4,"Pale band = approximate pre-analysis 80% detectable |ΔAUROC|; interpretive reference only, not an equivalence margin.","tiny"))

svg.append('</svg>')
OUT.write_text("\n".join(svg),encoding="utf-8")
print(json.dumps({"status":"completed","svg":str(OUT.relative_to(ROOT)),"forest_rows":len(rows)},indent=2))
