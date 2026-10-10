"""Render overlay cards (Ink & Print): night tags + end card. usage: python tools/cards.py"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
W,H=1920,1080
PAPER=(255,253,244); INK=(31,27,22); NAVY=(21,38,85); MUTED=(110,104,96)
MONO='assets/fonts/IBMPlexMono-SemiBold.ttf'; SERIF='assets/fonts/IBMPlexSerif-Regular.ttf'; MONOR='assets/fonts/IBMPlexMono-Regular.ttf'
def tag(label, out):
    im=Image.new('RGBA',(W,H),(0,0,0,0)); d=ImageDraw.Draw(im)
    f=ImageFont.truetype(MONO,34); txt=label.upper(); sp=6
    tw=sum(d.textlength(c,font=f)+sp for c in txt)-sp; th=40
    px,py=96,H-96-th-36
    box=(px-28,py-18,px+tw+28,py+th+18)
    sh=Image.new('RGBA',(W,H),(0,0,0,0)); ImageDraw.Draw(sh).rectangle([box[0]+6,box[1]+8,box[2]+6,box[3]+8],fill=(21,38,85,110)); sh=sh.filter(ImageFilter.GaussianBlur(6))
    im=Image.alpha_composite(im,sh); d=ImageDraw.Draw(im)
    d.rectangle(box,fill=PAPER+(255,)); d.line([box[0],box[3],box[2],box[3]],fill=NAVY+(255,),width=3)
    x=px
    for c in txt: d.text((x,py),c,font=f,fill=INK+(255,)); x+=d.textlength(c,font=f)+sp
    im.save(out)
def endcard(out):
    im=Image.new('RGB',(W,H),PAPER); d=ImageDraw.Draw(im)
    # faint paper grain
    import random; random.seed(3); px=im.load()
    for _ in range(26000):
        x,y=random.randrange(W),random.randrange(H); r,g,b=px[x,y]; k=random.randint(-7,4); px[x,y]=(r+k,g+k,b+k)
    f=ImageFont.truetype(SERIF,64); line='Alignment is something you learn with others.'
    tw=d.textlength(line,font=f); d.text(((W-tw)/2,H/2-120),line,font=f,fill=INK)
    wm=Image.open('assets/cards/wordmark_src.png').convert('RGBA'); s=360/wm.width; wm=wm.resize((360,int(wm.height*s)),Image.LANCZOS)
    im.paste(wm,((W-wm.width)//2,int(H/2+20)),wm)
    f2=ImageFont.truetype(MONOR,26); t='softmax.com'; tw=d.textlength(t,font=f2); d.text(((W-tw)/2,H/2+20+wm.height+28),t,font=f2,fill=MUTED)
    im.save(out)
for n in ['3','4','9','17']: tag(f'Night {n}', f'assets/cards/night_{n}.png')
endcard('assets/cards/end.png'); print('cards ok')
