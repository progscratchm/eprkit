import json
from playwright.sync_api import sync_playwright
d=json.load(open("scenes.json"))
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':1280,'height':720})
    for name,dur,body in d["scenes"]:
        pg.set_content(f"<html><head><style>{d['css']}</style></head><body>{body}</body></html>"); pg.wait_for_timeout(150)
        pg.screenshot(path=f"{name}.png")
    b.close()
print("ok")
