"""验证客户档案主内容区二级页、适当性元数据和跨入口返回。"""
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
OUTPUT = ROOT / 'outputs/asset-center/customers/profile-page'
HTML = '企业数据资产中心-交互原型.html'


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    os.environ.setdefault('PLAYWRIGHT_BROWSERS_PATH', str(Path.home() / 'AppData/Local/ms-playwright'))
    OUTPUT.mkdir(parents=True, exist_ok=True)
    report = {'checks': [], 'pageErrors': [], 'consoleErrors': [], 'requestFailures': [], 'layouts': []}

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
            context = browser.new_context(viewport={'width': 1440, 'height': 1000}, reduced_motion='reduce', accept_downloads=True)
            page = context.new_page()
            page.on('pageerror', lambda e: report['pageErrors'].append(str(e)))
            page.on('console', lambda m: report['consoleErrors'].append(m.text) if m.type == 'error' else None)
            page.on('requestfailed', lambda r: report['requestFailures'].append({'url': r.url, 'failure': r.failure}))
            page.goto(url)
            page.wait_for_function('window.assetDemoReady === true')

            def open_customer(code='CUS-001'):
                page.evaluate("AssetDemo.nav('customers')")
                page.locator('#directory-mode').select_option('code')
                page.locator('#filter-query').fill(code)
                page.locator('#directory-submit').click()
                page.locator('.customer-name').click()

            def tab(tab_id):
                page.locator(f'#customer-profile-tabs [data-id="{tab_id}"]').click()

            def export_profile():
                with page.expect_download() as info:
                    page.locator('#customer-profile-export').click()
                return json.loads(Path(info.value.path()).read_text(encoding='utf-8'))

            open_customer()
            expect(page.locator('#customer-profile-page')).to_be_visible()
            expect(page.locator('#detail')).not_to_be_visible()
            expect(page.locator('#nav-item-customers')).to_have_attribute('aria-current', 'page')
            expect(page.locator('#breadcrumb')).to_have_text('客户档案 / 李明')
            check('客户从目录进入主内容区二级页，不打开客户抽屉')
            expect(page.locator('#customer-profile-tabs [role="tab"]')).to_have_count(8)
            expect(page.locator('#customer-profile-tabs [data-id="profile"]')).to_have_attribute('aria-selected', 'true')
            expect(page.locator('#customer-profile-page')).to_contain_text('138****1001')
            expect(page.locator('#customer-profile-page')).to_contain_text('wx********09')
            check('默认进入客户信息页，展示脱敏手机微信，标签共八个')
            info_body = page.locator('#customer-profile-content').inner_text()
            check('客户信息页集中展示基础身份、联系方式、证件与跨系统身份', all(x in info_body for x in ['基础身份', '联系方式', '证件与实名', '跨系统身份', '310***********1021', 'KYC-CUS-001', 'EXT-A013']))
            check('客户信息页按来源留存，不提供明文证件入口', '不提供明文查看入口' in info_body)
            page.screenshot(path=str(OUTPUT / '01-客户档案-客户信息.png'), full_page=True)

            tab('overview')
            overview_body = page.locator('#customer-profile-content').inner_text()
            check('档案总览不再重复展示号码身份与证件', '310***********1021' not in overview_body and 'EXT-A013' not in overview_body)
            check('档案总览保留时间线、对接人员与获客信息，并提供客户信息入口', all(x in overview_body for x in ['完整记录时间线', '实际对接人员', '获客与服务', '客户信息']))
            expect(page.locator('.person-tags')).to_contain_text('风控 · 正常')
            expect(page.locator('#customer-risk-panel')).to_contain_text('未命中风险规则')
            expect(page.locator('#customer-risk-banner')).to_have_count(0)
            check('客户页头与总览均展示风控状态及判定依据，正常客户不占风险说明条')
            page.screenshot(path=str(OUTPUT / '02-客户档案-总览.png'), full_page=True)

            tab('suitability')
            body = page.locator('#customer-profile-content').inner_text()
            check('适当性页展示投资者类型、风险等级和测评时点', all(x in body for x in ['普通投资者', 'C3 · 稳健型', '2026-09-12 10:16', '2027-09-11']))
            check('财务经验和投资目标按来源区间留存', all(x in body for x in ['30–50万元', '100–300万元', '5–10年', '可承受10%以内损失']))
            check('适当性页只留实名摘要，证件号引导至客户信息页', '310***********1021' not in body and '客户信息' in body and 'KYC-CUS-001' in body)
            page.screenshot(path=str(OUTPUT / '03-客户档案-适当性.png'), full_page=True)
            payload = export_profile()
            raw = json.dumps(payload, ensure_ascii=False)
            check('客户档案导出保留元数据来源且不包含完整手机微信', payload['record']['id'] == 'c1' and payload['record']['metadata']['suitability']['sourceRecordId'] == 'KYC-CUS-001' and '13800001001' not in raw and 'wx_liming_2609' not in raw)

            tab('chat')
            expect(page.locator('#customer-profile-content .chat-thread')).to_have_count(2)
            page.locator('#customer-profile-content .chat-thread').nth(1).click()
            check('二级页内可切换多销售企微会话', page.evaluate("AssetDemo.getState().customerProfile.threadId") == 'cv7')
            expect(page.locator('#customer-profile-content [data-action="thread"][data-id="cv7"]')).to_be_focused()
            check('会话切换后恢复当前会话按钮焦点，支持连续键盘浏览')
            tab('business')
            expect(page.locator('#customer-profile-content [data-product-reference="p1"]')).to_be_visible()
            expect(page.locator('#customer-profile-content [data-action="open-asset"][data-id="o1"]').first).to_be_visible()
            check('交易与服务页保留商品和订单的明确关系')
            page.locator('#customer-profile-content [data-action="open-asset"][data-id="o1"]').first.click()
            expect(page.locator('#detail')).to_be_visible()
            page.keyboard.press('Escape')
            expect(page.locator('#customer-profile-page')).to_be_visible()
            check('客户页内查看资产使用抽屉，关闭后仍停留原标签')

            page.locator('#customer-profile-back').click()
            expect(page.locator('[data-customer-row="c1"]')).to_be_visible()
            expect(page.locator('#filter-query')).to_have_value('CUS-001')
            expect(page.locator('#customer-open-c1')).to_be_focused()
            check('返回目录保留已提交查询并恢复触发按钮焦点')

            # 从直播抽屉进入客户二级页，再返回恢复直播动作标签。
            page.evaluate("AssetDemo.nav('live')")
            page.locator('[data-asset-row="l1"] .title').click()
            page.locator('#detail [role="tab"][data-id="actions"]').click()
            page.locator('#detail [data-action="open-customer"][data-id="c1"]').first.click()
            expect(page.locator('#customer-profile-page')).to_be_visible()
            expect(page.locator('#detail')).not_to_be_visible()
            page.locator('#customer-profile-back').click()
            expect(page.locator('#detail')).to_be_visible()
            expect(page.locator('#detail [role="tab"][data-id="actions"]')).to_have_class('active')
            check('从资产抽屉进入客户页后可恢复原对象、标签和抽屉')
            page.keyboard.press('Escape')

            # 嵌套来源同时恢复底层客户页和长抽屉的阅读位置。
            open_customer()
            profile_y = page.evaluate('window.scrollTo(0,900);window.scrollY')
            page.evaluate("AssetDemo.openDetail('sales','e1',{tab:'customers'})")
            drawer_y = page.locator('#detail .drawer-body').evaluate('e=>{e.scrollTop=e.scrollHeight;return e.scrollTop}')
            page.evaluate("document.querySelector('#detail [data-action=\"open-customer\"][data-id=\"c2\"]').click()")
            page.locator('#customer-profile-back').click()
            expect(page.locator('#detail')).to_be_visible()
            page.wait_for_timeout(50)
            check('从长员工抽屉进入客户页再返回可恢复抽屉滚动位置', drawer_y > 0 and abs(page.locator('#detail .drawer-body').evaluate('e=>e.scrollTop') - drawer_y) <= 1)
            page.keyboard.press('Escape')
            check('嵌套客户页经抽屉跳转后可恢复底层页面滚动位置', abs(page.evaluate('window.scrollY') - profile_y) <= 1)
            page.locator('#customer-profile-back').click()

            # 纯目录样本不得生成金融画像。
            page.evaluate("AssetDemo.nav('customers')")
            page.locator('#directory-mode').select_option('code')
            page.locator('#filter-query').fill('CUS-DEMO-0007')
            page.locator('#directory-submit').click()
            page.locator('.customer-name').click()
            expect(page.locator('#customer-profile-page')).to_contain_text('CALL-CUSTOMER-0007')
            tab('suitability')
            text = page.locator('#customer-profile-content').inner_text()
            check('纯目录客户保持未提供，不编造性别年龄收入风险等级', text.count('未提供') >= 10 and 'C3' not in text and '30–50万元' not in text)
            page.locator('#customer-profile-back').click()

            # 风控状态需可回溯到来源事项。
            page.evaluate("AssetDemo.openCustomerPage('c5')")
            expect(page.locator('#customer-risk-banner')).to_contain_text('未办结事项')
            expect(page.locator('#customer-risk-banner')).to_contain_text('REF-20261022-005')
            expect(page.locator('#customer-risk-banner')).to_contain_text('CASE-20261022-005')
            check('异常风控在顶部说明原因，列出未办结事项及编号')
            page.wait_for_function("document.querySelector('#toast').hidden")
            page.screenshot(path=str(OUTPUT / '07-风控说明条.png'), full_page=True)
            page.locator('#customer-risk-banner [data-action="open-asset"][data-id="rf1"]').click()
            expect(page.locator('#detail')).to_be_visible()
            expect(page.locator('#detail-title')).to_contain_text('退款')
            page.keyboard.press('Escape')
            expect(page.locator('#customer-profile-page')).to_be_visible()
            page.locator('#customer-risk-banner [data-action="customer-profile-tab"][data-id="chat"]').click()
            expect(page.locator('#customer-profile-content .chat-thread')).to_have_count(1)
            check('说明条可直达退款记录与沟通记录，关闭抽屉后仍停留客户页')
            page.locator('#customer-profile-tabs [data-id="overview"]').click()
            expect(page.locator('#customer-risk-panel')).to_contain_text('投诉处理中')
            expect(page.locator('#customer-risk-panel')).to_contain_text('退费诉求')
            page.locator('#customer-risk-panel [data-action="open-asset"]').click()
            expect(page.locator('#detail')).to_be_visible()
            expect(page.locator('#detail-title')).to_contain_text('周宁')
            page.keyboard.press('Escape')
            expect(page.locator('#customer-profile-page')).to_be_visible()
            check('总览风控卡同样可跳转来源事项')
            page.locator('#customer-profile-back').click()

            # 投诉意向需展示命中原文与规则，并可定位原始消息。
            page.evaluate("AssetDemo.openCustomerPage('c3')")
            expect(page.locator('#customer-risk-banner')).to_contain_text('R-T0')
            expect(page.locator('#customer-risk-banner')).to_contain_text('再不处理我就投诉')
            page.locator('#customer-risk-banner [data-action="locate-message"][data-id="msg31"]').click()
            expect(page.locator('#detail')).to_be_visible()
            expect(page.locator('#message-msg31')).to_contain_text('再不处理我就投诉')
            expect(page.locator('#detail .message-locator')).to_contain_text('msg31')
            page.keyboard.press('Escape')
            page.locator('#customer-profile-back').click()
            check('投诉意向展示命中原文与规则编号，可定位到原始消息')

            page.evaluate("AssetDemo.openCustomerPage('c4')")
            expect(page.locator('#customer-risk-banner')).to_contain_text('历史结论')
            expect(page.locator('#customer-risk-banner')).to_contain_text('办结，保留历史结论')
            page.locator('#customer-profile-back').click()
            check('已完结事项按历史结论展示，不当作当前风险')

            # 风险测评过期必须显式呈现。
            page.locator('#directory-mode').select_option('code')
            page.locator('#filter-query').fill('CUS-004')
            page.locator('#directory-submit').click()
            page.locator('.customer-name').click()
            expect(page.locator('#customer-profile-risk-status')).to_contain_text('已过期')
            tab('suitability')
            check('过期测评显示原评估时点和有效期，不当作当前结论', '2025-09-01 09:25' in page.locator('#customer-profile-content').inner_text() and '2026-08-31' in page.locator('#customer-profile-content').inner_text())
            page.locator('#customer-profile-back').click()

            for width, height in [(1440, 1000), (1280, 720), (900, 844), (390, 844), (320, 800)]:
                page.set_viewport_size({'width': width, 'height': height})
                open_customer()
                check(f'{width}px 客户二级页无整页横向溢出', page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'))
                expect(page.locator('#customer-profile-back')).to_be_in_viewport(ratio=1)
                page.wait_for_function("document.querySelector('#toast').hidden")
                if width == 390:
                    page.screenshot(path=str(OUTPUT / '06-客户信息-窄屏.png'), full_page=True)
                tab('chat')
                check(f'{width}px 客户聊天局部布局不撑宽页面', page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'))
                if width == 1280:
                    page.wait_for_function("document.querySelector('#toast').hidden")
                    page.screenshot(path=str(OUTPUT / '04-客户档案-笔记本.png'), full_page=True)
                if width == 390:
                    page.wait_for_function("document.querySelector('#toast').hidden")
                    page.screenshot(path=str(OUTPUT / '05-客户档案-窄屏.png'), full_page=True)
                page.locator('#customer-profile-back').click()
                report['layouts'].append({'width': width, 'height': height, 'passed': True})

            check('客户二级页没有浏览器脚本、控制台或资源请求错误', not any(report[k] for k in ['pageErrors', 'consoleErrors', 'requestFailures']))
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
        (OUTPUT / 'verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f'客户二级页验证报告：{OUTPUT / "verification.json"}', flush=True)


if __name__ == '__main__':
    main()
