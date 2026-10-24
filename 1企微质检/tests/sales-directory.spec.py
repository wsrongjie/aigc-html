"""独立浏览器验证销售目录和企微账号关系，所有数据均为虚构演示。"""
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
            page.evaluate('()=>{window.__summaryCalls=0;const original=personSummary;window.personSummary=(...args)=>{window.__summaryCalls++;return original(...args);};}')
            page.locator('#nav-item-sales').click()

            def ids():
                return page.locator('[data-sales-row]').evaluate_all('rows=>rows.map(r=>r.dataset.salesRow)')

            def reset():
                page.locator('#sales-reset').click()

            def submit(text=None):
                if text is not None:
                    page.locator('#filter-query').fill(text)
                page.locator('#sales-submit').click()

            def export():
                with page.expect_download() as info:
                    page.locator('.head-actions [data-action="export"]').click()
                return json.loads(Path(info.value.path()).read_text(encoding='utf-8'))

            expect(page.locator('.person-card, #main .stats')).to_have_count(0)
            expect(page.locator('[data-sales-row]')).to_have_count(25)
            check('销售目录默认只展示25位员工，移除人物卡片和全库资产统计')
            expect(page.locator('.sales-totals')).to_contain_text('销售员工 40 位')
            expect(page.locator('.sales-totals')).to_contain_text('已标识企微账号 152 个')
            check('员工与账号分别按演示数据计数，内容作者不混入销售目录', 'e4' not in ids())
            check('目录不逐行调用完整档案汇总', page.evaluate('window.__summaryCalls') == 0)
            page.screenshot(path=str(OUTPUT / '01-销售目录-桌面.png'), full_page=True)
            first = ids()
            page.locator('#sales-next').click()
            second = ids()
            expect(page.locator('#sales-next')).to_be_disabled()
            expect(page.locator('#sales-page-size')).to_be_focused()
            check('两页25/15位无重复遗漏，末页边界和焦点正确', len(second) == 15 and len(set(first + second)) == 40)
            page.locator('#sales-page-size').select_option('50')
            expect(page.locator('[data-sales-row]')).to_have_count(40)
            page.locator('#sales-page-size').select_option('100')
            expect(page.locator('[data-sales-row]')).to_have_count(40)
            page.locator('#sales-page-size').select_option('25')
            check('每页25/50/100位切换正常并返回第一页')

            page.locator('#filter-query').fill('张晨')
            expect(page.locator('#sales-dirty')).to_be_visible()
            expect(page.locator('[data-sales-row]')).to_have_count(25)
            submit()
            check('姓名检索提交后生效，同名员工保留独立编号', set(ids()) == {'e1', 'demo-e0005'})
            page.screenshot(path=str(OUTPUT / '03-同名员工检索.png'), full_page=True)
            submit('EMP-001')
            check('员工编号精确定位', ids() == ['e1'])
            submit('WX-EM-108')
            check('任一个企微账号可反查所属员工', ids() == ['e1'])
            exported = export()
            check('员工导出与已生效账号检索一致', [r['id'] for r in exported['records']] == ['e1'] and {a['id'] for a in exported['records'][0]['accounts']} == {'WX-EM-101', 'WX-EM-108'})
            page.locator('#filter-query').fill('陈悦')
            check('未提交输入不改变员工结果或导出', ids() == ['e1'] and [r['id'] for r in export()['records']] == ['e1'])
            submit('WX-EM-10')
            expect(page.get_by_role('heading', name='没有找到匹配员工')).to_be_visible()
            check('明确账号ID不作前缀模糊匹配')
            reset()
            page.locator('#sales-team').select_option('客户服务一组')
            page.locator('#sales-account-filter').select_option('multi')
            submit()
            check('团队与多账号条件组合正确', len(ids()) == 20 and 'e1' in ids() and 'e3' not in ids())
            page.locator('#filter-query').fill('EMP-001')
            page.locator('#sales-condition-team').click()
            expect(page.locator('#filter-query')).to_have_value('EMP-001')
            expect(page.locator('#sales-dirty')).to_be_visible()
            check('移除单项条件保留其他未提交输入')
            reset()
            page.locator('#sales-account-filter').select_option('none')
            submit()
            expect(page.get_by_role('heading', name='没有找到匹配员工')).to_be_visible()
            check('无匹配账号情况时给出真实空态')
            reset()
            expect(page.locator('#toast')).to_be_hidden(timeout=6000)

            page.locator('#sales-accounts-e1').focus()
            page.keyboard.press('Enter')
            expect(page.locator('#sales-accounts-e1')).to_be_focused()
            expect(page.locator('#sales-account-panel-e1')).to_be_visible()
            account_rows = page.locator('#sales-account-panel-e1 [data-sales-account]')
            check('键盘可展开两个企微账号，显示各自真实留存客户范围', account_rows.count() == 2 and account_rows.locator('td:nth-child(3)').all_text_contents() == ['1 位', '1 位'])
            page.screenshot(path=str(OUTPUT / '02-企微账号展开.png'), full_page=True)
            page.locator('#sales-accounts-e2').click()
            expect(page.locator('#sales-account-panel-e1')).to_be_visible()
            expect(page.locator('#sales-account-panel-e2')).to_be_visible()
            page.locator('#sales-accounts-e2').click()
            expect(page.locator('#sales-account-panel-e1')).to_be_visible()
            expect(page.locator('#sales-account-panel-e2')).not_to_be_visible()
            check('多名员工账号可独立展开收起，不覆盖其他员工选择')
            expected_count = int(page.locator('[data-sales-row="e1"] .sales-customer-count').inner_text())
            page.locator('.sales-name[data-id="e1"]').click()
            page.locator('#detail .drawer-tabs [data-id="customers"]').click()
            expect(page.locator('#detail .record-row')).to_have_count(expected_count)
            check('员工列表客户去重数量与详情关系名单一致', expected_count == 30)
            page.keyboard.press('Escape')
            expect(page.locator('#sales-account-panel-e1')).to_be_visible()
            check('关闭详情保留原账号展开状态')
            reset()
            page.locator('.sales-table-wrap').evaluate('e=>e.scrollTop=200')
            position = page.locator('.sales-table-wrap').evaluate('e=>e.scrollTop')
            page.locator('[data-action="sales-accounts"]').nth(6).click()
            check('展开账号后保留表格纵向阅读位置', page.locator('.sales-table-wrap').evaluate('e=>e.scrollTop') == position)
            page.locator('.sales-name').nth(6).click()
            page.keyboard.press('Escape')
            check('关闭详情保留表格阅读位置及当前页', page.locator('.sales-table-wrap').evaluate('e=>e.scrollTop') == position and len(ids()) == 25)
            reset()
            submit('EMP-DEMO-0005')
            page.locator('.sales-name').click()
            expect(page.locator('#detail .profile-numbers strong')).to_have_text(['0', '0', '0'])
            expect(page.locator('#detail .identity')).to_have_count(4)
            check('纯目录员工保留账号信息，不编造资产会话或消息', 'undefined' not in page.locator('#detail').inner_text())
            page.keyboard.press('Escape')
            reset()

            # 同一客户在来源映射和会话重复出现，员工和账号的去重口径分别验证。
            page.evaluate("()=>{const d=AssetDemo.getData();d.customers.find(c=>c.id==='c1').directorySales=['e1'];const e=d.employees.find(e=>e.id==='e1');e.accountIds.push('WX-EM-101');e.accounts.push('重复来源名称');}")
            submit('EMP-001')
            check('重复客户关系和重复账号ID不重复计数', page.locator('.sales-customer-count').inner_text() == '30' and len(export()['records'][0]['accounts']) == 2)
            page.evaluate("()=>{const d=AssetDemo.getData();d.customers.find(c=>c.id==='c1').directorySales=[];const e=d.employees.find(e=>e.id==='e1');e.accountIds.pop();e.accounts.pop();}")
            reset()
            cdp = context.new_cdp_session(page)
            page.locator('#filter-query').focus()
            cdp.send('Input.imeSetComposition', {'text': 'zhang', 'selectionStart': 5, 'selectionEnd': 5})
            page.wait_for_timeout(300)
            cdp.send('Input.insertText', {'text': '张'})
            expect(page.locator('#filter-query')).to_have_value('张')
            expect(page.locator('[data-sales-row]')).to_have_count(25)
            page.locator('#filter-query').press('Enter')
            check('中文组合输入不中断，Enter提交查询', set(ids()) == {'e1', 'demo-e0005'})
            cdp.detach()
            reset()
            submit('+86 (138) 0000-1001')
            check('员工导出查询元信息同样对完整号码脱敏', export()['salesQuery']['text'] == '138****1001')
            reset()
            page.locator('#nav-item-customers').click()
            expect(page.locator('[data-customer-row]')).to_have_count(50)
            check('销售筛选不泄漏到客户目录')
            page.locator('#nav-item-sales').click()
            expect(page.locator('#toast')).to_be_hidden(timeout=6000)
            for width, height in [(1440, 1000), (1280, 720), (900, 844), (390, 844), (320, 800)]:
                page.set_viewport_size({'width': width, 'height': height})
                page.evaluate('window.scrollTo(0,0)')
                check(f'{width}px 销售目录无整页横向溢出', page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'))
                page.locator('#sales-accounts-e1').click()
                expect(page.locator('#sales-account-panel-e1')).to_be_visible()
                check(f'{width}px 账号展开不产生整页横向溢出', page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'))
                report['layouts'].append({'width': width, 'height': height, 'table': page.locator('.sales-table-wrap').bounding_box()})
                if width == 1280:
                    page.screenshot(path=str(OUTPUT / '04-销售目录-笔记本.png'))
                if width == 390:
                    page.screenshot(path=str(OUTPUT / '05-销售目录-窄屏展开.png'), full_page=True)
                page.locator('#sales-accounts-e1').click()

            page.set_viewport_size({'width': 1440, 'height': 1000})
            page.evaluate("()=>{const e=AssetDemo.getData().employees.find(e=>e.id==='e1');e.name='张晨改名';}")
            submit('EMP-001')
            check('同条数来源字段更新后重新查询刷新，稳定编号保留历史关系', ids() == ['e1'] and '张晨改名' in page.locator('[data-sales-row]').inner_text() and page.locator('.sales-customer-count').inner_text() == '30')
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
        (OUTPUT / 'verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f'销售目录验证报告：{OUTPUT / "verification.json"}', flush=True)


if __name__ == '__main__':
    main()
