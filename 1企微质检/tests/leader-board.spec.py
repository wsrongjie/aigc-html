"""在独立浏览器上下文验证领导看板，测试样本变更只发生在内存。"""
from __future__ import annotations
import functools
import hashlib
import json
import os
from pathlib import Path
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/leader-board'
HTML = '企业数据资产中心-领导看板版.html'
SOURCE = ROOT / '企业数据资产中心-交互原型.html'

class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    os.environ.setdefault('PLAYWRIGHT_BROWSERS_PATH', str(Path.home() / 'AppData/Local/ms-playwright'))
    OUT.mkdir(parents=True, exist_ok=True)
    report = {'checks': [], 'pageErrors': [], 'consoleErrors': [], 'requestFailures': [], 'layouts': []}
    baseline = json.loads((OUT / 'build-report.json').read_text(encoding='utf-8'))
    def check(name, value=True):
        assert value, name
        report['checks'].append(name)
        print('通过：' + name, flush=True)
    server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(ROOT)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f'http://127.0.0.1:{server.server_port}/{HTML}'
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(viewport={'width': 1440, 'height': 1000}, reduced_motion='reduce', accept_downloads=True)
            page = context.new_page()
            page.on('pageerror', lambda e: report['pageErrors'].append(str(e)))
            page.on('console', lambda m: report['consoleErrors'].append(m.text) if m.type == 'error' else None)
            page.on('requestfailed', lambda r: report['requestFailures'].append(r.url))
            def reload():
                page.goto(url)
                page.wait_for_function('window.assetDemoReady === true')
            def model():
                return page.evaluate('LeaderBoard.getModel()')
            def open_list(key):
                page.evaluate('(key)=>LeaderBoard.openList(key)', key)
                expect(page.locator('#detail')).to_be_visible()
            def close():
                page.keyboard.press('Escape')
                expect(page.locator('#detail')).not_to_be_visible()
            def download(selector):
                with page.expect_download() as info:
                    page.locator(selector).click()
                return json.loads(Path(info.value.path()).read_text(encoding='utf-8'))
            reload()
            expect(page.locator('#leader-board')).to_be_visible()
            check('副本默认进入领导看板，原版默认入口独立', page.evaluate('AssetDemo.getState().page') == 'board')
            m = model()
            check('在服客户按来源订单状态去重', sorted(m['serving']) == ['c1','c2','c3','c5'])
            check('关注客户与咨诉退款分别计数', sorted(x['id'] for x in m['focus']) == ['c3','c5'] and len(m['openCases']) == 1 and len(m['openRefunds']) == 1)
            check('退款金额来自实际申请且截止时间缺失不判超期', m['refundAmount'] == 1980 and len(m['overdue']) == 0 and len(m['unknownDue']) == 1)
            check('登记和办结仅使用明确时间，平均耗时剔除缺失样本', len(m['registered']) == 2 and len(m['closed']) == 2 and m['avgHours'] == 20 and len(m['missingOpened']) == 1)
            check('内容发送和覆盖独立核对', len(m['contentMessages']) == 13 and len(m['reached']) == 5 and len(m['usedVersions']) == 7)
            check('区分目录客户与有业务记录客户', len(m['recordCustomers']) == 6 and len(m['directoryOnly']) == 114)
            check('退款合同不能替代购买合同', len([x for x in m['evidence'] if x['missing']]) == 1 and next(x for x in m['evidence'] if x['missing'])['id'] == 'c5')
            page.screenshot(path=str(OUT / '01-领导看板-1440.png'), full_page=True)
            page.screenshot(path=str(OUT / '02-领导看板-首屏.png'))
            for key in m['lists']:
                open_list(key)
                expected_ids = [r['id'] for r in m['lists'][key]['rows'][:15]]
                actual_ids = page.locator('.leader-detail-row').evaluate_all('(rows)=>rows.map(r=>r.dataset.recordId)')
                check('同源下钻：' + key, expected_ids == actual_ids)
                close()
            page.locator('#leader-kpi-focus').click()
            page.screenshot(path=str(OUT / '03-重点客户明细.png'))
            row = page.locator('.leader-detail-row[data-record-id="c3"]')
            row.locator('[data-action="locate-message"]').click()
            expect(page.locator('#detail #message-msg31')).to_have_class(__import__('re').compile('located'))
            page.locator('#detail [data-action="drawer-back"]').click()
            expect(page.locator('#detail-title')).to_have_text('重点关注客户')
            page.locator('.leader-detail-row[data-record-id="c3"] [data-action="open-customer"]').click()
            expect(page.locator('#customer-profile-page')).to_be_visible()
            page.locator('#customer-profile-back').click()
            expect(page.locator('#detail-title')).to_have_text('重点关注客户')
            check('原消息与客户档案均能返回原看板明细')
            close()
            open_list('usedVersions')
            page.locator('.leader-detail-row[data-record-id="m3"] [data-action="open-asset"]').click()
            expect(page.locator('#version-select')).to_have_value('m3-v1')
            page.locator('#detail [data-action="drawer-back"]').click()
            expect(page.locator('#detail-title')).to_have_text('本期使用的已审核版本')
            check('素材下钻保留实际使用的旧版本')
            close()
            open_list('unassessed')
            page.locator('[data-action="leader-page"][data-id="2"]').click()
            expect(page.locator('.leader-detail-row')).to_have_count(15)
            exported = download('#detail [data-action="leader-export-list"]')
            check('明细分页且导出全部当前指标记录', len(exported['records']) == 114 and exported['records'][15]['id'] == page.locator('.leader-detail-row').first.get_attribute('data-record-id'))
            close()
            exported = download('.head-actions [data-action="export"]')
            check('看板导出含范围、指标和同源明细', exported['metrics']['focusCustomers'] == len(exported['details']['focus']['rows']) and exported['period']['days'] == 7 and exported['metrics']['refundApplicationAmount'] == 1980)
            page.locator('#leader-range-30').click()
            m30 = model()
            check('切换期间不改变当前存量', m30['serving'] == m['serving'] and m30['refundAmount'] == m['refundAmount'] and m30['lists']['open']['rows'] == m['lists']['open']['rows'] and len(m30['trend']) == 30)
            check('时间切换后保留键盘焦点', page.evaluate('document.activeElement.id') == 'leader-range-30')
            page.locator('#leader-range-7').click()
            # 独立内存样本：跨期办结与久远积压，验证存量不会被时间窗裁掉。
            page.evaluate("""()=>{
              assets.push({id:'test-case',type:'case',title:'跨期登记办结',source:'compliance',sourceId:'TEST-CASE',time:'2026-10-12 10:00',status:'已完结',customers:['c1'],employees:['e1'],fields:{首次记录:'2026-10-05 10:00',完成时间:'2026-10-12 10:00'}});
              assets.push({id:'test-overdue',type:'case',title:'久远积压',source:'compliance',sourceId:'TEST-OLD',time:'2026-08-10 10:00',status:'处理中',customers:['c1'],employees:['e1'],fields:{首次记录:'2026-08-10 10:00',任务截止:'2026-08-15 10:00'}});
            }""")
            a = model()
            page.locator('#leader-range-30').click()
            b = model()
            check('跨期事件进入相应时间窗、久远积压始终统计', len(b['registered']) == len(a['registered']) + 1 and len(b['closed']) == len(a['closed']) + 1 and len(a['overdue']) == len(b['overdue']) == 1)
            reload()
            page.evaluate("""()=>{
              messages.push({id:'test-before-review',conversationId:'cv1',sender:'employee',time:'2026-10-23 15:45',text:'审核之前发送',assetId:'m1',versionId:'m1-v2'});
              messages.push({id:'test-missing-review',conversationId:'cv1',sender:'employee',time:'2026-10-23 15:45',text:'依据缺失',assetId:'u0',versionId:'u0-v1'});
            }""")
            a = model()
            check('发送后审核通过不倒推发送时合规，缺失依据单列', [x['id'] for x in a['lists']['unapproved']['rows']] == ['test-before-review'] and [x['id'] for x in a['lists']['unverified']['rows']] == ['test-missing-review'])
            reload()
            # 当前只读演示值为零也有解释性空态。
            page.locator('#leader-kpi-overdue').click()
            expect(page.locator('#detail .leader-empty')).to_contain_text('当前范围暂无记录')
            close()
            check('零值指标提供明确空态')
            # 本地 TXT 上传与原数据库隔离。
            page.locator('#navigation [data-id="all"]').click()
            page.locator('[data-action="upload"]').click()
            page.locator('#upload-file').set_input_files({'name':'领导版独立验证.txt','mimeType':'text/plain','buffer':'独立存储验证'.encode('utf-8')})
            page.locator('#upload-submit').click()
            expect(page.locator('#detail-title')).to_have_text('领导版独立验证')
            close()
            reload()
            check('上传刷新恢复且快照后的上传不污染看板', page.evaluate("AssetDemo.getData().assets.some(a=>a.title==='领导版独立验证')") and model()['assetCount'] == m['assetCount'])
            dbs = page.evaluate('(async()=> (await indexedDB.databases()).map(x=>x.name))()')
            check('副本使用独立 IndexedDB', 'jianwei-asset-center-leader-v1' in dbs and 'jianwei-asset-center-prototype-v1' not in dbs)
            # 所有入口在桌面和移动视口均不造成页面横向溢出。
            for width,height in [(1920,1080),(1440,1000),(1024,900),(768,1000),(390,844)]:
                page.set_viewport_size({'width':width,'height':height})
                page.evaluate('window.scrollTo(0,0)')
                layout = page.evaluate('({width:innerWidth,body:document.documentElement.scrollWidth,duplicates:[...document.querySelectorAll("[id]")].map(n=>n.id).filter((id,i,a)=>a.indexOf(id)!==i)})')
                report['layouts'].append(layout)
                check('布局与标识唯一：'+str(width), layout['body'] <= width + 1 and not layout['duplicates'])
                page.screenshot(path=str(OUT / f'04-领导看板-{width}.png'), full_page=True)
            page.locator('#leader-kpi-focus').click()
            expect(page.locator('#detail')).to_be_visible()
            check('移动端明细可查阅且无横向溢出', page.locator('#detail').evaluate('(e)=>e.scrollWidth<=e.clientWidth+1'))
            page.screenshot(path=str(OUT / '05-移动端明细.png'))
            close()
            page.set_viewport_size({'width':1440,'height':1000})
            page.emulate_media(media='print')
            page.pdf(path=str(OUT / '领导看板-打印检查.pdf'), format='A4', landscape=True, print_background=True)
            check('打印媒体隐藏导航与操作栏', not page.locator('.sidebar').is_visible() and not page.locator('.head-actions').is_visible())
            page.emulate_media(media='screen')
            # 原有资产页、日期档案、客户与销售入口保持可用。
            for nav_id in ['all','dates','customers','sales','product','sources','board']:
                if nav_id=='product':
                    page.locator('#nav-toggle-business').click()
                page.locator(f'#navigation [data-action="nav"][data-id="{nav_id}"]').click()
                check('原入口回归：'+nav_id, page.evaluate('AssetDemo.getState().page') == nav_id)
            check('无脚本错误、控制台错误或请求失败', not report['pageErrors'] and not report['consoleErrors'] and not report['requestFailures'])
            browser.close()
        check('原型源文件保持原样', hashlib.sha256(SOURCE.read_bytes()).hexdigest() == baseline['sourceSHA256'])
    finally:
        server.shutdown()
        (OUT / 'test-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2), encoding='utf-8')
    print('完成：'+str(len(report['checks']))+' 项检查')

if __name__=='__main__':
    main()
