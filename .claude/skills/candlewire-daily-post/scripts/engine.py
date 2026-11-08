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
        self.total=total; self.n=0; self.tagtext=tagtext; self.tagcol=tagcol; self.qa=[]; self.notes=[]; self.nx=None
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
        seg=(W-120)/self.total
        for i in range(self.total):
            x0=60+i*seg+3; d.rounded_rectangle([x0,22,x0+seg-6,28],radius=3,fill=self.tagcol if i<self.n else (40,44,58))
        self.logo(d,60,56); d.text((112,58),BRAND,font=inter("ExtraBold",30),fill=TXT)
        t=f"{self.n}/{self.total}"; w=d.textlength(t,font=inter("Bold",24))+36
        d.rounded_rectangle([W-60-w,58,W-60,100],radius=21,fill=(28,30,40)); d.text((W-60-w+18,64),t,font=inter("Bold",24),fill=TXT)
        if footer: d.text((60,H-130),footer,font=inter("Medium",21),fill=MUT)
        y=H-62; d.line([60,y,400,y],fill=TXT,width=2); d.line([W-400,y,W-60,y],fill=TXT,width=2)
        d.text((W//2,y),HANDLE,font=inter("SemiBold",24),fill=TXT,anchor="mm")
        if self.nx: d.text((W-60,1176),"NEXT: "+self.nx+"  →",font=inter("Bold",24),fill=self.tagcol,anchor="ra")
        self.nx=None
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
        im,d=self.new(); self.hero(im,seed,gp); self.glow(im,W//2,470,340,bigcol,50); d=ImageDraw.Draw(im)
        d.text((W//2,330),kicker,font=inter("Bold",26),fill=MUT,anchor="mm")
        d.text((W//2,470),big,font=an(self.autosize(d,big,bigsize,W-140)),fill=bigcol,anchor="mm")
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
    def autosize(self,d,text,size,maxw):
        while size>60 and d.textlength(text,font=an(size))>maxw: size-=10
        return size
    def cpara(self,d,y,text,font,fill,maxw,gap=1.3,cx=None):
        cx=cx or W//2
        words=text.split(); line=""
        for w in words:
            if d.textlength((line+" "+w).strip(),font=font)<=maxw: line=(line+" "+w).strip()
            else: d.text((cx,y),line,font=font,fill=fill,anchor="ma"); y+=int(font.size*gap); line=w
        d.text((cx,y),line,font=font,fill=fill,anchor="ma"); return y+int(font.size*gap)
    def stat(self,kicker,big,bigcol,label,ctx,footer,bigsize=300):
        im,d=self.new(bigcol); d.text((60,150),kicker,font=inter("Bold",25),fill=self.tagcol)
        self.glow(im,W//2,520,380,bigcol,60); d=ImageDraw.Draw(im)
        d.text((W//2,520),big,font=an(self.autosize(d,big,bigsize,W-140)),fill=bigcol,anchor="mm")
        y=self.rich(d,0,730,[(label,TXT)],an(70),gap=1.04,center=True)+24
        self.cpara(d,y,ctx,inter("Medium",32),(200,204,214),W-200)
        self.save(im,footer)
    def versus(self,kicker,parts,left,right,win,verdict,footer):
        im,d=self.new(); y=self.head(d,kicker,parts)+30; ph=560; pw=(W-150)//2
        wcol=AMB
        for i,(side,x) in enumerate(((left,60),(right,60+pw+30))):
            label,big,sub,colr=side; isw=(win=="LR"[i]); wcol=colr if isw else wcol
            d.rounded_rectangle([x,y,x+pw,y+ph],radius=32,fill=CARD,outline=colr if isw else LINE,width=5 if isw else 2)
            if isw: self.glow(im,x+pw//2,y+ph//2,230,colr,45); d=ImageDraw.Draw(im)
            d.text((x+pw//2,y+62),self.fit(d,label.upper(),an(40),pw-40),font=an(40),fill=TXT if isw else MUT,anchor="mm")
            d.text((x+pw//2,y+ph//2-14),big,font=an(self.autosize(d,big,160,pw-104)),fill=colr,anchor="mm")
            self.cpara(d,y+ph//2+100,sub,inter("Medium",26),(205,209,219) if isw else MUT,pw-70,cx=x+pw//2)
        cx,cy=W//2,y+ph//2; d.ellipse([cx-54,cy-54,cx+54,cy+54],fill=BG,outline=AMB,width=5); d.text((cx,cy+2),"VS",font=an(50),fill=AMB,anchor="mm")
        vy=y+ph+34; d.rounded_rectangle([60,vy,W-60,vy+112],radius=28,fill=wcol)
        d.text((W//2,vy+56),self.fit(d,verdict.upper(),an(44),W-170),font=an(44),fill=BG,anchor="mm")
        self.save(im,footer)
    def chain(self,kicker,parts,nodes,footer):
        im,d=self.new(); y=self.head(d,kicker,parts)+24; n=len(nodes); gap=46
        nh=min(170,int((1150-y-gap*(n-1))/n)); tx=190
        for i,(title,text,colr) in enumerate(nodes):
            yy=y+i*(nh+gap)
            d.rounded_rectangle([60,yy,W-60,yy+nh],radius=26,fill=CARD,outline=LINE,width=2); d.rectangle([60,yy+18,70,yy+nh-18],fill=colr)
            d.ellipse([96,yy+nh//2-30,156,yy+nh//2+30],outline=colr,width=4); d.text((126,yy+nh//2),str(i+1),font=an(36),fill=colr,anchor="mm")
            d.text((tx,yy+16),self.fit(d,title.upper(),an(42),W-60-24-tx),font=an(42),fill=TXT)
            self.para(d,tx,yy+68,text,inter("Medium",25),MUT,W-60-24-tx,gap=1.25)
            if i<n-1:
                d.line([126,yy+nh,126,yy+nh+gap-14],fill=colr,width=5); d.polygon([(126,yy+nh+gap),(113,yy+nh+gap-18),(139,yy+nh+gap-18)],fill=colr)
        self.save(im,footer)
    # ---------- original mascot "Wick" (a candlestick with moods) + meme slides
    def mascot(self,im,cx,cy,h,mood="happy"):
        S=3; Wd=Hd=h*S; big=Image.new("RGBA",(Wd,Hd),(0,0,0,0)); d=ImageDraw.Draw(big); mx,my=Wd//2,Hd//2
        col={"happy":GREEN,"smug":GREEN,"shocked":AMB,"panic":RED,"sad":RED}[mood]
        bw,bh=int(Wd*0.42),int(Hd*0.50); lw=int(Wd*0.028); w2=int(Wd*0.020); er=int(bw*0.15); ex=int(bw*0.24); ey=my-int(bh*0.10)
        d.line([mx,my-bh//2-int(Hd*0.16),mx,my+bh//2+int(Hd*0.16)],fill=col,width=lw)
        d.rounded_rectangle([mx-bw//2,my-bh//2,mx+bw//2,my+bh//2],radius=int(Wd*0.07),fill=col)
        INK=BG; WH=(255,255,255)
        for sx in (-1,1):
            x=mx+sx*ex
            if mood=="happy": d.arc([x-er,ey-er,x+er,ey+er],200,340,fill=INK,width=w2*2)
            elif mood in("panic","shocked"):
                r=int(er*1.3); d.ellipse([x-r,ey-r,x+r,ey+r],fill=WH); pr=int(r*(0.32 if mood=="panic" else 0.22)); d.ellipse([x-pr,ey-pr,x+pr,ey+pr],fill=INK)
            elif mood=="smug":
                d.ellipse([x-er,ey-er,x+er,ey+er],fill=WH); d.ellipse([x+int(er*0.1)-int(er*0.35),ey+int(er*0.1)-int(er*0.35),x+int(er*0.1)+int(er*0.35),ey+int(er*0.1)+int(er*0.35)],fill=INK)
                d.rectangle([x-er-2,ey-er-2,x+er+2,ey-int(er*0.15)],fill=col); d.line([x-er,ey-int(er*0.15),x+er,ey-int(er*0.15)],fill=INK,width=w2)
            elif mood=="sad":
                d.ellipse([x-er,ey-er,x+er,ey+er],fill=WH); pr=int(er*0.45); d.ellipse([x-pr,ey+int(er*0.2)-pr,x+pr,ey+int(er*0.2)+pr],fill=INK)
        if mood=="panic":
            for sx in (-1,1): d.line([mx+sx*ex-sx*er,ey-int(er*2.0)-int(er*0.4),mx+sx*ex+sx*er,ey-int(er*1.8)+int(er*0.4)*0],fill=INK,width=w2)
            d.ellipse([mx-int(bw*0.13),my+int(bh*0.08),mx+int(bw*0.13),my+int(bh*0.30)],fill=INK)
            d.ellipse([mx+bw//2-int(bw*0.02),my-bh//2+int(bh*0.06),mx+bw//2+int(bw*0.12),my-bh//2+int(bh*0.24)],fill=CYAN)
        elif mood=="shocked": d.ellipse([mx-int(bw*0.09),my+int(bh*0.10),mx+int(bw*0.09),my+int(bh*0.28)],fill=INK)
        elif mood=="happy": d.arc([mx-int(bw*0.25),my+int(bh*0.0),mx+int(bw*0.25),my+int(bh*0.30)],20,160,fill=INK,width=w2*2)
        elif mood=="smug": d.arc([mx-int(bw*0.22),my+int(bh*0.02),mx+int(bw*0.30),my+int(bh*0.30)],10,95,fill=INK,width=w2*2)
        elif mood=="sad":
            d.arc([mx-int(bw*0.22),my+int(bh*0.16),mx+int(bw*0.22),my+int(bh*0.40)],200,340,fill=INK,width=w2*2)
            for sx in (-1,1): d.line([mx+sx*ex+sx*er,ey-int(er*1.6),mx+sx*ex-sx*er,ey-int(er*1.2)],fill=INK,width=w2)
            d.ellipse([mx-ex-int(er*0.35),ey+er,mx-ex+int(er*0.35),ey+er+int(er*1.1)],fill=CYAN)
        sm=big.resize((h,h),Image.LANCZOS); im.paste(sm,(cx-h//2,cy-h//2),sm)
    def _mood_col(self,mood): return {"happy":GREEN,"smug":GREEN,"shocked":AMB,"panic":RED,"sad":RED}[mood]
    def react(self,kicker,top,bottom,mood,footer):
        col=self._mood_col(mood); im,d=self.new(col); d.text((60,150),kicker,font=inter("Bold",25),fill=self.tagcol)
        y=self.rich(d,60,196,[(top,TXT)],an(86),gap=1.02)+6; cy=y+290
        self.glow(im,W//2,cy,300,col,55); self.mascot(im,W//2,cy,520,mood); d=ImageDraw.Draw(im)
        self.rich(d,0,cy+285,[(bottom,col)],an(76),gap=1.02,center=True); self.save(im,footer)
    def approve(self,kicker,no,yes,footer):
        im,d=self.new(); d.text((60,150),kicker,font=inter("Bold",25),fill=self.tagcol); rh=420
        for i,(txt,mood,col,tag) in enumerate(((no,"sad",RED,"NOPE"),(yes,"smug",GREEN,"YES"))):
            yy=215+i*(rh+24); d.rounded_rectangle([60,yy,W-60,yy+rh],radius=30,fill=CARD,outline=col,width=3)
            self.glow(im,60+200,yy+rh//2,170,col,40); self.mascot(im,60+200,yy+rh//2,400,mood); d=ImageDraw.Draw(im)
            d.rounded_rectangle([430,yy+34,430+150,yy+34+54],radius=27,fill=col); d.text((505,yy+61),tag,font=an(36),fill=BG,anchor="mm")
            self.rich(d,430,yy+112,[(txt,TXT)],an(58),gap=1.04,maxw=W-60-430-30)
        self.save(im,footer)
    def ev(self,kicker,left,right,footer):
        im,d=self.new(); d.text((60,150),kicker,font=inter("Bold",25),fill=self.tagcol); y=215; ph=820; pw=(W-150)//2
        for (label,text,mood),x in ((left,60),(right,60+pw+30)):
            col=self._mood_col(mood); d.rounded_rectangle([x,y,x+pw,y+ph],radius=32,fill=CARD,outline=col,width=4); self.glow(im,x+pw//2,y+400,190,col,40); d=ImageDraw.Draw(im)
            d.text((x+pw//2,y+60),label.upper(),font=an(44),fill=col,anchor="mm"); self.mascot(im,x+pw//2,y+330,420,mood); d=ImageDraw.Draw(im)
            self.rich(d,x+24,y+560,[(text,TXT)],an(46),gap=1.04,maxw=pw-48,center=False)
        cx,cy=W//2,y+330; d.ellipse([cx-54,cy-54,cx+54,cy+54],fill=BG,outline=AMB,width=5); d.text((cx,cy+2),"VS",font=an(50),fill=AMB,anchor="mm")
        self.save(im,footer)
    def mascot(self,im,cx,cy,h,mood="happy"):
        S=3; B=int(h*1.2*S); cv=Image.new("RGBA",(B,B),(0,0,0,0)); d=ImageDraw.Draw(cv); ox=oy=B//2
        col={"happy":GREEN,"smug":GREEN,"panic":RED,"sad":RED,"shocked":AMB}.get(mood,AMB)
        bw=int(h*0.42*S); bh=int(h*0.60*S); K=(8,9,13); Wt=(250,250,252); lw=max(3,int(bw*0.05))
        d.line([ox,oy-bh//2-int(h*0.14*S),ox,oy+bh//2+int(h*0.14*S)],fill=col,width=int(h*0.03*S))
        d.rounded_rectangle([ox-bw//2,oy-bh//2,ox+bw//2,oy+bh//2],radius=int(h*0.06*S),fill=col)
        ey=oy-int(bh*0.14); dx=int(bw*0.23); er=int(bw*0.13); my=oy+int(bh*0.16); u=int(bw*0.1)
        for sx in (-1,1):
            x=ox+sx*dx
            if mood=="happy": d.arc([x-er,ey-er//2,x+er,ey+er*3//2],200,340,fill=K,width=lw)
            else:
                d.ellipse([x-er,ey-er,x+er,ey+er],fill=Wt)
                if mood in("panic","shocked"): d.ellipse([x-er//3,ey-er//3,x+er//3,ey+er//3],fill=K)
                elif mood=="sad": d.ellipse([x-er//3,ey,x+er//3,ey+2*er//3],fill=K)
                elif mood=="smug":
                    d.ellipse([x,ey-er//4,x+2*er//3,ey+er//3],fill=K); d.rectangle([x-er-2,ey-er-2,x+er+2,ey-er//6],fill=col); d.line([x-er,ey-er//6,x+er,ey-er//6],fill=K,width=lw)
            if mood in("panic","sad"):
                inner=x-sx*er; outer=x+sx*er
                d.line([outer,ey-er-lw*2,inner,ey-er-lw*6],fill=K,width=lw)
        if mood=="happy": d.arc([ox-2*u,my-u,ox+2*u,my+2*u],20,160,fill=K,width=lw)
        elif mood=="smug": d.arc([ox-2*u,my-u//2,ox+2*u+u//2,my+2*u],10,120,fill=K,width=lw)
        elif mood=="panic": d.ellipse([ox-u,my,ox+u,my+2*u],fill=K); d.ellipse([ox+bw//2-u,oy-bh//2+u,ox+bw//2+u//3,oy-bh//2+3*u],fill=CYAN)
        elif mood=="shocked": d.ellipse([ox-int(u*.9),my,ox+int(u*.9),my+int(u*2.4)],fill=K)
        elif mood=="sad": d.arc([ox-2*u,my+u//2,ox+2*u,my+3*u],200,340,fill=K,width=lw)
        out=cv.resize((B//S,B//S),Image.LANCZOS); im.paste(out,(cx-out.width//2,cy-out.height//2),out)
    def react(self,kicker,top,bottom,mood,footer):
        colr={"happy":GREEN,"smug":GREEN,"panic":RED,"sad":RED,"shocked":AMB}.get(mood,AMB)
        im,d=self.new(colr); d.text((60,150),kicker,font=inter("Bold",25),fill=self.tagcol)
        self.rich(d,0,196,[(top,TXT)],an(86),gap=1.02,center=True)
        self.glow(im,W//2,735,330,colr,55); self.mascot(im,W//2,735,640,mood); d=ImageDraw.Draw(im)
        self.rich(d,0,1030,[(bottom,colr)],an(72),gap=1.02,center=True)
        self.save(im,footer)
    def approve(self,kicker,no,yes,footer):
        im,d=self.new(); d.text((60,150),kicker,font=inter("Bold",25),fill=self.tagcol)
        for i,(txt,mood,colr,lab) in enumerate(((no,"sad",RED,"NOPE"),(yes,"smug",GREEN,"YES"))):
            yy=210+i*480
            d.rounded_rectangle([60,yy,W-60,yy+440],radius=30,fill=CARD,outline=colr,width=4)
            d.rounded_rectangle([60,yy,470,yy+440],radius=30,fill=tuple(int(c*0.30) for c in colr))
            self.mascot(im,265,yy+225,400,mood); d=ImageDraw.Draw(im)
            d.text((96,yy+22),lab,font=an(46),fill=colr)
            rows=self.rows_of(d,[(txt,TXT)],an(62),W-60-30-500); hh=len(rows)*int(62*1.04)
            self.rich(d,500,yy+220-hh//2,[(txt,TXT)],an(62),gap=1.04,maxw=W-60-30-500)
        self.save(im,footer)
    def ev(self,kicker,left,right,footer):
        im,d=self.new(); d.text((60,150),kicker,font=inter("Bold",25),fill=self.tagcol); y=210; ph=760; pw=(W-150)//2
        for i,((label,text,mood),x) in enumerate(((left,60),(right,60+pw+30))):
            colr={"happy":GREEN,"smug":GREEN,"panic":RED,"sad":RED,"shocked":AMB}.get(mood,AMB)
            d.rounded_rectangle([60 if i==0 else x,y,(60 if i==0 else x)+pw,y+ph],radius=32,fill=CARD,outline=colr,width=4)
            d.text((x+pw//2,y+58),self.fit(d,label.upper(),an(42),pw-40),font=an(42),fill=MUT,anchor="mm")
            self.mascot(im,x+pw//2,y+330,430,mood); d=ImageDraw.Draw(im)
            rows=self.rows_of(d,[(text.upper(),colr)],an(54),pw-60); hh=len(rows)*int(54*1.04)
            self.rich(d,x+pw//2,y+600+(120-hh)//2,[(text.upper(),colr)],an(54),gap=1.04,center=False,maxw=pw-60) if False else self.cpara_big(d,y+600+(130-hh)//2,text.upper(),an(54),colr,pw-60,x+pw//2)
        self.save(im,footer)
    def cpara_big(self,d,y,text,font,fill,maxw,cx):
        words=text.split(); line=""
        for w in words:
            if d.textlength((line+" "+w).strip(),font=font)<=maxw: line=(line+" "+w).strip()
            else: d.text((cx,y),line,font=font,fill=fill,anchor="ma"); y+=int(font.size*1.04); line=w
        d.text((cx,y),line,font=font,fill=fill,anchor="ma")
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
