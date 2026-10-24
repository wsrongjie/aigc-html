"""在独立浏览器验证客户目录，不连接客户系统，不用样本规模推断生产容量。"""
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
OUTPUT = ROOT / 'outputs/asset-center/customers'
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
            context = browser.new_context(viewport={'width': 1440, 'height': 1000}, accept_downloads=True, reduced_motion='reduce')
            page = context.new_page()
            page.on('pageerror', lambda e: report['pageErrors'].append(str(e)))
            page.on('console', lambda m: report['consoleErrors'].append(m.text) if m.type == 'error' else None)
            page.on('requestfailed', lambda r: report['requestFailures'].append({'url': r.url, 'failure': r.failure}))
            page.goto(url)
            page.wait_for_function('window.assetDemoReady === true')
            page.evaluate('()=>{window.__summaryCalls=0;const original=personSummary;window.personSummary=(...args)=>{window.__summaryCalls++;return original(...args);};}')
            page.locator('#nav-item-customers').click()

            def reset():
                page.locator('#directory-reset').click()

            def submit(text=None, mode=None):
                if mode:
                    page.locator('#directory-mode').select_option(mode)
                if text is not None:
                    page.locator('#filter-query').fill(text)
                page.locator('#directory-submit').click()

            def ids():
                return page.locator('[data-customer-row]').evaluate_all('rows=>rows.map(r=>r.dataset.customerRow)')

            def export():
                with page.expect_download() as download:
                    page.locator('.head-actions [data-action="export"]').click()
                return json.loads(Path(download.value.path()).read_text(encoding='utf-8'))

            expect(page.locator('h1')).to_have_text('客户档案')
            expect(page.locator('.person-card, #main .stats')).to_have_count(0)
            expect(page.locator('[data-customer-row]')).to_have_count(50)
            expect(page.locator('.directory-result-bar')).to_contain_text('120')
            check('客户目录使用表格和真实样本数量，默认只渲染50行')
            check('风控状态列位于服务状态之后', page.locator('.customer-table thead th').evaluate_all('ths=>ths.map(t=>t.innerText)').index('风控状态') == 5)
            check('目录行同时展示风控状态与风险类型', page.locator('[data-customer-row="c5"]').inner_text().count('投诉处理中') == 1 and '退费诉求' in page.locator('[data-customer-row="c5"]').inner_text())
            check('目录不为每行计算完整客户资产和会话', page.evaluate('window.__summaryCalls') == 0)
            page.screenshot(path=str(OUTPUT / '01-客户目录-桌面.png'), full_page=True)
            first = ids()
            page.locator('#directory-next').click()
            second = ids()
            expect(page.locator('#directory-next')).to_be_focused()
            page.locator('#directory-next').click()
            third = ids()
            expect(page.locator('#directory-next')).to_be_disabled()
            expect(page.locator('#directory-page-size')).to_be_focused()
            check('三页分别50、50、20位，无重复遗漏，末页边界和焦点正确', len(second) == 50 and len(third) == 20 and len(set(first + second + third)) == 120)
            page.locator('#directory-page-size').select_option('25')
            expect(page.locator('[data-customer-row]')).to_have_count(25)
            expect(page.locator('#directory-prev')).to_be_disabled()
            page.locator('#directory-page-size').select_option('100')
            expect(page.locator('[data-customer-row]')).to_have_count(100)
            page.locator('#directory-page-size').select_option('50')
            check('每页25、50、100条可切换并返回第一页')

            page.locator('#filter-query').fill('13800001001')
            expect(page.locator('#directory-dirty')).to_be_visible()
            expect(page.locator('[data-customer-row]')).to_have_count(50)
            submit(mode='phone')
            check('手机号精确查询仅在提交后生效', ids() == ['c1'])
            expect(page.locator('.customer-phone')).to_have_text('138****1001')
            exported = export()
            check('手机号查询导出记录和查询元信息均脱敏', exported['records'][0]['phoneMasked'] == '138****1001' and '13800001001' not in json.dumps(exported))
            submit('+86 (138) 0000-1001', 'phone')
            formatted_export = export()
            check('带国家码、括号和分隔符的合法手机号使用统一规范化与脱敏', ids() == ['c1'] and formatted_export['customerQuery']['text'] == '138****1001')
            page.locator('#filter-query').fill('陈静')
            page.locator('#directory-mode').select_option('name')
            pending_export = export()
            check('未提交的草稿条件不改变当前结果和导出', ids() == ['c1'] and [r['id'] for r in pending_export['records']] == ['c1'])
            reset()
            submit('138', 'phone')
            expect(page.locator('#directory-error')).to_contain_text('11位')
            expect(page.locator('[data-customer-row]')).to_have_count(50)
            check('不完整手机号有明确校验，保留上一次已生效结果')
            reset()
            submit('李明', 'name')
            check('同名客户保留独立编号，不自动合并', set(ids()) == {'c1', 'demo-c0007'})
            page.screenshot(path=str(OUTPUT / '02-同名客户检索.png'), full_page=True)
            reset()
            submit('CUS-001', 'code')
            check('客户编号精确定位原客户', ids() == ['c1'])
            submit('CUS-00', 'code')
            expect(page.get_by_role('heading', name='没有找到匹配客户')).to_be_visible()
            check('客户编号不使用前缀模糊匹配')
            reset()
            submit('EXT-A013', 'sourceId')
            expect(page.locator('#directory-error')).to_contain_text('先选择来源系统')
            page.locator('#directory-source').select_option('wecom')
            submit()
            check('来源客户ID与来源系统共同精确定位', ids() == ['c1'])
            page.locator('#directory-condition-source').click()
            expect(page.locator('#directory-mode')).to_have_value('auto')
            expect(page.locator('#filter-query')).to_have_value('')
            expect(page.locator('[data-customer-row]')).to_have_count(50)
            check('移除来源时清除依赖的已生效来源ID，不生成无效查询')
            page.locator('#directory-source').select_option('wecom')
            submit()
            page.locator('#filter-query').fill('CUS-001')
            page.locator('#directory-condition-source').click()
            expect(page.locator('#filter-query')).to_have_value('CUS-001')
            expect(page.locator('#directory-dirty')).to_be_visible()
            check('单项移除保留其他未提交草稿，不静默丢弃输入')
            reset()
            page.locator('#directory-source').select_option('wecom')
            submit('EXT-A013', 'sourceId')
            page.locator('#directory-source').select_option('app')
            submit('APP01-OPEN-A001')
            check('小程序身份保留来源范围且可以查询', ids() == ['c1'])
            reset()
            submit('13800001001', 'name')
            check('导出查询元信息在任意检索模式下均脱敏手机号', '13800001001' not in json.dumps(export()))
            reset()

            page.locator('#directory-sales').select_option('e1')
            page.locator('#directory-more').click()
            page.locator('#directory-team').select_option('客户服务二组')
            submit()
            check('销售与团队要求同一人满足条件，不把跨人员关系拼接', ids() == [])
            page.locator('#directory-team').select_option('客户服务一组')
            page.locator('#directory-service').select_option('已开通')
            submit()
            check('销售、团队和来源服务状态组合正确', set(ids()) == {'c1', 'c2'})
            expect(page.locator('#toast')).to_be_hidden(timeout=6000)
            page.screenshot(path=str(OUTPUT / '03-组合筛选.png'), full_page=True)
            reset()
            page.locator('#directory-service').select_option('已开通')
            submit()
            check('退款申请不覆盖原服务状态', set(ids()) == {'c1', 'c2', 'c3', 'c5'})
            page.locator('#directory-service').select_option('未提供')
            submit()
            check('缺失服务状态不伪装为无服务或已终止', 'c6' in ids() or any(r['id'] == 'c6' for r in export()['records']))
            reset()

            if page.locator('#directory-risk').count() == 0:
                page.locator('#directory-more').click()
            page.locator('#directory-risk').select_option('投诉处理中')
            submit()
            check('风控筛选可定位未办结投诉客户', ids() == ['c5'])
            risk_export = export()
            check('导出记录包含风控状态、类型与判定依据', risk_export['records'][0]['risk']['level'] == '投诉处理中' and risk_export['records'][0]['risk']['type'] == '退费诉求' and risk_export['customerQuery']['risk'] == '投诉处理中' and '尚未办结' in risk_export['records'][0]['risk']['basis'])
            page.locator('#directory-risk').select_option('关注')
            submit()
            check('关注态由客户表达命中规则判定，可回溯规则编号', ids() == ['c2'] and page.evaluate("riskOf('c2').ruleId") == 'R-SERVICE')
            page.locator('#directory-risk').select_option('投诉意向')
            submit()
            check('投诉意向与已建单的投诉处理中分别统计，不重复计入', ids() == ['c3'] and page.evaluate("riskOf('c3').ruleId") == 'R-T0')
            page.locator('#directory-risk').select_option('已完结')
            submit()
            check('已办结事项保留历史风控结论', ids() == ['c4'])
            page.locator('#directory-risk').select_option('正常')
            submit()
            check('无风险信号的客户为正常，资料查看类事项不计入投诉', set(ids()) == {'c1', 'c6'})
            page.locator('#directory-risk').select_option('未评估')
            submit()
            expect(page.locator('.directory-result-bar')).to_contain_text('匹配 114 位客户')
            check('无会话无事项的目录样本统一标记未评估，不冒充正常', 'c1' not in ids() and page.locator('[data-customer-row]').evaluate_all("rows=>rows.every(r=>r.children[5].innerText.includes('未评估'))"))
            page.locator('#directory-risk').select_option('投诉处理中')
            submit()
            page.wait_for_function("document.querySelector('#toast').hidden")
            page.screenshot(path=str(OUTPUT / '04-风控筛选.png'), full_page=True)
            reset()
            page.locator('#directory-from').fill('2026-10-23')
            page.locator('#directory-to').fill('2026-10-23')
            submit()
            check('归档更新日期筛选使用明确记录时间', set(ids()) == {'c1', 'c2', 'c3', 'c5'})
            page.locator('#directory-from').fill('2026-10-24')
            submit()
            expect(page.locator('#directory-error')).to_contain_text('开始日期晚于结束日期')
            check('无效日期范围不会覆盖已生效查询', set(ids()) == {'c1', 'c2', 'c3', 'c5'})
            reset()
            submit('CUS-DEMO-0007', 'code')
            page.locator('.customer-name').click()
            expect(page.locator('#customer-profile-page')).to_contain_text('0 项资产 · 0 个会话')
            expect(page.locator('#customer-profile-page .identity-list')).to_contain_text('CALL-CUSTOMER-0007')
            check('仅身份目录样本可打开详情，不编造资产、聊天、订单或身份', 'undefined' not in page.locator('#customer-profile-page').inner_text())
            page.locator('#customer-profile-back').click()
            reset()

            page.locator('#directory-next').click()
            page.locator('.customer-table-wrap').evaluate('e=>e.scrollTop=300')
            before_ids = ids()
            before_scroll = page.locator('.customer-table-wrap').evaluate('e=>e.scrollTop')
            page.locator('.customer-name').nth(8).click()
            page.locator('#customer-profile-back').click()
            check('关闭客户详情保留目录所在页和表格阅读位置', ids() == before_ids and page.locator('.customer-table-wrap').evaluate('e=>e.scrollTop') == before_scroll)
            page.locator('#nav-item-sales').click()
            expect(page.locator('[data-sales-row]')).to_have_count(25)
            check('客户目录条件不泄漏到销售目录，分页列表正常显示')
            page.locator('#nav-item-customers').click()

            cdp = context.new_cdp_session(page)
            page.locator('#filter-query').focus()
            cdp.send('Input.imeSetComposition', {'text': 'li', 'selectionStart': 2, 'selectionEnd': 2})
            page.wait_for_timeout(300)
            cdp.send('Input.insertText', {'text': '李'})
            expect(page.locator('#filter-query')).to_have_value('李')
            expect(page.locator('[data-customer-row]')).to_have_count(50)
            page.locator('#filter-query').press('Enter')
            check('中文组合输入完整保留，Enter提交后查询', set(ids()) == {'c1', 'demo-c0007'})
            cdp.detach()
            reset()
            expect(page.locator('#toast')).to_be_hidden(timeout=6000)
            if page.locator('#directory-more').get_attribute('aria-expanded') == 'true':
                page.locator('#directory-more').click()
            for width, height in [(1440, 1000), (1280, 720), (900, 844), (390, 844), (320, 800)]:
                page.set_viewport_size({'width': width, 'height': height})
                page.evaluate('window.scrollTo(0,0)')
                check(f'{width}px 客户目录无整页横向溢出', page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'))
                expect(page.locator('#directory-submit')).to_be_visible()
                expect(page.locator('.customer-action button').first).to_be_visible()
                report['layouts'].append({'width': width, 'height': height, 'table': page.locator('.customer-table-wrap').bounding_box()})
                if width == 1280:
                    page.screenshot(path=str(OUTPUT / '04-客户目录-笔记本.png'))
                if width == 390:
                    page.screenshot(path=str(OUTPUT / '05-客户目录-窄屏.png'), full_page=True)
                page.locator('#directory-more').click()
                check(f'{width}px 客户高级筛选无整页横向溢出', page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'))
                if width == 390:
                    page.screenshot(path=str(OUTPUT / '06-客户目录-窄屏展开.png'), full_page=True)
                page.locator('#directory-more').click()

            # 仅在临时内存模拟来源字段更新，验证重新查询会刷新目录快照。
            page.set_viewport_size({'width': 1440, 'height': 1000})
            page.evaluate("""()=>{const d=AssetDemo.getData();d.customers.find(c=>c.id==='c5').phone='13800001999';const order=d.assets.find(a=>a.id==='o5');order.fields['服务状态']='已暂停';order.time='2026-10-24 12:00';}""")
            submit('13800001999', 'phone')
            check('来源字段条数不变时重新查询仍刷新手机号与服务状态', ids() == ['c5'] and '已暂停' in page.locator('[data-customer-row]').inner_text() and '10-24' in page.locator('[data-customer-row]').inner_text())
            reset()
            # 仅注入临时内存身份，验证有界DOM，不作为后台容量或性能结论。
            page.set_viewport_size({'width': 1440, 'height': 1000})
            summary_calls_before = page.evaluate('window.__summaryCalls')
            page.evaluate("""()=>{const d=AssetDemo.getData();for(let i=0;i<10000;i++)d.customers.push({id:'load-'+i,name:'扩量样本'+i,code:'LOAD-'+i,tags:[],since:'2026-10-19',directoryOnly:true,identities:[],identitySources:['wecom'],directorySales:[]});AssetDemo.nav('customers');}""")
            check('临时增加一万条身份样本仍只渲染50行，且不执行逐客户详情计算', page.locator('[data-customer-row]').count() == 50 and '10120' in page.locator('.directory-result-bar').inner_text() and page.evaluate('window.__summaryCalls') == summary_calls_before)
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
        print(f'客户目录验证报告：{OUTPUT / "verification.json"}', flush=True)


if __name__ == '__main__':
    main()
