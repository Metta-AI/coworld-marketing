"""Assemble the Wall reel: cuts on Pip's narration + end card + VO + bed.
usage: python tools/assemble_wall.py [--stills] [--vo sarah|river] [--out wall/out/reel.mp4]"""
import subprocess, sys
args=sys.argv[1:]; use_stills='--stills' in args
vo=args[args.index('--vo')+1] if '--vo' in args else 'lily'
out=args[args.index('--out')+1] if '--out' in args else 'wall/out/reel.mp4'
VO_OFF=1.0; W,H,FPS=1920,1080,24
cut=[("o1_wall",2.9),("o2_timer_flip",3.2),("o3_line_to_pip",3.5),("o4_flint_vs_pip",3.0),("o5_flint_lands",3.0),("s03_scramble",4.0),("s05_hands",5.1),("s06_practice",9.4),
     ("s07c",8.1),("s07b_flint_close",5.9),("s08_lift",4.8),("s09_top",3.3),("s12_timer",3.4),("s10_last",5.5),("s11_walk",7.1)]
END_HOLD=5.5; XF=0.8
inputs=[]; fc=[]; t=0.0; starts=[]
for i,(s,d) in enumerate(cut):
    import os
    src=None
    for cand in [f"wall/open/{s}.mp4", f"wall/action/{s}.mp4", f"wall/reroll/{s}.mp4", f"wall/video/{s}.mp4", f"wall/video2/{s}.mp4"]:
        if os.path.exists(cand) and not use_stills: src=cand; break
    if src is None:
        for cand in [f"wall/stills/{s}.png", f"wall/stills2/{s}.png"]:
            if os.path.exists(cand): src=cand; break
        inputs+=["-loop","1","-t",f"{d}","-i",src]
    else: inputs+=["-i",src]
    fc.append(f"[{i}:v]trim=0:{d},setpts=PTS-STARTPTS,scale={W}:{H}:flags=lanczos,fps={FPS},format=yuv420p[v{i}]")
    starts.append(t); t+=d
body=t; n=len(cut)
fc.append("".join(f"[v{i}]" for i in range(n))+f"concat=n={n}:v=1:a=0,fps={FPS}[body]")
inputs+=["-loop","1","-t",f"{END_HOLD}","-i","assets/cards/end.png"]
fc.append(f"[{n}:v]scale={W}:{H},format=yuv420p,fps={FPS}[endc]")
fc.append(f"[body][endc]xfade=transition=fade:duration={XF}:offset={body-XF:.3f}[vx]")
total=body+END_HOLD-XF
fc.append(f"[vx]fade=in:st=0:d=0.6,fade=out:st={total-0.6:.3f}:d=0.6[vout]")
k=n+1
inputs+=["-i",f"wall/audio/vo_{vo}.wav","-i","wall/audio/bed.mp3"]
fc.append(f"[{k}:a]aresample=48000,adelay={int(VO_OFF*1000)}|{int(VO_OFF*1000)}[vo]")
fc.append(f"[{k+1}:a]aresample=48000,volume=0.16,afade=in:st=0:d=2,afade=out:st={total-3.5:.3f}:d=3.5,atrim=0:{total:.3f}[bed]")
fc.append("[vo][bed]amix=inputs=2:duration=longest:normalize=0,loudnorm=I=-17:TP=-1.5:LRA=9[aout]")
cmd=["ffmpeg","-y","-loglevel","error"]+inputs+["-filter_complex",";".join(fc),"-map","[vout]","-map","[aout]","-t",f"{total:.3f}",
     "-c:v","libx264","-crf","17","-preset","medium","-pix_fmt","yuv420p","-c:a","aac","-b:a","192k","-movflags","+faststart",out]
print('total',round(total,2),'s; cuts at',[round(x,1) for x in starts])
subprocess.run(cmd,check=True); print('wrote',out)
