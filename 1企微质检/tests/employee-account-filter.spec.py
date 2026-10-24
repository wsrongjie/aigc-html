"""验证员工总览的企微账号筛选，使用隔离浏览器及虚构数据。"""
from __future__ import annotations

import functools
import hashlib
import json
import os
from pathlib import Path
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'outputs/asset-center/sales'
HTML = '企业数据资产中心-交互原型.html'


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    os.environ.setdefault('PLAYWRIGHT_BROWSERS_PATH', str(Path.home() / 'AppData/Local/ms-playwright'))
    OUTPUT.mkdir(parents=True, exist_ok=True)
    report = {'checks': [], 'pageErrors': [], 'consoleErrors': [], 'requestFailures': []}

    def check(name, condition=True):
        assert condition, name
        report['checks'].append(name)
        print('通过：' + name, flush=True)

    server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(ROOT)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f'http://127.0.0.1:{server.server_port}/{HTML}'
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(viewport={'width': 1440, 'height': 1000}, reduced_motion='reduce')
            page = context.new_page()
            page.on('pageerror', lambda e: report['pageErrors'].append(str(e)))
            page.on('console', lambda m: report['consoleErrors'].append(m.text) if m.type == 'error' else None)
            page.on('requestfailed', lambda r: report['requestFailures'].append({'url': r.url, 'failure': r.failure}))
            page.goto(url)
            page.wait_for_function('window.assetDemoReady === true')
            page.locator('#nav-item-sales').click()
            page.locator('.sales-name[data-id="e1"]').click()

            def timeline_ids():
                return page.locator('#staff-record-timeline [data-event-id]').evaluate_all('nodes=>nodes.map(n=>n.dataset.eventId)')

            def customer_ids():
                return page.locator('#staff-related-customers [data-action="open-customer"]').evaluate_all('nodes=>nodes.map(n=>n.dataset.id)')

            def toggle(account):
                page.locator('#staff-account-' + account).click()

            def tab(value):
                page.locator(f'#detail .drawer-tabs [data-id="{value}"]').click()

            all_events, all_customers = timeline_ids(), customer_ids()
            check('默认全部不选，展示21条员工记录和30位实际对接客户', len(all_events) == 21 and len(all_customers) == 30 and page.locator('.staff-account-card[aria-pressed="true"]').count() == 0)
            toggle('WX-EM-101')
            expect(page.locator('#staff-account-WX-EM-101')).to_have_attribute('aria-pressed', 'true')
            expect(page.locator('#staff-account-WX-EM-101')).to_be_focused()
            check('单击账号只展示其8条消息及李明，保留键盘焦点', set(timeline_ids()) == {f'msg{i:02}' for i in range(1, 9)} and customer_ids() == ['c1'])
            expect(page.locator('.staff-account-scope')).to_contain_text('另有 8 条员工记录未关联具体企微账号')
            check('无账号依据的员工业务记录不强行归入某账号')
            page.screenshot(path=str(OUTPUT / '06-员工档案-账号筛选.png'))
            toggle('WX-EM-101')
            check('再次单击取消，恢复完整时间线与全部客户', timeline_ids() == all_events and set(customer_ids()) == set(all_customers))
            page.locator('#staff-account-WX-EM-108').focus()
            page.keyboard.press('Space')
            check('空格可选中另一账号，限定5条消息与陈静', set(timeline_ids()) == {'msg09', 'msg10', 'msg11', 'msg12', 'msg32'} and customer_ids() == ['c2'])
            toggle('WX-EM-101')
            check('多选按并集展示13条去重记录与2位客户', len(timeline_ids()) == 13 and len(set(timeline_ids())) == 13 and set(customer_ids()) == {'c1', 'c2'})
            expect(page.locator('.staff-account-card[aria-pressed="true"]')).to_have_count(2)
            page.screenshot(path=str(OUTPUT / '07-员工档案-账号多选.png'))
            toggle('WX-EM-108')
            check('取消其中一个账号保留另一账号的结果', set(timeline_ids()) == {f'msg{i:02}' for i in range(1, 9)} and customer_ids() == ['c1'])
            page.locator('#staff-account-clear').click()
            expect(page.locator('#staff-account-clear')).to_be_disabled()
            expect(page.locator('#staff-account-WX-EM-101')).to_be_focused()
            check('恢复全部账号清空选择，结果与初始一致', timeline_ids() == all_events and set(customer_ids()) == set(all_customers))

            toggle('WX-EM-101')
            page.locator('#staff-record-timeline [data-action="locate-message"]').first.click()
            expect(page.locator('#detail .message')).to_have_count(8)
            page.locator('#detail [data-action="drawer-back"]').click()
            expect(page.locator('#staff-account-WX-EM-101')).to_have_attribute('aria-pressed', 'true')
            check('查看原始会话后返回保留所选账号及筛选结果', len(timeline_ids()) == 8 and customer_ids() == ['c1'])
            tab('customers')
            expect(page.locator('#detail .record-row')).to_have_count(30)
            tab('chat')
            expect(page.locator('#detail .chat-thread')).to_have_count(2)
            tab('overview')
            expect(page.locator('#staff-account-WX-EM-101')).to_have_attribute('aria-pressed', 'true')
            check('账号选择只作用于总览下方两区，其他标签保持原有范围')
            page.evaluate("AssetDemo.openDetail('sales','e2')")
            expect(page.locator('.staff-account-card[aria-pressed="true"]')).to_have_count(0)
            expect(page.locator('.staff-account-card')).to_have_count(1)
            page.locator('#detail [data-action="drawer-back"]').click()
            expect(page.locator('#staff-account-WX-EM-101')).to_have_attribute('aria-pressed', 'true')
            check('另一员工独立默认全量，返回原员工恢复选择')
            page.keyboard.press('Escape')
            page.locator('.sales-name[data-id="e1"]').click()
            expect(page.locator('.staff-account-card[aria-pressed="true"]')).to_have_count(0)
            check('关闭后重新打开员工档案默认恢复全量')

            # 临时补充来源明确的账号字段，验证业务事件依据原始关联而非客户猜测。
            page.evaluate("()=>{AssetDemo.getData().assets.find(a=>a.id==='o1').accountId='WX-EM-108';}")
            toggle('WX-EM-108')
            check('来源有明确账号字段时纳入对应业务记录和客户', 'asset-o1' in timeline_ids() and set(customer_ids()) == {'c1', 'c2'})
            page.evaluate("()=>{delete AssetDemo.getData().assets.find(a=>a.id==='o1').accountId;}")
            page.locator('#staff-account-clear').click()
            toggle('WX-EM-108')
            check('移除账号依据后不凭同员工关系纳入订单', 'asset-o1' not in timeline_ids() and customer_ids() == ['c2'])
            page.keyboard.press('Escape')

            # 同一客户同时出现在两个账号时，账号并集只保留一个客户身份。
            page.evaluate("()=>{AssetDemo.getData().conversations.push({id:'account-filter-overlap',customerId:'c1',employeeId:'e1',accountId:'WX-EM-108',account:'企微·晨晨'});}")
            page.locator('#sales-submit').click()
            page.locator('.sales-name[data-id="e1"]').click()
            toggle('WX-EM-101')
            toggle('WX-EM-108')
            check('同客户跨账号出现时客户并集按稳定ID去重', len(customer_ids()) == 2 and set(customer_ids()) == {'c1', 'c2'})
            page.keyboard.press('Escape')
            page.evaluate("()=>{const d=AssetDemo.getData();d.conversations.splice(d.conversations.findIndex(c=>c.id==='account-filter-overlap'),1);const cv=d.conversations.find(c=>c.id==='cv1');cv.accountId='WX-PROBE-NEW';cv.account='企微·来源新号';}")
            page.locator('#sales-submit').click()
            page.locator('.sales-name[data-id="e1"]').click()
            expect(page.locator('.staff-account-card')).to_have_count(3)
            expect(page.locator('#staff-account-WX-PROBE-NEW')).to_be_visible()
            toggle('WX-PROBE-NEW')
            check('仅会话来源提供的账号同时进入员工详情并可筛选', len(timeline_ids()) == 8 and customer_ids() == ['c1'])
            page.keyboard.press('Escape')
            page.evaluate("()=>{const cv=AssetDemo.getData().conversations.find(c=>c.id==='cv1');cv.accountId='WX-EM-101';cv.account='企微·张晨';}")
            page.locator('#sales-submit').click()
            page.locator('.sales-name[data-id="demo-e0005"]').click()
            toggle('WX-DEMO-0005-1')
            check('无留存消息的目录账号选择后显示真实空态', timeline_ids() == [] and customer_ids() == [])
            page.keyboard.press('Escape')
            page.locator('.sales-name[data-id="e1"]').click()
            for width, height in [(1440, 1000), (1280, 720), (900, 844), (390, 844), (320, 800)]:
                page.set_viewport_size({'width': width, 'height': height})
                toggle('WX-EM-101')
                expect(page.locator('#staff-account-WX-EM-101')).to_be_focused()
                check(f'{width}px 账号筛选无抽屉横向溢出且按钮可操作', page.locator('#detail .drawer-body').evaluate('e=>e.scrollWidth<=e.clientWidth+1'))
                if width == 390:
                    page.screenshot(path=str(OUTPUT / '08-员工档案-窄屏账号筛选.png'))
                toggle('WX-EM-101')
            check('没有浏览器脚本、控制台或资源请求错误', not any(report[k] for k in ['pageErrors', 'consoleErrors', 'requestFailures']))
            report['sha256'] = hashlib.sha256((ROOT / HTML).read_bytes()).hexdigest()
            report['result'] = 'passed'
            browser.close()
    except Exception as error:
        report['result'] = 'failed'
        report['failure'] = str(error)
        raise
    finally:
        server.shutdown()
        server.server_close()
        (OUTPUT / 'account-filter-verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f'员工账号筛选验证报告：{OUTPUT / "account-filter-verification.json"}', flush=True)


if __name__ == '__main__':
    main()
