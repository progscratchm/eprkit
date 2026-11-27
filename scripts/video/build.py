import json, subprocess, os, functools, http.server, threading
from playwright.sync_api import sync_playwright
d=json.load(open("scenes.json"))
ENC=["-c:v","libx264","-crf","20","-preset","veryfast","-pix_fmt","yuv420p","-r","30"]
def run(cmd): subprocess.run(cmd,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
def still(name,dur):
    tmp=f"_{name}.tmp.mp4"
    vf=f"format=yuv420p,loop=-1:1,trim=duration={dur},fade=t=in:st=0:d=0.4,fade=t=out:st={dur-0.4}:d=0.4"
    run(["ffmpeg","-y","-framerate","30","-i",f"{name}.png","-vf",vf]+ENC+[tmp]); os.rename(tmp,f"{name}.mp4")
# scroll scene of the sample report
root='/home/claude/eprkit/site'
srv=http.server.ThreadingHTTPServer(('127.0.0.1',8766),functools.partial(http.server.SimpleHTTPRequestHandler,directory=root))
threading.Thread(target=srv.serve_forever,daemon=True).start()
os.makedirs("scroll",exist_ok=True)
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':1280,'height':720})
    pg.goto('http://127.0.0.1:8766/sample-report.html'); pg.wait_for_timeout(300)
    total=pg.evaluate("document.body.scrollHeight")-720
    N=330  # 11 s
    for i in range(N):
        t=i/(N-1); e=t*t*(3-2*t)
        pg.evaluate(f"window.scrollTo(0,{int(e*min(total,2900))})")
        pg.screenshot(path=f"scroll/{i:04d}.jpg",type="jpeg",quality=92)
    b.close()
srv.shutdown()
tmp="_scroll.tmp.mp4"
run(["ffmpeg","-y","-framerate","30","-i","scroll/%04d.jpg","-vf","format=yuv420p,fade=t=in:st=0:d=0.4,fade=t=out:st=10.6:d=0.4"]+ENC+[tmp]); os.rename(tmp,"scroll.mp4")
order=[]
for name,dur,_ in d["scenes"]:
    still(name,dur); order.append(f"{name}.mp4")
    if name=="s5": order.append("scroll.mp4")
open("list.txt","w").write("".join(f"file '{f}'\n" for f in order))
run(["ffmpeg","-y","-f","concat","-safe","0","-i","list.txt","-c","copy","-movflags","+faststart","_final.tmp.mp4"]); os.rename("_final.tmp.mp4","eprkit-explainer.mp4")
run(["ffmpeg","-y","-i","title.png","-q:v","3","poster.jpg"])
print(subprocess.run(["ffprobe","-v","error","-show_entries","format=duration,size","-of","default=nw=1","eprkit-explainer.mp4"],capture_output=True,text=True).stdout)
