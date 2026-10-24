"""验证平台入口页的卡片、跳转可达性与响应式布局。"""
import functools, os, threading, json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright
os.environ.setdefault('PLAYWRIGHT_BROWSERS_PATH', str(Path.home()/'AppData/Local/ms-playwright'))
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'outputs'/'index'; OUT.mkdir(parents=True,exist_ok=True)
class H(SimpleHTTPRequestHandler):
    def log_message(self,*a): pass
srv=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(H,directory=str(ROOT)))
threading.Thread(target=srv.serve_forever,daemon=True).start()
url=f'http://127.0.0.1:{srv.server_port}/index.html'
report={'checks':[],'errors':[],'requests':[]}
def check(n,c=True):
    assert c,n; report['checks'].append(n); print('通过：'+n,flush=True)
with sync_playwright() as pw:
    b=pw.chromium.launch(headless=True)
    for w,h,name in [(1440,1000,'01-入口页-桌面'),(1280,800,'02-入口页-笔记本'),(900,900,'03-入口页-平板'),(390,844,'04-入口页-窄屏')]:
        ctx=b.new_context(viewport={'width':w,'height':h},reduced_motion='reduce')
        p=ctx.new_page()
        p.on('pageerror',lambda e:report['errors'].append(str(e)))
        p.on('requestfailed',lambda r:report['requests'].append(r.url))
        p.goto(url); p.wait_for_timeout(300)
        check(f'{w}px 无整页横向溢出', p.evaluate('document.documentElement.scrollWidth<=innerWidth+1'))
        check(f'{w}px 显示六张入口卡片', p.locator('.card').count()==6)
        p.screenshot(path=str(OUT/ f'{name}.png'), full_page=True)
        ctx.close()
    ctx=b.new_context(viewport={'width':1440,'height':1000},accept_downloads=True)
    p=ctx.new_page(); p.goto(url)
    order = p.locator('.card-grid > .card .card-body strong').all_text_contents()
    check('卡片顺序为原四张系统在前，数据资产与风控质检在最后', order == ['天枢', '包大人', '大管家', '盯盘侠', '有据', '风控质检'])
    check('数据资产与风控质检均可进入', p.locator('.card[href]').count()==2)
    for href in p.locator('.card[href]').evaluate_all("els=>els.map(e=>e.getAttribute('href'))"):
        r=p.request.get(url.rsplit('/',1)[0]+'/'+href)
        check(f'入口可达：{href}', r.ok)
    disabled=p.locator('[aria-disabled="true"]')
    check('四张占位卡标记为禁用并保留入口位置', disabled.count()==4)
    disabled.first.dispatch_event('click')
    p.wait_for_selector('#toast.show')
    check('点击占位卡给出明确提示', '暂未接入' in p.locator('#toast').inner_text())
    p.screenshot(path=str(OUT/'05-占位提示.png'))
    check('无脚本错误与失败资源', not report['errors'] and not report['requests'])
    report['result']='passed'
    (OUT/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    b.close()
srv.shutdown()
