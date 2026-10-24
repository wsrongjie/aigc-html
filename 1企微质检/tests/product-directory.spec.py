"""独立浏览器检查商品配置、订单快照与来源关系，不连接客户系统。"""
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
OUTPUT = ROOT / 'outputs/asset-center/products'
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
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(viewport={'width': 1440, 'height': 1000}, reduced_motion='reduce', accept_downloads=True)
            page = context.new_page()
            page.on('pageerror', lambda e: report['pageErrors'].append(str(e)))
            page.on('console', lambda m: report['consoleErrors'].append(m.text) if m.type == 'error' else None)
            page.on('requestfailed', lambda r: report['requestFailures'].append({'url': r.url, 'failure': r.failure}))
            page.goto(f'http://127.0.0.1:{server.server_port}/{HTML}')
            page.wait_for_function('window.assetDemoReady === true')

            def rows():
                return page.locator('[data-product-row]').evaluate_all('rs=>rs.map(r=>r.dataset.productRow)')

            def submit(text=None):
                if text is not None:
                    page.locator('#product-query').fill(text)
                page.locator('#product-submit').click()

            def reset():
                page.locator('[data-action="product-reset"]').first.click()

            def tab(name):
                page.locator(f'#detail .drawer-tabs [data-id="{name}"]').click()

            def open_product(pid):
                page.locator(f'[data-product-row="{pid}"] .title').click()

            def download(selector):
                with page.expect_download() as info:
                    page.locator(selector).click()
                return json.loads(Path(info.value.path()).read_text(encoding='utf-8'))

            page.locator('#nav-toggle-business').click()
            page.locator('#nav-item-product').click()
            expect(page.locator('h1')).to_have_text('商品档案')
            expect(page.locator('#nav-item-product')).to_have_attribute('aria-current', 'page')
            expect(page.locator('#main .stats, #main .asset-cards')).to_have_count(0)
            check('商品档案纳入业务记录，使用独立紧凑目录', set(rows()) == {'p1', 'p2', 'p3', 'p4'})
            check('商品字段缺失显示未提供，真实零值不变成缺失', '未提供' in page.locator('[data-product-row="p4"]').inner_text() and '¥0.00' not in page.locator('[data-product-row="p4"]').inner_text())
            page.screenshot(path=str(OUTPUT / '01-商品目录-桌面.png'), full_page=True)

            page.locator('#product-query').fill('基础投研服务')
            expect(page.locator('#product-dirty')).to_be_visible()
            check('未提交商品条件不会改变列表及导出', len(rows()) == 4 and len(download('.head-actions [data-action="export"]')['records']) == 4)
            submit()
            check('同名不同编号分别展示，查询后生效', set(rows()) == {'p1', 'p3'})
            expect(page.locator('#product-dirty')).to_be_hidden()
            payload = download('.head-actions [data-action="export"]')
            check('商品索引导出包含已提交条件和全部匹配商品', {p['id'] for p in payload['records']} == {'p1', 'p3'} and payload['productQuery']['text'] == '基础投研服务')
            submit('GOODS-001')
            check('支持来源商品编号定位', rows() == ['p1'])
            page.locator('#product-query').fill('GOODS-002')
            page.locator('#product-query').press('Enter')
            check('商品查询支持键盘回车', rows() == ['p2'])
            reset()
            page.locator('#product-category').select_option('投研服务')
            page.locator('#product-level').select_option('基础')
            page.locator('#product-status').select_option('在售')
            page.locator('#product-source').select_option('oms')
            check('组合条件提交前结果保持不变', len(rows()) == 4)
            submit()
            check('分类等级来源状态组合查询一致', rows() == ['p1'])
            page.locator('#product-status').select_option('已下架')
            submit()
            expect(page.locator('.product-directory')).to_contain_text('暂无匹配商品')
            check('矛盾组合显示真实空态', rows() == [])
            page.locator('#product-empty-reset').focus()
            page.keyboard.press('Enter')
            expect(page.locator('#product-query')).to_be_focused()
            check('空结果键盘清除后回到商品搜索框')
            reset()
            page.locator('#product-reset').focus()
            page.keyboard.press('Enter')
            expect(page.locator('#product-reset')).to_be_focused()
            check('键盘重置后保留焦点，结果恢复')
            check('重置恢复全部商品及全部条件', len(rows()) == 4 and page.locator('#product-query').input_value() == '' and page.locator('#product-category').input_value() == 'all')

            open_product('p1')
            expect(page.locator('#detail-title')).to_have_text('基础投研服务')
            expect(page.locator('.product-price strong')).to_have_text('¥3,280.00')
            check('商品详情显示当前价格配置并明确区别订单成交', '订单成交金额' in page.locator('.product-price').inner_text())
            page.screenshot(path=str(OUTPUT / '02-商品档案-当前配置.png'))
            tab('orders')
            check('基础商品仅关联三笔明确订单', set(page.locator('[data-product-order]').evaluate_all('rs=>rs.map(r=>r.dataset.productOrder)')) == {'o1', 'o3', 'o5'})
            check('订单列表保留2980成交金额而非3280当前价格', page.locator('.product-order-table').inner_text().count('¥2,980.00') == 3 and '¥3,280.00' not in page.locator('.product-order-table').inner_text())
            page.screenshot(path=str(OUTPUT / '03-商品关联订单.png'))
            page.locator('[data-product-order="o1"] [data-action="open-asset"]').click()
            expect(page.locator('#detail-title')).to_contain_text('李明')
            expect(page.locator('#detail [data-product-reference="p1"]')).to_be_visible()
            check('订单详情保留成交快照并提供商品回跳', '订单实付金额' in page.locator('#detail .drawer-body').inner_text() and '¥2,980.00' in page.locator('#detail .drawer-body').inner_text())
            tab('products')
            page.locator('#detail [data-product-reference="p1"] [data-action="open-asset"]').click()
            expect(page.locator('.product-price strong')).to_have_text('¥3,280.00')
            page.locator('#detail [data-action="drawer-back"]').click()
            check('商品与订单往返保留上一详情标签', page.evaluate('AssetDemo.getState().drawer.tab') == 'products' and page.evaluate('AssetDemo.getState().drawer.id') == 'o1')
            page.locator('#detail [data-action="drawer-back"]').click()
            expect(page.locator('[data-product-order]')).to_have_count(3)

            tab('people')
            cids = page.locator('#detail [data-action="open-customer"]').evaluate_all('bs=>bs.map(b=>b.dataset.id)')
            eids = page.locator('#detail [data-action="open-sales"]').evaluate_all('bs=>bs.map(b=>b.dataset.id)')
            check('购买客户和成交销售分别按已支付订单去重', set(cids) == {'c1', 'c3', 'c5'} and set(eids) == {'e1', 'e2', 'e3'})
            tab('business')
            bids = page.locator('#detail [data-action="open-asset"]').evaluate_all('bs=>bs.map(b=>b.dataset.id)')
            check('合同退款和事项按明确订单链关联，不纳入同客户其他记录', set(bids) == {'ct1', 'ct2', 'ct4', 'ct6', 'rf1', 'cs1', 'ca2'} and 'cs3' not in bids)
            page.locator('#detail .record-main [data-id="rf1"]').click()
            tab('products')
            check('退款通过明确订单关系回到商品', page.locator('#detail [data-product-reference="p1"]').count() == 1)
            page.locator('#detail [data-action="drawer-back"]').click()
            tab('content')
            content = page.locator('#detail .record-main [data-action="open-asset"]').evaluate_all('bs=>bs.map(b=>b.dataset.id)')
            check('内容仅按独立来源映射关联，不因发送同客户自动关联', set(content) == {'m4', 'r1'} and 'm1' not in content)
            page.locator('#detail .record-main [data-id="m4"]').click()
            tab('products')
            check('素材可以查看商品关联依据并回跳', 'REL-m4-p1' in page.locator('#detail .drawer-body').inner_text())
            page.locator('#detail [data-action="drawer-back"]').click()
            tab('source')
            check('历史配置留存调价前后快照，不伪造审批结果', '¥2,980.00' in page.locator('#detail .drawer-body').inner_text() and '¥3,280.00' in page.locator('#detail .drawer-body').inner_text() and '来源未提供审核记录' in page.locator('#detail .drawer-body').inner_text())
            page.screenshot(path=str(OUTPUT / '04-商品历史配置.png'))
            product_export = download('#detail [data-action="download-product"]')
            check('完整商品导出保留价格历史、订单快照及关联依据', product_export['currentFields']['销售价格'] == 3280 and len(product_export['history']) == 2 and all(o['snapshot']['paidAmount'] == '¥2,980.00' for o in product_export['orders']) and len(product_export['relatedRecords']) == 12)
            page.keyboard.press('Escape')

            # 仅修改浏览器内存；验证当前商品改名调价不会回写订单快照。
            page.evaluate("()=>{const p=AssetDemo.getData().assets.find(a=>a.id==='p1');window.__productTitle=p.title;window.__productPrice=p.fields.销售价格;p.title='改名后的商品';p.fields.销售价格=9999;}")
            open_product('p1')
            tab('orders')
            check('商品改名调价不覆盖既有订单的名称价格与服务期间', '改名后的商品' not in page.locator('.product-order-table').inner_text() and '¥9,999.00' not in page.locator('.product-order-table').inner_text() and '2026-09-12 至 2026-12-11' in page.locator('.product-order-table').inner_text())
            page.keyboard.press('Escape')
            page.evaluate("()=>{const p=AssetDemo.getData().assets.find(a=>a.id==='p1');p.title=window.__productTitle;p.fields.销售价格=window.__productPrice;}")
            open_product('p3')
            expect(page.locator('#detail .drawer-body')).to_contain_text('¥0.00')
            tab('orders')
            check('同名历史商品不自动接收其他编号的订单', page.locator('[data-product-order]').count() == 0)
            page.keyboard.press('Escape')
            open_product('p4')
            expect(page.locator('.product-price strong')).to_have_text('未提供')
            tab('source')
            check('缺失价格和历史如实展示未提供', '来源尚未提供历史配置' in page.locator('#detail .drawer-body').inner_text())
            missing = download('#detail [data-action="download-product"]')
            check('商品导出保留null和空历史，不转成零或审批通过', missing['currentFields']['销售价格'] is None and missing['history'] == [] and missing['orders'] == [])
            page.keyboard.press('Escape')

            page.evaluate("AssetDemo.openDetail('customer','c1',{tab:'business'})")
            expect(page.locator('#customer-profile-content [data-product-reference="p1"]')).to_be_visible()
            check('客户订单与服务中可进入订单关联商品')
            page.locator('#customer-profile-back').click()
            page.evaluate("AssetDemo.openDetail('asset','l1')")
            tab('products')
            check('直播独立商品关系可查看，不借用观众的购买关系', page.locator('#detail [data-product-reference="p2"]').count() == 1 and page.locator('#detail [data-product-reference="p1"]').count() == 0)
            page.keyboard.press('Escape')
            page.evaluate("AssetDemo.nav('all')")
            page.locator('#search-type').select_option('product')
            check('统一资产检索包含商品类型', page.locator('[data-asset-row]').count() == 4)
            page.locator('#filter-query').fill('GOODS-003')
            page.locator('#search-run').click()
            check('统一检索按商品原始编号定位独立商品', page.locator('[data-asset-row]').get_attribute('data-asset-row') == 'p3')
            all_export = download('.head-actions [data-action="export"]')
            check('统一检索导出保留商品结构化字段', all_export['records'][0]['product']['currentFields']['促销立减'] == 0)
            page.evaluate("AssetDemo.nav('dates')")
            page.locator('#main [data-action="category"][data-id="product"]').click()
            check('日期归档可以按商品配置类型查看', page.locator('#main .timeline-item').count() > 0)
            page.locator('#main [data-action="date"][data-id="2026-09-01"]').click()
            expect(page.locator('#main .timeline')).to_contain_text('¥2,980.00')
            page.locator('#main .timeline [data-action="open-asset"]').click()
            check('历史商品配置按当时日期归档，打开来源历史而非当前价格', page.evaluate('AssetDemo.getState().drawer.tab') == 'source')
            page.keyboard.press('Escape')

            # 临时补充33份目录，仅验证分页和导出边界，不写入磁盘。
            page.evaluate("()=>{const a=AssetDemo.getData().assets,base=a.find(x=>x.id==='p4');for(let i=0;i<33;i++)a.push({...base,id:'probe-p'+i,sourceId:'PROBE-GOODS-'+i,title:'分页商品'+i});AssetDemo.nav('product');}")
            expect(page.locator('[data-product-row]')).to_have_count(25)
            first = rows()
            page.locator('#product-next').click()
            expect(page.locator('[data-product-row]')).to_have_count(12)
            second = rows()
            expect(page.locator('#product-next')).to_be_disabled()
            expect(page.locator('#product-page-size')).to_be_focused()
            check('商品分页25/12项无重复遗漏，末页边界与焦点正确', len(set(first + second)) == 37)
            check('商品目录导出全部匹配项而非仅当前页', len(download('.head-actions [data-action="export"]')['records']) == 37)
            page.locator('#product-page-size').select_option('50')
            expect(page.locator('[data-product-row]')).to_have_count(37)
            page.locator('#product-page-size').select_option('100')
            expect(page.locator('[data-product-row]')).to_have_count(37)
            check('商品每页25/50/100项切换有效')
            page.evaluate("()=>{const a=AssetDemo.getData().assets;for(let i=a.length-1;i>=0;i--)if(a[i].id.startsWith('probe-p'))a.splice(i,1);AssetDemo.nav('product');}")
            for width, height in [(1440, 1000), (1280, 720), (900, 844), (390, 844), (320, 800)]:
                page.set_viewport_size({'width': width, 'height': height})
                check(f'{width}px 商品目录无整页横向溢出', page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'))
                if width == 1280:
                    page.screenshot(path=str(OUTPUT / '05-商品目录-笔记本.png'), full_page=True)
                if width == 390:
                    page.screenshot(path=str(OUTPUT / '06-商品目录-窄屏.png'), full_page=True)
                open_product('p1')
                expect(page.locator('#detail [data-action="drawer-close"]')).to_be_in_viewport(ratio=1)
                check(f'{width}px 商品配置和关闭按钮保持在抽屉内', page.locator('#detail .drawer-body').evaluate('e=>e.scrollWidth<=e.clientWidth+1'))
                if width == 390:
                    page.screenshot(path=str(OUTPUT / '07-商品详情-窄屏.png'))
                tab('orders')
                check(f'{width}px 订单长表仅在表格容器滚动', page.locator('#detail .drawer-body').evaluate('e=>e.scrollWidth<=e.clientWidth+1'))
                report['layouts'].append({'width': width, 'height': height, 'passed': True})
                page.keyboard.press('Escape')
            check('商品相关操作没有浏览器脚本、控制台及资源请求错误', not any(report[k] for k in ['pageErrors', 'consoleErrors', 'requestFailures']))
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
        print(f'商品验证报告：{OUTPUT / "verification.json"}', flush=True)


if __name__ == '__main__':
    main()
