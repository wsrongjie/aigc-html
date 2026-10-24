"""使用独立 Chromium 上下文验证资产检索，不连接客户系统。"""
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
OUTPUT = ROOT / 'outputs/asset-center/search'
HTML = '企业数据资产中心-交互原型.html'


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


def verify_sidebar(page, check):
    """覆盖折叠导航的键盘、当前栏目、跨入口跳转和窄侧栏路径。"""
    output = ROOT / 'outputs/asset-center/menu'
    output.mkdir(parents=True, exist_ok=True)
    for group in ['content', 'business']:
        expect(page.locator(f'#nav-toggle-{group}')).to_have_attribute('aria-expanded', 'false')
        expect(page.locator(f'#nav-group-{group}')).not_to_be_visible()
    check('两组一级菜单默认收起，八个子菜单不可见')
    page.screenshot(path=str(output / '01-一级菜单-收起.png'), full_page=True)
    page.locator('#nav-toggle-content').focus()
    page.keyboard.press('Enter')
    expect(page.locator('#nav-toggle-content')).to_be_focused()
    expect(page.locator('#nav-item-material')).to_be_visible()
    expect(page.locator('h1')).to_have_text('资产检索')
    page.locator('#nav-toggle-business').focus()
    page.keyboard.press('Space')
    expect(page.locator('#nav-toggle-business')).to_be_focused()
    expect(page.locator('#nav-item-order')).to_be_visible()
    expect(page.locator('#nav-item-material')).to_be_visible()
    check('Enter和空格可独立展开两组菜单，焦点保留且不切换内容页')
    page.locator('#nav-item-material').click()
    expect(page.locator('h1')).to_have_text('营销素材')
    expect(page.locator('#nav-item-material')).to_have_attribute('aria-current', 'page')
    expect(page.locator('#nav-toggle-content')).to_have_class('nav-btn nav-parent current')
    page.screenshot(path=str(output / '02-两组菜单-展开.png'), full_page=True)
    check('子页面可进入，二级与所属一级菜单同步高亮')
    page.locator('#nav-toggle-content').click()
    expect(page.locator('#nav-group-content')).not_to_be_visible()
    page.locator('#filter-query').fill('市场')
    expect(page.locator('.results-bar')).to_contain_text('关键词：市场')
    expect(page.locator('#nav-toggle-content')).to_have_attribute('aria-expanded', 'false')
    expect(page.locator('#nav-toggle-content')).to_have_class('nav-btn nav-parent current')
    expect(page.locator('h1')).to_have_text('营销素材')
    check('手动收起当前栏目后，筛选重绘保留折叠和父级高亮')
    page.evaluate("AssetDemo.nav('contract')")
    expect(page.locator('#nav-toggle-content')).to_have_attribute('aria-expanded', 'true')
    expect(page.locator('#nav-item-contract')).to_have_attribute('aria-current', 'page')
    expect(page.locator('#nav-item-contract')).to_be_visible()
    check('通过统一导航进入子页面会自动展开对应一级菜单')
    page.set_viewport_size({'width': 900, 'height': 844})
    bounds = page.locator('.sidebar').bounding_box()
    controls = page.locator('#navigation button:visible').evaluate_all('nodes=>nodes.map(n=>{const r=n.getBoundingClientRect();return {left:r.left,right:r.right};})')
    check('900px图标侧栏中父子菜单均可见且未越出侧栏', all(r['left'] >= bounds['x'] and r['right'] <= bounds['x'] + bounds['width'] + 1 for r in controls))
    page.screenshot(path=str(output / '03-图标侧栏-展开.png'), full_page=True)
    page.set_viewport_size({'width': 390, 'height': 844})
    page.locator('#mobile-nav').select_option('call')
    expect(page.locator('h1')).to_have_text('外呼记录')
    page.set_viewport_size({'width': 1440, 'height': 1000})
    expect(page.locator('#nav-toggle-business')).to_have_attribute('aria-expanded', 'true')
    expect(page.locator('#nav-item-call')).to_have_attribute('aria-current', 'page')
    expect(page.locator('#navigation [aria-current="page"]')).to_have_count(1)
    check('移动切换子页面后，回到桌面仍展开正确栏目且只有一个当前页面')
    page.evaluate("AssetDemo.nav('all')")
    for group in ['content', 'business']:
        if page.locator(f'#nav-toggle-{group}').get_attribute('aria-expanded') == 'true':
            page.locator(f'#nav-toggle-{group}').click()


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

            def nav(page_id):
                target = page.locator(f'#navigation [data-action="nav"][data-id="{page_id}"]')
                if not target.is_visible():
                    group = page.locator('.nav-folder').filter(has=page.locator(f'[data-action="nav"][data-id="{page_id}"]'))
                    group.locator('[data-action="nav-group"]').click()
                target.click()

            def reset():
                page.locator('#search-reset').click()

            expect(page.locator('h1')).to_have_text('资产检索')
            expect(page.locator('#breadcrumb')).to_have_text('资产检索')
            expect(page.locator('#mobile-nav option[value="all"]')).to_have_text('资产检索')
            check('桌面、面包屑、移动入口名称一致')
            check('检索首页移除重复分类和全库统计', page.locator('#main .category-tabs, #main .stats').count() == 0)
            expect(page.locator('.results-bar')).to_contain_text(f'当前匹配 {page.evaluate("AssetDemo.getData().assets.length")} 条资产记录')
            expect(page.locator('#search-advanced')).not_to_be_visible()
            check('默认显示统一列表并收起更多筛选', page.locator('[data-asset-row]').count() == 10)
            page.screenshot(path=str(OUTPUT / '02-资产检索-桌面.png'), full_page=True)
            verify_sidebar(page, check)

            page.locator('#filter-query').fill('今日市场复盘')
            page.locator('#search-run').click()
            expect(page.locator('[data-asset-row]')).to_have_count(2)
            page.locator('#search-type').select_option('material')
            page.locator('#search-source').select_option('research')
            page.locator('#search-start').fill('2026-10-23')
            page.locator('#search-end').fill('2026-10-23')
            page.locator('#search-more').click()
            page.locator('#search-customer').focus()
            page.locator('#search-customer').select_option('c1')
            expect(page.locator('#search-customer')).to_be_focused()
            page.locator('#search-sales').select_option('e1')
            page.locator('#search-format').select_option('image')
            expect(page.locator('[data-asset-row]')).to_have_count(1)
            expect(page.locator('[data-asset-row="m1"]')).to_be_visible()
            expect(page.locator('.results-bar')).to_contain_text('当前匹配 1 条资产记录')
            check('关键词、类型、来源、日期、客户、销售与文件形式可组合，筛选后保留焦点')
            page.screenshot(path=str(OUTPUT / '03-组合检索-展开.png'), full_page=True)

            with page.expect_download() as download:
                page.locator('.head-actions [data-action="export"]').click()
            exported = json.loads(Path(download.value.path()).read_text(encoding='utf-8'))
            check('组合检索导出范围与结果一致', [r['id'] for r in exported['records']] == ['m1'])
            expect(page.locator('#toast')).to_be_hidden(timeout=6000)
            page.locator('#search-more').click()
            expect(page.locator('#search-more')).to_be_focused()
            expect(page.locator('#search-more')).to_have_attribute('aria-expanded', 'false')
            expect(page.locator('#search-advanced')).not_to_be_visible()
            expect(page.locator('.search-more-count')).to_have_text('3')
            expect(page.locator('#search-condition-customerId')).to_contain_text('李明')
            expect(page.locator('#search-condition-salesId')).to_contain_text('张晨')
            check('收起更多筛选后仍显示有效条件及数量，按钮焦点保留')
            page.screenshot(path=str(OUTPUT / '04-组合检索-收起.png'), full_page=True)
            page.locator('[data-asset-row="m1"] .title').click()
            expect(page.locator('#detail-title')).to_have_text('今日市场复盘 · 收盘海报')
            page.locator('#detail .drawer-tabs [data-id="relations"]').click()
            expect(page.locator('#detail tbody tr')).to_have_count(3)
            page.keyboard.press('Escape')
            expect(page.locator('[data-asset-row]')).to_have_count(1)
            expect(page.locator('#search-condition-customerId')).to_contain_text('李明')
            check('检索结果沿用同一资产与三次发送记录，关闭详情保留筛选')
            page.locator('#search-condition-customerId').click()
            expect(page.locator('#search-condition-customerId')).to_have_count(0)
            expect(page.locator('.search-more-count')).to_have_text('2')
            expect(page.locator('#filter-query')).to_be_focused()
            page.locator('#search-more').click()
            expect(page.locator('#search-customer')).to_have_value('all')
            expect(page.locator('#search-sales')).to_have_value('e1')
            check('隐藏筛选可逐项移除，重新展开时条件保持一致')

            reset()
            expect(page.locator('.search-condition')).to_have_count(0)
            expect(page.locator('#search-advanced')).not_to_be_visible()
            expect(page.locator('.results-bar')).to_contain_text(f'当前匹配 {page.evaluate("AssetDemo.getData().assets.length")} 条资产记录')
            check('重置清空所有组合条件和分页状态')
            page.locator('#search-start').fill('2026-10-24')
            page.locator('#search-end').fill('2026-10-20')
            expect(page.locator('.search-date-error')).to_be_visible()
            expect(page.locator('[data-asset-row]')).to_have_count(0)
            page.locator('#search-condition-start').click()
            expect(page.locator('.search-date-error')).to_have_count(0)
            expect(page.locator('[data-asset-row]')).not_to_have_count(0)
            check('无效日期范围显示提示，单项移除后恢复结果')
            reset()

            cdp = context.new_cdp_session(page)
            page.locator('#filter-query').focus()
            page.evaluate('window.__imeNode=document.querySelector("#filter-query")')
            cdp.send('Input.imeSetComposition', {'text': 'li', 'selectionStart': 2, 'selectionEnd': 2})
            page.wait_for_timeout(400)
            check('中文组合输入等待时输入节点保持稳定', page.evaluate('window.__imeNode===document.querySelector("#filter-query")'))
            cdp.send('Input.insertText', {'text': '李'})
            expect(page.locator('#filter-query')).to_have_value('李')
            page.wait_for_timeout(250)
            check('组合提交后不残留拼音且触发检索', page.locator('#filter-query').input_value() == '李' and page.locator('[data-asset-row]').count() > 0)
            cdp.detach()
            reset()
            page.locator('#filter-query').fill('不存在<脚本>"&')
            page.locator('#filter-query').press('Enter')
            expect(page.get_by_role('heading', name='暂无匹配记录')).to_be_visible()
            expect(page.locator('#search-condition-query')).to_contain_text('不存在<脚本>"&')
            check('特殊字符安全展示，空结果可清除条件')
            page.locator('.empty [data-action="reset-filters"]').click()

            page.locator('#search-more').click()
            page.locator('#search-customer').select_option('c6')
            page.locator('#search-sales').select_option('e1')
            page.locator('#search-format').select_option('pdf')
            nav('material')
            expect(page.locator('.stat')).to_have_count(4)
            expect(page.locator('[data-action="category"][data-id="image"]')).to_be_visible()
            expect(page.locator('.results-bar')).to_contain_text('8')
            check('检索条件不泄漏到营销素材，其专有统计与分类保持可用')
            page.locator('#global-query').fill('今日市场复盘')
            page.locator('#global-query').dispatch_event('keydown', {'key': 'Enter', 'isComposing': True})
            expect(page.locator('h1')).to_have_text('营销素材')
            check('全局搜索不在中文组合确认时提前跳页')
            page.locator('#global-query').press('Enter')
            expect(page.locator('h1')).to_have_text('资产检索')
            expect(page.locator('#filter-query')).to_have_value('今日市场复盘')
            expect(page.locator('[data-asset-row]')).to_have_count(2)
            check('全局搜索进入统一检索并清除旧的隐藏条件')
            reset()

            for width, height in [(1440, 1000), (1280, 720), (900, 844), (390, 844), (320, 800)]:
                page.set_viewport_size({'width': width, 'height': height})
                page.evaluate('window.scrollTo(0,0)')
                expect(page.locator('#search-run')).to_be_in_viewport(ratio=1)
                expect(page.locator('#search-type')).to_be_in_viewport(ratio=1)
                check(f'{width}px 检索首屏可操作且无整页横向溢出', page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'))
                layout = page.locator('.results-bar').bounding_box()
                report['layouts'].append({'width': width, 'height': height, 'resultsTop': layout['y']})
                if width == 1280:
                    check('1280×720首屏可看到实际资产行', page.locator('[data-asset-row]').first.bounding_box()['y'] < 620)
                    page.screenshot(path=str(OUTPUT / '05-资产检索-笔记本.png'))
                if width == 390:
                    page.screenshot(path=str(OUTPUT / '06-资产检索-窄屏.png'), full_page=True)
                page.locator('#search-more').click()
                expect(page.locator('#search-customer')).to_be_visible()
                check(f'{width}px 展开更多筛选无整页横向溢出', page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'))
                if width == 390:
                    page.screenshot(path=str(OUTPUT / '07-资产检索-窄屏展开.png'), full_page=True)
                page.locator('#search-more').click()

            report['sha256'] = hashlib.sha256((ROOT / HTML).read_bytes()).hexdigest()
            check('浏览器没有未捕获错误、控制台错误或失败资源请求', not any(report[k] for k in ['pageErrors', 'consoleErrors', 'requestFailures']))
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
        print(f'检索验证报告：{OUTPUT / "verification.json"}', flush=True)


if __name__ == '__main__':
    main()
