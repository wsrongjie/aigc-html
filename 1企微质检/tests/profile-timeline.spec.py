"""使用隔离的无头浏览器验证档案时间线，不读取用户浏览器数据。"""
import functools
import json
import os
import re
from pathlib import Path
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'outputs/profile-timeline'
HTML = '数据资产交互设计.html'


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    os.environ.setdefault('PLAYWRIGHT_BROWSERS_PATH', str(Path.home() / 'AppData/Local/ms-playwright'))
    OUTPUT.mkdir(parents=True, exist_ok=True)
    baseline = '--baseline' in sys.argv
    report = {'checks': [], 'errors': [], 'layouts': []}

    def check(name, value=True):
        assert value, name
        report['checks'].append(name)
        print('通过：' + name, flush=True)

    server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(ROOT)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(viewport={'width': 1440, 'height': 1000}, reduced_motion='reduce')
            page = context.new_page()
            page.on('pageerror', lambda e: report['errors'].append(str(e)))
            page.goto(f'http://127.0.0.1:{server.server_port}/{HTML}')
            page.wait_for_function('window.assetDemoReady === true')
            for kind, person, target in [('customer', 'c1', 'customer'), ('sales', 'e1', 'staff')]:
                page.evaluate('(x)=>window.AssetDemo[x.kind === "customer" ? "openCustomerPage" : "openSalesPage"](x.id,{tab:"overview"})', {'kind': kind, 'id': person})
                root = page.locator(f'#{target}-record-timeline')
                root.evaluate('el=>window.scrollTo(0,window.scrollY+el.getBoundingClientRect().top-80)')
                ids = root.locator('[data-event-id]').evaluate_all('nodes=>nodes.map(n=>n.dataset.eventId)')
                expected = page.evaluate('(x)=>AssetDemo.allEvents().filter(e=>e[x.kind === "customer" ? "customers" : "employees"].includes(x.id)).map(e=>e.id)', {'kind': kind, 'id': person})
                check(kind + '记录完整且顺序一致', ids == expected)
                metrics = root.locator('[data-event-id]').evaluate_all('nodes=>({count:nodes.length,averageHeight:nodes.reduce((s,n)=>s+n.getBoundingClientRect().height,0)/nodes.length})')
                report[kind] = {'ids': ids, **metrics}
                if not baseline:
                    check(kind + '每个节点完整显示年月日时分秒', all(re.fullmatch(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', t) for t in root.locator('.profile-event-time time').all_text_contents()))
                    check(kind + '保留竖线圆点且不按日期合并', root.locator('.profile-timeline-day').count() == 0 and root.locator('.timeline-item').count() == len(ids) and root.locator('.timeline-item').first.evaluate('el=>getComputedStyle(el).borderLeftStyle==="solid"&&getComputedStyle(el,"::before").content!=="none"'))
                    check(kind + '时间与原始数据一致', root.locator('.profile-event').evaluate_all('nodes=>nodes.every(n=>n.querySelector("time").dateTime===AssetDemo.allEvents().find(e=>e.id===n.dataset.eventId).time.replace(" ","T"))'))
                page.screenshot(path=str(OUTPUT / f'{kind}-{"before" if baseline else "after"}.png'))
            if baseline:
                (OUTPUT / 'baseline.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
                return
            before = json.loads((OUTPUT / 'baseline.json').read_text(encoding='utf-8'))
            for kind in ['customer', 'sales']:
                check(kind + '保留修改前全部记录', set(before[kind]['ids']) <= set(report[kind]['ids']))
                check(kind + '平均行高下降', report[kind]['averageHeight'] < before[kind]['averageHeight'])
            page.locator('#staff-account-WX-EM-101').click()
            expected_account = page.evaluate('''() => {
                const d = AssetDemo.getData();
                const ids = d.conversations.filter(c => c.accountId === 'WX-EM-101').map(c => c.id);
                return d.messages.filter(m => ids.includes(m.conversationId)).map(m => m.id);
            }''')
            check('销售账号筛选与来源消息一致', set(page.locator('#staff-record-timeline [data-event-id]').evaluate_all('nodes=>nodes.map(n=>n.dataset.eventId)')) == set(expected_account))
            page.locator('#staff-record-timeline [data-action="locate-message"]').first.click()
            expect(page.locator('#detail')).to_be_visible()
            expect(page.locator('#detail .message.located')).to_have_count(1)
            check('点击时间线可定位原始消息')
            page.locator('#detail [data-action="drawer-close"]').click()
            page.evaluate('AssetDemo.openCustomerPage("c5",{tab:"overview"})')
            page.locator('#customer-record-timeline [data-action="open-asset"]').first.click()
            expect(page.locator('#detail')).to_be_visible()
            check('业务记录详情可打开')
            page.locator('#detail [data-action="drawer-close"]').click()
            page.evaluate('AssetDemo.openSalesPage("e4")')
            review = page.locator('#staff-record-timeline [data-tab="reviews"]').first
            version = review.get_attribute('data-version')
            review.click()
            expect(page.locator('#version-select')).to_have_value(version)
            check('审核跳转保留对应版本')
            page.locator('#detail [data-action="drawer-close"]').click()
            # 缺秒、同秒与长内容只注入隔离页面，不写入演示文件或持久化存储。
            edge = page.evaluate('''()=>{
                const rows=[
                  {id:'z',time:'2026-10-23 12:00:04'},
                  {id:'a',time:'2026-10-23 12:00:04'},
                  {id:'minute',time:'2026-10-23 11:00'},
                  {id:'day',time:'2026-10-22'},
                  {id:'missing',time:''}
                ].map(e=>({...e,type:'conversation',source:'wecom',title:'边界记录',description:'长正文<不可执行>'.repeat(25),assetId:'cv1',action:'asset'}));
                const host=document.createElement('div');host.innerHTML=profileTimeline(rows);
                return {ids:[...host.querySelectorAll('[data-event-id]')].map(n=>n.dataset.eventId),text:host.textContent,html:host.innerHTML};
            }''')
            check('同秒稳定排序与缺秒说明', edge['ids'][:2] == ['a', 'z'] and '秒未提供' in edge['text'] and '时间未提供' in edge['text'])
            check('长正文折叠且安全转义', '<details' in edge['html'] and '&lt;不可执行&gt;' in edge['html'])
            page.evaluate('''()=>{const e=AssetDemo.allEvents()[0];document.querySelector('#staff-record-timeline .section-content').innerHTML=profileTimeline([{...e,description:'长正文测试。'.repeat(80)}]);}''')
            disclosure = page.locator('.profile-event-text details')
            disclosure.locator('summary').click()
            expect(disclosure).to_have_attribute('open', '')
            disclosure.locator('summary').click()
            check('长正文可展开和收起', disclosure.get_attribute('open') is None)
            for width in [1440, 1024, 768, 390]:
                page.set_viewport_size({'width': width, 'height': 1000})
                for kind in ['customer', 'sales']:
                    page.evaluate('(kind)=>AssetDemo[kind==="customer"?"openCustomerPage":"openSalesPage"](kind==="customer"?"c1":"e1",{tab:"overview"})', kind)
                    selector = '#customer-record-timeline' if kind == 'customer' else '#staff-record-timeline'
                    page.locator(selector).evaluate('el=>window.scrollTo(0,window.scrollY+el.getBoundingClientRect().top-80)')
                    layout = page.locator(selector).evaluate('''root=>{
                        const row=root.querySelector('.profile-event'),t=row.querySelector('.profile-event-time').getBoundingClientRect(),b=row.querySelector('.profile-event-body').getBoundingClientRect();
                        return {horizontal:b.left>=t.right,overflow:document.documentElement.scrollWidth>innerWidth,contentOverflow:root.scrollWidth>root.clientWidth};
                    }''')
                    report['layouts'].append({'width': width, 'kind': kind, **layout})
                    check(f'{width}px {kind}左右布局且无横向溢出', layout['horizontal'] and not layout['overflow'] and not layout['contentOverflow'])
                    if width in [1440, 390]:
                        page.screenshot(path=str(OUTPUT / f'{kind}-{width}.png'))
            page.evaluate('AssetDemo.nav("dates")')
            check('日期归档同步左右时间线', page.locator('.archive-day .profile-event').count() > 0)
            for width in [1440, 1024, 768, 390]:
                page.set_viewport_size({'width': width, 'height': 1000})
                layout = page.locator('.archive-day').evaluate('''root=>{
                    const row=root.querySelector('.profile-event'),t=row.querySelector('.profile-event-time').getBoundingClientRect(),b=row.querySelector('.profile-event-body').getBoundingClientRect();
                    return b.left>=t.right && root.scrollWidth<=root.clientWidth && document.documentElement.scrollWidth<=innerWidth;
                }''')
                check(f'{width}px 日期归档左右布局无溢出', layout)
                if width in [1440, 390]:
                    page.locator('.archive-day').evaluate('el=>window.scrollTo(0,window.scrollY+el.getBoundingClientRect().top-80)')
                    page.screenshot(path=str(OUTPUT / f'dates-{width}.png'))
            page.locator('.date-btn[data-id="2026-10-22"]').click()
            times = page.locator('.archive-day .profile-event time').all_text_contents()
            check('切换日期后每节点保留当天完整时间', bool(times) and all(re.fullmatch(r'2026-10-22 \d{2}:\d{2}:\d{2}', t) for t in times))
            page.locator('.archive-day [data-action="locate-message"]').first.click()
            expect(page.locator('#detail .message.located')).to_have_count(1)
            page.locator('#detail [data-action="drawer-close"]').click()
            check('日期归档原消息跳转正常')
            page.locator('[data-action="category"][data-id="conversation"]').click()
            expect(page.locator('.archive-chat-shell')).to_be_visible()
            check('聊天消息分类保留原有对话目录')
            page.locator('[data-action="category"][data-id="all"]').click()
            check('全部静态事件均有秒数', page.evaluate('AssetDemo.allEvents().every(e=>/^\\d{4}-\\d{2}-\\d{2} \\d{2}:\\d{2}:\\d{2}$/.test(e.time))'))
            check('按新需求移除主动上传入口', page.locator('[data-action="upload"]').count() == 0)
            # 接口来源若仅提供分钟，仍须保留真实精度；只向隔离页面内存注入。
            page.evaluate('''()=>{AssetDemo.getData().assets.push({id:'legacy-minute',type:'material',format:'text',title:'分钟精度来源记录',source:'research',sourceId:'LEGACY',time:'2026-10-23 12:34',customers:['c1'],employees:['e1'],extract:'旧资料'});}''')
            for kind in ['customer', 'sales']:
                page.evaluate('(kind)=>AssetDemo[kind==="customer"?"openCustomerPage":"openSalesPage"](kind==="customer"?"c1":"e1",{tab:"overview"})', kind)
                legacy = page.locator('[data-event-id="asset-legacy-minute"]')
                expect(legacy.locator('time')).to_have_text('2026-10-23 12:34')
                expect(legacy).to_contain_text('秒未提供')
                check(kind + '接口来源分钟精度不伪造秒数')
            check('无页面脚本错误', not report['errors'])
            (OUTPUT / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
            browser.close()
    finally:
        server.shutdown()


if __name__ == '__main__':
    main()
