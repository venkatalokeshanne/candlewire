import random, os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
W,H=1080,1350
BG=(6,7,10); TXT=(246,247,250); MUT=(135,142,158)
AMB=(255,193,59); RED=(255,64,64); GREEN=(40,214,128); CYAN=(70,200,255)
CARD=(16,18,26); LINE=(38,42,56)
FONT_DIR=Path(__file__).resolve().parent.parent/"assets"/"fonts"
AN=str(FONT_DIR/"Anton-Regular.ttf"); IN=str(FONT_DIR/"Inter-")
def an(s): return ImageFont.truetype(AN,s)
def inter(w,s): return ImageFont.truetype(IN+w+".otf",s)
BRAND="CANDLEWIRE"; HANDLE="@CANDLEWIRE_"

INK=(6,7,10)
def mix(a,b,t): return tuple(int(a[i]*t+b[i]*(1-t)) for i in range(3))
def draw_mark(d,x,y,s,col=AMB,body=None,bg=INK,arcs=3):
    w=lambda f:max(1,int(round(f*s)))
    cx=x+0.36*s; cy=y+0.54*s
    d.line([cx,y+0.12*s,cx,y+0.94*s],fill=col,width=w(0.05))
    d.rounded_rectangle([cx-0.12*s,y+0.34*s,cx+0.12*s,y+0.74*s],radius=w(0.035),fill=body or col)
    for i,r in enumerate((0.27,0.42,0.57)[:arcs]):
        c=mix(col,bg,[1.0,0.66,0.38][i])
        d.arc([cx-r*s,cy-r*s,cx+r*s,cy+r*s],-40,40,fill=c,width=w(0.055))



# ---- layout QA: record every text box so overflow and collisions can be detected without viewing images
_QA = {}
_orig_text = ImageDraw.ImageDraw.text
def _text(self, xy, text, *a, **k):
    try:
        _QA.setdefault(id(self.im), []).append((self.textbbox(xy, str(text), font=k.get("font"), anchor=k.get("anchor")), str(text)))
    except Exception:
        pass
    return _orig_text(self, xy, text, *a, **k)
ImageDraw.ImageDraw.text = _text

class Post:
    def __init__(self,out_dir,total,tagtext,tagcol):
        self.out=str(out_dir).rstrip("/")+"/"; os.makedirs(self.out,exist_ok=True)
        self.total=total; self.n=0; self.tagtext=tagtext; self.tagcol=tagcol; self.qa=[]; self.notes=[]
    # ---------- primitives
    def glow(self,im,cx,cy,r,col,a):
        L=Image.new("RGBA",im.size,(0,0,0,0)); ImageDraw.Draw(L).ellipse([cx-r,cy-r,cx+r,cy+r],fill=col+(a,))
        L=L.filter(ImageFilter.GaussianBlur(r*.55)); im.paste(L,(0,0),L)
    def logo(self,d,x,y,s=44):
        draw_mark(d,x-6,y-4,s+12,AMB)
    def new(self,glowcol=RED):
        self.n+=1; im=Image.new("RGB",(W,H),BG)
        self.glow(im,W-100,150,360,glowcol,36); self.glow(im,60,H-120,320,AMB,20)
        return im,ImageDraw.Draw(im)
    def chrome(self,im,footer=None):
        d=ImageDraw.Draw(im)
        self.logo(d,60,56); d.text((112,58),BRAND,font=inter("ExtraBold",30),fill=TXT)
        t=f"{self.n}/{self.total}"; w=d.textlength(t,font=inter("Bold",24))+36
        d.rounded_rectangle([W-60-w,58,W-60,100],radius=21,fill=(28,30,40)); d.text((W-60-w+18,64),t,font=inter("Bold",24),fill=TXT)
        if footer: d.text((60,H-130),footer,font=inter("Medium",21),fill=MUT)
        y=H-62; d.line([60,y,400,y],fill=TXT,width=2); d.line([W-400,y,W-60,y],fill=TXT,width=2)
        d.text((W//2,y),HANDLE,font=inter("SemiBold",24),fill=TXT,anchor="mm")
    def fit(self,d,text,font,maxw):
        if d.textlength(text,font=font)<=maxw: return text
        t=text
        while len(t)>1 and d.textlength(t+"…",font=font)>maxw: t=t[:-1]
        self.notes.append(f"slide {self.n}: trimmed '{text[:30]}' to fit")
        return t.rstrip()+"…"
    def check(self,im):
        items=_QA.pop(id(im.im),[]); out=[]
        for bb,t in items:
            if bb[0]<40 or bb[2]>W-50 or bb[3]>H-40: out.append(f"edge: '{t[:28]}'")
        for i in range(len(items)):
            for j in range(i+1,len(items)):
                a,b=items[i][0],items[j][0]; ix=min(a[2],b[2])-max(a[0],b[0]); iy=min(a[3],b[3])-max(a[1],b[1])
                if ix>4 and iy>2:
                    am=min((a[2]-a[0])*(a[3]-a[1]),(b[2]-b[0])*(b[3]-b[1]))
                    if am>0 and ix*iy/am>0.04: out.append(f"overlap: '{items[i][1][:22]}' x '{items[j][1][:22]}'")
        self.qa+= [f"slide {self.n}: {o}" for o in out]
    def save(self,im,footer=None):
        self.chrome(im,footer); self.check(im); im.save(self.out+f"slide_{self.n}.png")
    @staticmethod
    def rows_of(d,parts,font,maxw):
        words=[(w,c) for t,c in parts for w in t.split()]; sp=d.textlength(" ",font=font); rows=[];cur=[];cw=0
        for w,c in words:
            wl=d.textlength(w,font=font)
            if cur and cw+sp+wl>maxw: rows.append((cur,cw));cur=[];cw=0
            cw+=(sp if cur else 0)+wl; cur.append((w,c))
        rows.append((cur,cw)); return rows
    def rich(self,d,x,y,parts,font,gap=1.02,center=False,maxw=W-120):
        sp=d.textlength(" ",font=font)
        for r,wd in self.rows_of(d,parts,font,maxw):
            xx=W/2-wd/2 if center else x
            for w,c in r: d.text((xx,y),w,font=font,fill=c); xx+=d.textlength(w,font=font)+sp
            y+=int(font.size*gap)
        return y
    def para(self,d,x,y,t,font,fill,maxw,gap=1.3):
        words=t.split(); line=""
        for w in words:
            if d.textlength((line+" "+w).strip(),font=font)<=maxw: line=(line+" "+w).strip()
            else: d.text((x,y),line,font=font,fill=fill); y+=int(font.size*gap); line=w
        d.text((x,y),line,font=font,fill=fill); return y+int(font.size*gap)
    def tag(self,d,cx,y):
        f=an(34); w=d.textlength(self.tagtext,font=f)+60
        d.line([60,y+26,cx-w/2-24,y+26],fill=TXT,width=3); d.line([cx+w/2+24,y+26,W-60,y+26],fill=TXT,width=3)
        d.polygon([(cx-w/2+14,y),(cx+w/2+14,y),(cx+w/2-14,y+52),(cx-w/2-14,y+52)],fill=self.tagcol)
        d.text((cx,y+27),self.tagtext,font=f,fill=BG,anchor="mm")
    def head(self,d,kicker,parts,size=104,y0=150):
        d.text((60,y0),kicker,font=inter("Bold",25),fill=self.tagcol)
        return self.rich(d,60,y0+46,parts,an(size),gap=1.0)
    # ---------- hero
    def hero(self,im,seed,gp):
        hh=800; lay=Image.new("RGB",(W,hh),BG); d=ImageDraw.Draw(lay); random.seed(seed); rects=[]
        def split(x,y,ww,h2,dep):
            if dep==0 or ww<70 or h2<70: rects.append((x,y,ww,h2)); return
            s=random.uniform(.35,.65)
            if ww>h2: split(x,y,ww*s,h2,dep-1); split(x+ww*s,y,ww*(1-s),h2,dep-1)
            else: split(x,y,ww,h2*s,dep-1); split(x,y+h2*s,ww,h2*(1-s),dep-1)
        split(0,0,W,hh,7)
        for (x,y,ww,h2) in rects:
            k=random.random()
            if random.random()<gp: c=(int(8+k*30),int(95+k*125),int(55+k*60))
            else: c=(int(120+k*135),int(10+k*40),int(14+k*36))
            d.rectangle([x+3,y+3,x+ww-3,y+h2-3],fill=c)
        lay=lay.filter(ImageFilter.GaussianBlur(1.2)); mask=Image.new("L",(W,hh)); md=ImageDraw.Draw(mask)
        for yy in range(hh): md.line([0,yy,W,yy],fill=int(255*max(0,min(1,(hh-yy)/330))))
        im.paste(lay,(0,0),mask)
        ov=Image.new("RGBA",(W,hh),(0,0,0,0)); ImageDraw.Draw(ov).ellipse([140,150,W-140,660],fill=(0,0,0,175)); ov=ov.filter(ImageFilter.GaussianBlur(40)); im.paste(ov,(0,0),ov)
    # ---------- slide types
    def cover(self,kicker,big,bigcol,bigsub,headline,seed=11,gp=0.3,bigsize=230):
        im,d=self.new(); self.hero(im,seed,gp); d=ImageDraw.Draw(im)
        d.text((W//2,330),kicker,font=inter("Bold",26),fill=MUT,anchor="mm")
        d.text((W//2,470),big,font=an(bigsize),fill=bigcol,anchor="mm")
        d.text((W//2,610),bigsub,font=an(50),fill=TXT,anchor="mm")
        d.text((W-60,742),"ILLUSTRATIVE BACKGROUND",font=inter("Bold",18),fill=MUT,anchor="ra")
        self.tag(d,W//2,790); self.rich(d,0,880,headline,an(84),gap=1.04,center=True)
        d.text((W-60,1192),"SWIPE  →",font=inter("Bold",28),fill=TXT,anchor="ra")
        self.save(im)
    def board(self,kicker,parts,rows,footer,rowh=170,valsize=84):
        im,d=self.new(); y=self.head(d,kicker,parts)+30
        for i,(nm,val,sub,col,ratio) in enumerate(rows):
            yy=y+i*(rowh+22)
            d.rounded_rectangle([60,yy,W-60,yy+rowh],radius=24,fill=CARD,outline=LINE,width=2)
            if ratio: 
                dark=tuple(int(c*0.38) for c in col)
                d.rounded_rectangle([60,yy,60+max(40,int((W-120)*ratio)),yy+rowh],radius=24,fill=dark)
            vw=d.textlength(val,font=an(valsize)); d.text((92,yy+22),self.fit(d,nm,an(38),W-92-vw-24-92),font=an(38),fill=TXT)
            self.para(d,92,yy+84,sub,inter("SemiBold",24),(215,218,226),560,gap=1.2)
            d.text((W-92,yy+rowh//2),val,font=an(valsize),fill=col,anchor="rm")
        self.save(im,footer)
    def cards(self,kicker,parts,cards,footer,cardh=215):
        im,d=self.new(); y=self.head(d,kicker,parts)+36
        for i,(n,t,s) in enumerate(cards):
            yy=y+i*(cardh+24)
            d.rounded_rectangle([60,yy,W-60,yy+cardh],radius=24,fill=CARD,outline=LINE,width=2)
            d.text((100,yy+cardh//2),n,font=an(100),fill=self.tagcol,anchor="lm")
            d.text((200,yy+26),self.fit(d,t.upper(),an(38),W-60-24-200),font=an(38),fill=TXT)
            self.para(d,200,yy+84,s,inter("Medium",27),MUT,W-300,gap=1.28)
        self.save(im,footer)
    def bignum(self,kicker,parts,big,bigcol,bigsub,bullets,footer):
        im,d=self.new(); y=self.head(d,kicker,parts)+36
        d.rounded_rectangle([60,y,W-60,y+330],radius=28,fill=CARD,outline=LINE,width=2)
        d.text((W//2,y+140),big,font=an(210),fill=bigcol,anchor="mm"); d.text((W//2,y+275),bigsub,font=an(40),fill=TXT,anchor="mm")
        yy=y+370
        for b in bullets:
            d.ellipse([72,yy+14,86,yy+28],fill=self.tagcol); yy=self.para(d,108,yy,b,inter("SemiBold",31),TXT,W-190,gap=1.3)+16
        self.save(im,footer)
    def movers(self,kicker,parts,rows,footer,rowh=120):
        im,d=self.new(); y=self.head(d,kicker,parts)+30
        for i,(tk,pct,note,time) in enumerate(rows):
            yy=y+i*(rowh+12); col=GREEN if pct>0 else RED
            d.rounded_rectangle([60,yy,W-60,yy+rowh],radius=22,fill=CARD,outline=LINE,width=2)
            d.rectangle([60,yy+18,70,yy+rowh-18],fill=col)
            d.text((96,yy+16),tk,font=an(46),fill=TXT)
            d.text((96,yy+74),time,font=inter("Bold",21),fill=MUT)
            self.para(d,330,yy+22,note,inter("Medium",25),(200,204,214),470,gap=1.22)
            d.text((W-88,yy+rowh//2),("+" if pct>0 else "−")+f"{abs(pct):.2f}%",font=an(54),fill=col,anchor="rm")
        self.save(im,footer)
    def movers2(self,kicker,parts,gain,lose,footer):
        im,d=self.new(); y=self.head(d,kicker,parts)+34; cw=(W-120-30)/2
        for ci,(lab,col,lst) in enumerate([("GAINERS",GREEN,gain),("LOSERS",RED,lose)]):
            x=60+ci*(cw+30); d.text((x,y),lab,font=an(40),fill=col)
            for i,(tk,name,pct) in enumerate(lst):
                yy=y+64+i*150
                d.rounded_rectangle([x,yy,x+cw,yy+132],radius=22,fill=CARD,outline=LINE,width=2); d.rectangle([x,yy+18,x+9,yy+114],fill=col)
                d.text((x+34,yy+14),tk,font=an(44),fill=TXT); d.text((x+34,yy+76),self.fit(d,name,inter("Medium",22),cw-34-24-165),font=inter("Medium",22),fill=MUT)
                d.text((x+cw-24,yy+66),("+" if pct>0 else "−")+f"{abs(pct):.2f}%",font=an(46),fill=col,anchor="rm")
        self.save(im,footer)
    def chipbars(self,kicker,parts,rows,avg,footer):
        im,d=self.new(); y=self.head(d,kicker,parts)+20
        rh=80
        for i,(tk,gain,share) in enumerate(rows):
            yy=y+i*(rh+10)
            d.rounded_rectangle([60,yy,W-60,yy+rh],radius=16,fill=CARD)
            d.rounded_rectangle([60,yy,60+int((W-120)*share/70),yy+rh],radius=16,fill=(15,92,58))
            d.text((86,yy+rh//2),tk,font=an(38),fill=TXT,anchor="lm")
            d.text((380,yy+rh//2),f"+{gain:.2f}% Fri",font=inter("SemiBold",25),fill=(215,218,226),anchor="lm")
            d.text((W-86,yy+rh//2),f"{share}%",font=an(48),fill=GREEN,anchor="rm")
        yy=y+len(rows)*(rh+10)+10
        d.rounded_rectangle([60,yy,W-60,yy+110],radius=22,fill=AMB)
        d.text((W//2,yy+55),f"AVERAGE: {avg}% OF THURSDAY'S LOSS WON BACK",font=an(40),fill=BG,anchor="mm")
        self.save(im,footer)
    def linechart(self,kicker,parts,pts,note,footer):
        im,d=self.new(CYAN); y=self.head(d,kicker,parts)+30; ch=560
        d.rounded_rectangle([60,y,W-60,y+ch],radius=28,fill=CARD,outline=LINE,width=2)
        x0,x1=130,W-110; y0,y1=y+90,y+ch-90
        for g in (0,25,50):
            yy=y1-(y1-y0)*g/50; d.line([x0,yy,x1,yy],fill=LINE,width=2); d.text((x0-14,yy),f"{g}%",font=inter("SemiBold",22),fill=MUT,anchor="rm")
        n=len(pts); xy=[]
        for i,(lab,v) in enumerate(pts):
            xx=x0+(x1-x0)*i/(n-1) if n>1 else x0; yy=y1-(y1-y0)*v/50; xy.append((xx,yy))
        L=Image.new("RGBA",im.size,(0,0,0,0)); ImageDraw.Draw(L).line(xy,fill=CYAN+(200,),width=16); L=L.filter(ImageFilter.GaussianBlur(10)); im.paste(L,(0,0),L); d=ImageDraw.Draw(im)
        d.line(xy,fill=CYAN,width=7,joint="curve")
        for (xx,yy),(lab,v) in zip(xy,pts):
            d.ellipse([xx-13,yy-13,xx+13,yy+13],fill=CYAN,outline=BG,width=4)
            d.text((xx,yy-34),f"≈{v}%",font=an(40),fill=TXT,anchor="mm"); d.text((xx,y1+36),lab,font=inter("Bold",22),fill=MUT,anchor="mm")
        self.para(d,70,y+ch+24,note,inter("Medium",25),MUT,W-140,gap=1.3)
        self.save(im,footer)
    def cta(self,sources,extra,disclaimer="Educational content only. Not financial advice. Trading involves risk of loss."):
        im,d=self.new(); y=self.rich(d,60,150,[("SEND THIS ",self.tagcol),("TO A FRIEND WHO TRADES.",TXT)],an(112),gap=1.0)+34
        if extra:
            d.rounded_rectangle([60,y,W-60,y+150],radius=24,fill=CARD,outline=LINE,width=2)
            d.text((92,y+22),extra[0],font=an(34),fill=MUT); d.text((92,y+78),extra[1],font=an(46),fill=self.tagcol); y+=180
        h=70+len(sources)*50+20
        d.rounded_rectangle([60,y,W-60,y+h],radius=26,fill=CARD,outline=LINE,width=2)
        d.text((92,y+22),"SOURCES",font=an(34),fill=MUT); yy=y+78
        for s in sources:
            d.ellipse([94,yy+12,106,yy+24],fill=self.tagcol); yy=self.para(d,124,yy,s,inter("Medium",24),TXT,W-220,gap=1.22)+6
        d.text((60,y+h+26),"Figures can differ slightly between outlets. Times are US Eastern.",font=inter("Medium",23),fill=MUT)
        d.text((60,y+h+60),disclaimer,font=inter("SemiBold",23),fill=MUT)
        self.save(im)
