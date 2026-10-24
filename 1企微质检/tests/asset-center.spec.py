"""在独立浏览器上下文验证原型，不连接客户系统，不修改备份。"""
from __future__ import annotations

import base64
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
OUTPUT = ROOT / "outputs" / "asset-center"
HTML = "企业数据资产中心-交互原型.html"
BACKUP_HASHES = {
    "见微合规工作台-全量资产版.html": "69573B338B543115C7D7E2BFB9A21C55C0E96478BB7ABB2C1055C270C3C04F4E",
    "见微合规工作台-组织权限版.html": "F9538D09674C5FBAE80B2E9BE2479D55DB92C59AF1C6F38E46F364FD1431AB85",
}


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


def demo_pdf():
    """生成最小有效 PDF，仅用于原件打开与下载回归。"""
    stream = b"BT /F1 18 Tf 50 740 Td (Asset center PDF original) Tj ET"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    data = b"%PDF-1.4\n"
    offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data += str(index).encode() + b" 0 obj\n" + obj + b"\nendobj\n"
    xref = len(data)
    data += b"xref\n0 6\n0000000000 65535 f \n"
    data += b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:])
    return data + f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()


def verify_daily_chat(context, url, check, report):
    """使用独立页面验证日期目录，临时多账号样本不写入文件或本地存储。"""
    page = context.new_page()
    page.on("pageerror", lambda err: report["pageErrors"].append(str(err)))
    page.on("console", lambda msg: report["consoleErrors"].append(msg.text) if msg.type == "error" else None)
    page.on("requestfailed", lambda request: report["requestFailures"].append({"url": request.url, "failure": request.failure}))
    page.goto(url)
    page.wait_for_function("window.assetDemoReady === true")
    page.locator('#navigation [data-id="dates"]').click()
    page.locator('[data-action="category"][data-id="conversation"]').click()
    page.locator('[data-action="date"][data-id="2026-10-23"]').click()

    def primary(person_id):
        page.locator(f'[data-action="archive-primary"][data-id="{person_id}"]').click()

    def peer(pair):
        page.locator(f'[data-action="archive-peer"][data-id="{pair}"]').click()

    def axis(value):
        page.locator(f'[data-action="archive-axis"][data-id="{value}"]').click()

    def message_ids():
        return page.locator('#archive-chat-detail .message').evaluate_all("rows=>rows.map(e=>e.dataset.messageId)")

    def export():
        with page.expect_download() as info:
            page.locator('.head-actions [data-action="export"]').click()
        return json.loads(Path(info.value.path()).read_text(encoding="utf-8"))

    expect(page.locator('.archive-primary')).to_have_count(3)
    expect(page.locator('.archive-peer:visible')).to_have_count(0)
    expect(page.locator('.archive-chat-placeholder')).to_contain_text('展开销售目录')
    check('日期聊天默认提供销售目录，逐级展开前不混入具体对话')
    check('日期聊天统计按当天双向消息和去重人员账号计算', page.locator('.stat-value').all_text_contents() == ['14条', '3位', '4位', '4个'])
    primary('e1')
    expect(page.locator('[data-primary-id="e1"] .archive-peer:visible')).to_have_count(2)
    peer('e1|c1')
    check('销售维度展开客户后仅显示当天四条双向消息', message_ids() == ['msg05', 'msg06', 'msg07', 'msg08'])
    expect(page.locator('#archive-chat-detail [data-message-id="msg01"]')).to_have_count(0)
    page.evaluate('window.scrollTo(0,0)')
    page.screenshot(path=str(OUTPUT / '08-日期聊天-销售维度.png'), full_page=True)
    page.locator('#archive-chat-detail [data-message-id="msg07"] [data-action="open-asset"]').click()
    expect(page.locator('#version-select')).to_have_value('m1-v2')
    page.keyboard.press('Escape')
    check('当天聊天中的素材仍打开实际发送版本，关闭后保留目录选择', message_ids() == ['msg05', 'msg06', 'msg07', 'msg08'])

    page.locator('#archive-chat-detail .chat-header [data-action="open-asset"]').click()
    expect(page.locator('#detail')).to_be_visible()
    page.locator('#detail .drawer-tabs [data-id="preview"]').click()
    expect(page.locator('#detail .message')).to_have_count(4)
    expect(page.locator('#detail #message-msg03')).to_have_count(0)
    check('日期主视图与来源抽屉同时展示时不存在重复消息DOM标识', page.evaluate("()=>{const ids=[...document.querySelectorAll('[id]')].map(n=>n.id);return ids.length===new Set(ids).size;}"))
    page.locator('#detail .drawer-tabs [data-id="relations"]').click()
    expect(page.locator('#detail .record-row')).to_have_count(2)
    expect(page.locator('#detail [data-action="open-asset"][data-id="m2"]')).to_have_count(0)
    check('来源抽屉及其关联内容继续限定当前查阅日期')
    page.locator('#detail [data-action="locate-message"][data-id="msg05"]').click()
    expect(page.locator('#detail #message-msg05')).to_have_class(__import__('re').compile('located'))
    expect(page.locator('#detail .message')).to_have_count(4)
    expect(page.locator('#detail #message-msg01')).to_have_count(0)
    check('从来源关联内容定位消息仍保留当天范围并定位在前景抽屉')
    page.keyboard.press('Escape')

    axis('customers')
    expect(page.locator('.archive-primary')).to_have_count(4)
    expect(page.locator('#archive-chat-detail .message')).to_have_count(0)
    expect(page.locator('[data-action="archive-primary"][data-id="c6"]')).to_have_count(0)
    primary('c1')
    expect(page.locator('[data-primary-id="c1"] .archive-peer:visible')).to_have_count(2)
    peer('e2|c1')
    check('客户维度列出当天两位对接销售并显示所选销售的消息', message_ids() == ['msg28', 'msg29'])
    page.evaluate('window.scrollTo(0,0)')
    page.screenshot(path=str(OUTPUT / '09-日期聊天-客户维度.png'), full_page=True)
    downloaded = export()
    check('日期聊天导出遵循当前客户销售对话及查阅日期', [m['id'] for m in downloaded['records']] == ['msg28', 'msg29'] and downloaded['archiveContext'] == {'date': '2026-10-23', 'axis': 'customers', 'primaryId': 'c1', 'pairKey': 'e2|c1'})
    primary('c1')
    expect(page.locator('#archive-chat-detail .message')).to_have_count(0)
    primary('c1')
    downloaded = export()
    check('展开客户未选下级时导出该客户当天所有对接消息', {m['id'] for m in downloaded['records']} == {'msg05', 'msg06', 'msg07', 'msg08', 'msg28', 'msg29'})

    page.locator('[data-action="date"][data-id="2026-10-22"]').click()
    expect(page.locator('#archive-chat-detail .message')).to_have_count(0)
    primary('c1')
    expect(page.locator('[data-primary-id="c1"] .archive-peer:visible')).to_have_count(1)
    peer('e1|c1')
    check('切换日期清空旧选择并只显示该日消息', message_ids() == ['msg03', 'msg04'])
    primary('c3')
    peer('e2|c3')
    check('只有销售发送消息的单向对话也计入当天目录', message_ids() == ['msg15'])
    page.locator('[data-action="date"][data-id="2026-10-19"]').click()
    expect(page.locator('.archive-primary')).to_have_count(1)
    primary('c6')
    peer('e3|c6')
    check('无当天往来人员不显示，历史日期保留其实际对话', message_ids() == ['msg26', 'msg27'])

    axis('sales')
    page.locator('[data-filter="start"]').fill('2026-10-23')
    page.locator('[data-filter="end"]').fill('2026-10-23')
    page.locator('#filter-query').fill('李明')
    expect(page.locator('.archive-primary')).to_have_count(2)
    primary('e1')
    peer('e1|c1')
    check('日期与人员筛选共同约束目录和完整当日对话', message_ids() == ['msg05', 'msg06', 'msg07', 'msg08'])
    page.locator('#filter-query').fill('资料来源那一节')
    expect(page.locator('.archive-primary')).to_have_count(1)
    expect(page.locator('#archive-chat-detail .message')).to_have_count(4)
    check('消息关键词匹配对话后仍保留当天完整上下文')
    page.locator('#filter-query').fill('WX-EM-108')
    expect(page.locator('[data-primary-id="e1"] .archive-peer:visible')).to_have_count(1)
    expect(page.locator('#archive-chat-detail .message')).to_have_count(0)
    peer('e1|c2')
    check('账号标识筛选后失效对话被清除且可查看正确客户', message_ids() == ['msg11', 'msg12'])
    page.locator('[data-filter="source"]').select_option('oms')
    expect(page.get_by_role('heading', name='暂无匹配的聊天记录')).to_be_visible()
    expect(page.locator('.archive-primary')).to_have_count(0)
    expect(page.locator('#archive-chat-detail .message')).to_have_count(0)
    check('无聊天来源的筛选展示空态而不残留旧消息')
    page.locator('[data-action="reset-filters"]').first.click()
    expect(page.locator('.category-tabs [data-id="conversation"]')).to_have_class('active')
    expect(page.locator('.archive-primary')).to_have_count(3)
    check('重置筛选后继续保持聊天目录视图')

    # 展示截图使用原始演示数据，多账号边界样本随后只在内存中添加。
    axis('customers')
    primary('c1')
    peer('e1|c1')
    page.set_viewport_size({'width': 390, 'height': 900})
    page.emulate_media(reduced_motion='reduce')
    peer('e1|c1')
    expect(page.locator('#archive-chat-detail .chat-header')).to_be_in_viewport()
    expect(page.locator('#toast')).not_to_be_visible(timeout=5000)
    page.screenshot(path=str(OUTPUT / '10-日期聊天-窄屏.png'), full_page=True)
    page.set_viewport_size({'width': 1440, 'height': 1000})

    # 同销售、同客户、第二个已映射企微账号，仅客户当天发言。
    page.evaluate("""() => {
        const d=AssetDemo.getData();
        d.conversations.push({id:'cv-daily-probe',customerId:'c1',employeeId:'e1',account:'企微·晨晨',accountId:'WX-EM-108'});
        d.messages.push({id:'msg-daily-probe',conversationId:'cv-daily-probe',sender:'customer',time:'2026-10-23 10:40',text:'这是另一个已映射账号上的当天补充消息。'});
        d.assets.push({id:'cv-daily-probe',type:'conversation',format:'text',title:'李明 × 张晨 · 第二账号会话',source:'wecom',sourceId:'DAILY-PROBE',time:'2026-10-23 10:40',customers:['c1'],employees:['e1'],status:'已归档'});
    }""")
    axis('sales')
    primary('e1')
    expect(page.locator('[data-primary-id="e1"] .archive-peer:visible')).to_have_count(2)
    peer('e1|c1')
    expect(page.locator('#archive-chat-detail .chat-header')).to_contain_text('2 个企微账号')
    check('同销售同客户多个企微账号合并为一个目录项', message_ids() == ['msg05', 'msg06', 'msg-daily-probe', 'msg07', 'msg08'])
    expect(page.locator('#archive-chat-detail [data-message-id="msg-daily-probe"] .chat-account-tag')).to_have_text('企微·晨晨')
    downloaded = export()
    check('合并对话按时间排序，导出逐条保留实际账号来源', len(downloaded['records']) == 5 and {m['accountId'] for m in downloaded['records']} == {'WX-EM-101', 'WX-EM-108'})
    page.locator('.account-sources summary').click()
    page.locator('.account-source-list [data-id="cv-daily-probe"]').click()
    page.locator('#detail .drawer-tabs [data-id="preview"]').click()
    expect(page.locator('#detail .message')).to_have_count(1)
    expect(page.locator('#detail .message.outgoing')).to_have_count(0)
    check('仅客户主动发送消息的账号也可归档与查阅来源')
    page.keyboard.press('Escape')
    axis('customers')
    primary('c1')
    expect(page.locator('[data-primary-id="c1"] .archive-peer:visible')).to_have_count(2)
    peer('e1|c1')
    check('反向客户目录同样合并销售账号，消息结果保持一致', message_ids() == ['msg05', 'msg06', 'msg-daily-probe', 'msg07', 'msg08'])

    for width in (900, 390):
        page.set_viewport_size({'width': width, 'height': 900})
        check(f'{width}px 日期聊天目录无页面横向溢出', page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'))
    page.emulate_media(reduced_motion='reduce')
    peer('e1|c1')
    expect(page.locator('#archive-chat-detail .chat-header')).to_be_in_viewport()
    check('窄屏展开选择后人员目录保留滚动位置且选中项完整可见', page.evaluate("()=>{const row=document.querySelector('.archive-peer.active').getBoundingClientRect(),box=document.querySelector('.archive-directory-scroll').getBoundingClientRect();return row.top>=box.top-1&&row.bottom<=box.bottom+1;}"))
    page.close()


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(Path.home() / "AppData/Local/ms-playwright"))
    OUTPUT.mkdir(parents=True, exist_ok=True)
    report = {"checks": [], "consoleErrors": [], "pageErrors": [], "requestFailures": []}

    def check(name, condition=True):
        assert condition, name
        report["checks"].append(name)
        print("通过：" + name, flush=True)

    server = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(QuietHandler, directory=str(ROOT)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}/{HTML}"
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
            page = context.new_page()
            page.on("pageerror", lambda err: report["pageErrors"].append(str(err)))
            page.on("console", lambda msg: report["consoleErrors"].append(msg.text) if msg.type == "error" else None)
            page.on("requestfailed", lambda request: report["requestFailures"].append({"url": request.url, "failure": request.failure}))
            page.goto(url)
            page.wait_for_function("window.assetDemoReady === true")
            expect(page.locator("h1")).to_have_text("资产检索")
            check("独立原型启动并提供演示标识", page.locator(".demo").inner_text() == "交互原型 · 演示数据")

            integrity = page.evaluate("""() => {
                const d=AssetDemo.getData(), ids=d.assets.map(x=>x.id);
                return {
                    count:ids.length, unique:ids.length===new Set(ids).size,
                    sources:d.assets.every(a=>d.sources.some(s=>s.id===a.source)),
                    refs:d.messages.every(m=>d.conversations.some(c=>c.id===m.conversationId)&&(!m.assetId||d.assets.some(a=>a.id===m.assetId&&(!m.versionId||a.versions.some(v=>v.id===m.versionId))))),
                    reviews:d.reviews.every(r=>d.assets.some(a=>a.id===r.assetId&&a.versions.some(v=>v.id===r.versionId))),
                    coreUses:AssetDemo.usages('m1').length,
                    coreCustomers:AssetDemo.links(d.assets.find(a=>a.id==='m1')).customers.length,
                    coreSales:new Set(AssetDemo.usages('m1').map(u=>u.employeeId)).size,
                    draftUsed:d.messages.some(m=>m.versionId==='m3-v2'),
                    chronology:d.messages.filter(m=>m.versionId).every(m=>d.assets.find(a=>a.id===m.assetId).versions.find(v=>v.id===m.versionId).date<=m.time),
                    refundHistory:AssetDemo.allEvents().some(e=>e.id==='history-rf1-0'&&e.time==='2026-10-22 10:30')
                };
            }""")
            check("稳定标识、来源与版本引用完整", all(integrity[k] for k in ("unique", "sources", "refs", "reviews")))
            check("同一海报对应三次发送、三位客户、两名销售", integrity["coreUses"] == 3 and integrity["coreCustomers"] == 3 and integrity["coreSales"] == 2)
            check("待审核的新文案版本没有历史发送记录", not integrity["draftUsed"])
            check("所有发送版本在发送前已存在", integrity["chronology"])
            check("退款申请历史按原始发生时间保留", integrity["refundHistory"])
            report["seedAssetCount"] = integrity["count"]
            page.screenshot(path=str(OUTPUT / "01-资产检索.png"), full_page=True)

            page.locator('[data-action="layout"][data-id="cards"]').click()
            expect(page.locator(".asset-card")).to_have_count(9)
            page.locator('[data-action="layout"][data-id="list"]').click()
            first = page.locator("tbody tr").first.get_attribute("data-asset-row")
            page.get_by_role("button", name="第2页", exact=True).click()
            check("列表、卡片与分页实际切换", page.locator("tbody tr").first.get_attribute("data-asset-row") != first)
            page.locator('[data-filter="source"]').select_option("oms")
            check("来源筛选仅保留订单系统", page.evaluate("AssetDemo.getState().source") == "oms" and "企微存档" not in page.locator("tbody").inner_text())
            page.locator('[data-filter="start"]').fill("2026-10-23")
            page.locator('[data-filter="end"]').fill("2026-10-23")
            check("日期范围筛选结果正确", all("10-23" in text for text in page.locator("tbody tr td:nth-child(5)").all_text_contents()))
            page.locator('[data-action="reset-filters"]').click()
            page.locator("#filter-query").fill('不存在<脚本>"&')
            expect(page.get_by_role("heading", name="暂无匹配记录")).to_be_visible()
            check("特殊字符搜索安全显示空态")
            page.locator('[data-action="reset-filters"]').first.click()

            def nav(name):
                if page.locator("#detail").is_visible():
                    page.keyboard.press("Escape")
                target = page.locator(f'#navigation [data-action="nav"][data-id="{name}"]')
                if not target.is_visible():
                    group = page.locator('.nav-folder').filter(has=page.locator(f'[data-action="nav"][data-id="{name}"]'))
                    group.locator('[data-action="nav-group"]').click()
                target.click()

            def open_asset(asset_id):
                page.locator(f'#main [data-asset-row="{asset_id}"] .title').click()

            def detail_tab(tab):
                page.locator(f'#detail .drawer-tabs [data-id="{tab}"]').click()

            nav("material")
            expect(page.locator(".results-bar")).to_contain_text("8")
            page.locator('[data-action="category"][data-id="image"]').click()
            expect(page.locator("tbody tr")).to_have_count(4)
            page.locator('[data-action="category"][data-id="all"]').click()
            open_asset("m1")
            expect(page.locator("#version-select")).to_have_value("m1-v2")
            check("海报原件可预览", page.locator(".preview-box img").evaluate("img=>img.complete && img.naturalWidth>0"))
            detail_tab("relations")
            expect(page.locator("#detail tbody tr")).to_have_count(3)
            page.locator('#detail [data-action="locate-message"][data-id="msg07"]').click()
            expect(page.locator("#message-msg07")).to_have_class(__import__("re").compile("located"))
            expect(page.locator("#message-msg06")).to_be_attached()
            check("素材使用记录定位原消息并保留上下文")
            page.screenshot(path=str(OUTPUT / "03-原始消息定位.png"))
            page.locator('#message-msg07 [data-action="open-asset"]').click()
            expect(page.locator("#version-select")).to_have_value("m1-v2")
            page.locator('#detail [data-action="drawer-back"]').click()
            expect(page.locator("#message-msg07")).to_have_class(__import__("re").compile("located"))
            check("抽屉跨对象回退保留消息定位状态")
            page.locator('#detail [data-action="drawer-back"]').click()
            expect(page.locator("#detail-title")).to_have_text("今日市场复盘 · 收盘海报")
            detail_tab("reviews")
            expect(page.locator("#detail .review-body")).to_have_count(1)
            expect(page.locator("#detail .review-body")).to_contain_text("REVIEW-MSG-0238")
            page.screenshot(path=str(OUTPUT / "02-素材审核追溯.png"))
            page.locator("#version-select").select_option("m1-v1")
            expect(page.locator("#detail .review-body")).to_contain_text("请补充资料日期")
            detail_tab("extraction")
            expect(page.locator("#detail .extract-box").first).to_contain_text("待补充日期与资料来源")
            expect(page.locator("#detail .extract-box").nth(1)).to_contain_text("初稿")
            check("历史版本的原件、提取结果及审核意见保持对应")

            nav("material")
            open_asset("m3")
            expect(page.locator("#version-select")).to_have_value("m3-v2")
            detail_tab("relations")
            expect(page.get_by_role("heading", name="当前版本暂无发送记录")).to_be_visible()
            page.locator("#version-select").select_option("m3-v1")
            expect(page.locator("#detail tbody tr")).to_have_count(1)
            page.locator('#detail [data-action="locate-message"][data-id="msg09"]').click()
            page.locator('#message-msg09 [data-action="open-asset"]').click()
            expect(page.locator("#version-select")).to_have_value("m3-v1")
            expect(page.locator(".document-paper")).not_to_contain_text("新增“资料来源”")
            check("历史聊天展示已发送版本，不被待审核新稿覆盖")

            nav("customers")
            page.locator('#main .customer-name[data-id="c2"]').click()
            expect(page.locator("#customer-profile-content")).not_to_contain_text("待审核")
            page.locator('#customer-profile-tabs [data-id="content"]').click()
            page.locator('#customer-profile-content [data-action="open-asset"][data-id="m3"]').click()
            expect(page.locator("#version-select")).to_have_value("m3-v1")
            check("客户关联内容入口也锁定实际收到的历史版本")

            nav("customers")
            page.locator('#main .customer-name[data-id="c1"]').click()
            expect(page.locator("#breadcrumb")).to_have_text("客户档案 / 李明")
            expect(page.locator("#customer-profile-page")).not_to_contain_text("周宁")
            expect(page.locator("#customer-profile-page .identity-list")).to_contain_text("EXT-A013")
            expect(page.locator("#customer-profile-page .person-tags")).to_contain_text("风控 · 正常")
            expect(page.locator("#customer-risk-banner")).to_have_count(0)
            page.evaluate("AssetDemo.openCustomerPage('c5')")
            expect(page.locator("#customer-risk-banner")).to_contain_text("REF-20261022-005")
            page.locator('#customer-risk-banner [data-action="open-asset"][data-id="rf1"]').click()
            expect(page.locator("#detail")).to_be_visible()
            page.keyboard.press("Escape")
            page.locator('#customer-profile-back').click()
            check("异常风控在客户页顶部给出原因与来源跳转，正常客户不占位")
            page.screenshot(path=str(OUTPUT / "04-客户完整档案.png"))
            page.locator('#customer-profile-tabs [data-id="chat"]').click()
            expect(page.locator("#customer-profile-content .chat-thread")).to_have_count(2)
            page.locator('#customer-profile-content [data-action="thread"][data-id="cv7"]').click()
            expect(page.locator("#customer-profile-content .chat-header")).to_contain_text("陈悦")
            expect(page.locator("#message-msg28")).to_be_visible()
            page.locator('#customer-profile-tabs [data-id="business"]').click()
            expect(page.locator("#customer-profile-content .record-row")).to_have_count(1)
            expect(page.locator("#customer-profile-content .record-row")).to_contain_text("李明")
            page.locator('#customer-profile-tabs [data-id="content"]').click()
            expect(page.locator("#customer-profile-content .timeline-item")).to_have_count(3)
            check("客户档案汇集多销售会话与实际业务，未混入其他客户记录")

            nav("sales")
            page.locator('#main .sales-name[data-id="e1"]').click()
            expect(page.locator("#detail .identity-list")).to_contain_text("WX-EM-108")
            detail_tab("chat")
            expect(page.locator(".chat-thread")).to_have_count(2)
            detail_tab("content")
            expect(page.locator('#detail tbody [data-action="open-asset"][data-id="m1"]')).to_have_count(2)
            check("销售档案合并一人多账号，并准确展示自身发送记录")
            nav("sales")
            page.locator("#filter-query").fill("WX-EM-101")
            page.locator("#sales-submit").click()
            expect(page.locator("[data-sales-row]")).to_have_count(1)
            expect(page.locator("[data-sales-row]")).to_contain_text("张晨")
            with page.expect_download() as account_download:
                page.locator('.head-actions [data-action="export"]').click()
            account_records = json.loads(Path(account_download.value.path()).read_text(encoding="utf-8"))
            check("人员账号标识搜索与导出范围一致", len(account_records["records"]) == 1 and account_records["records"][0]["id"] == "e1")
            nav("customers")
            page.locator("#filter-query").fill("EXT-A013")
            page.locator("#directory-submit").click()
            expect(page.locator("[data-customer-row]")).to_have_count(1)
            expect(page.locator("[data-customer-row]")).to_contain_text("李明")
            check("客户可以通过来源身份标识检索")

            nav("live")
            open_asset("l1")
            detail_tab("actions")
            expect(page.locator("#detail .action-item")).to_have_count(4)
            page.locator('#detail [data-action="open-customer"][data-id="c1"]').first.click()
            expect(page.locator("#breadcrumb")).to_have_text("客户档案 / 李明")
            page.locator('#customer-profile-back').click()
            expect(page.locator('#detail .drawer-tabs [data-id="actions"]')).to_have_class("active")
            check("直播公共内容和个人动作分别留存，可回跳客户")

            nav("report")
            open_asset("r1")
            detail_tab("relations")
            expect(page.locator("#detail tbody tr")).to_have_count(1)
            expect(page.locator("#detail tbody")).to_contain_text("李明")
            check("研报只通过实际发送记录建立客户关系")

            nav("contract")
            open_asset("ct2")
            expect(page.locator(".document-paper")).to_contain_text("电子问卷及确认")
            expect(page.locator("#detail audio")).to_have_count(0)
            check("电子回访与电话录音保持独立形态")

            nav("cases")
            open_asset("rf1")
            expect(page.locator(".document-paper")).to_contain_text("退款执行：未完成")
            detail_tab("source")
            expect(page.locator("#detail .timeline-item")).to_have_count(4)
            check("退款申请、合同与执行状态分别保留且不提供执行动作")

            nav("call")
            open_asset("ca1")
            page.locator("#detail audio").evaluate("a=>new Promise((resolve,reject)=>{if(a.readyState>=1)return resolve(a.duration);a.onloadedmetadata=()=>resolve(a.duration);a.onerror=()=>reject(new Error('音频不可播放'));})")
            check("外呼演示录音存在且可播放", page.locator("#detail audio").evaluate("a=>a.duration>0"))
            page.locator("#detail audio").evaluate("a=>a.play()")
            page.wait_for_timeout(250)
            check("音频播放时间实际前进", page.locator("#detail audio").evaluate("a=>a.currentTime>0"))
            page.locator("#detail audio").evaluate("a=>a.pause()")
            nav("material")
            open_asset("m2")
            page.locator("#detail video").evaluate("v=>new Promise((resolve,reject)=>{if(v.readyState>=1)return resolve(v.duration);v.onloadedmetadata=()=>resolve(v.duration);v.onerror=()=>reject(new Error('视频不可播放'));})")
            check("演示视频可读取音视频元数据", page.locator("#detail video").evaluate("v=>v.duration>10 && v.videoWidth>0"))
            page.locator("#detail video").evaluate("v=>v.play()")
            page.wait_for_timeout(250)
            check("视频播放时间实际前进", page.locator("#detail video").evaluate("v=>v.currentTime>0"))
            page.locator("#detail video").evaluate("v=>v.pause()")

            nav("sources")
            expect(page.get_by_role("heading", name="待关联资料")).to_be_visible()
            open_asset("u0")
            expect(page.locator("#detail .detail-meta")).to_contain_text("待关联")
            page.keyboard.press("Escape")
            page.locator('[data-action="source-assets"][data-id="oms"]').click()
            expect(page.locator('[data-filter="source"]')).to_have_value("oms")
            check("数据来源可定位资产，关系不足的资料独立保留")

            page.locator("#global-query").fill("今日市场复盘")
            page.locator("#global-query").press("Enter")
            expect(page.locator("tbody tr")).to_have_count(2)
            with page.expect_download() as download_info:
                page.locator('.head-actions [data-action="export"]').click()
            download = download_info.value
            exported = json.loads(Path(download.path()).read_text(encoding="utf-8"))
            check("全局搜索与导出索引使用当前筛选范围", {r["id"] for r in exported["records"]} == {"m1", "cv3"})
            nav("dates")
            page.locator('[data-action="date"][data-id="2026-10-22"]').click()
            check("日期归档按来源发生时间显示消息及业务记录", "2026-10-22" in page.locator(".archive-day").inner_text())
            page.screenshot(path=str(OUTPUT / "05-日期归档.png"), full_page=True)
            page.locator('[data-action="category"][data-id="refund"]').click()
            page.locator('[data-action="date"][data-id="2026-10-22"]').click()
            expect(page.locator(".archive-day")).to_contain_text("提交退款申请")
            expect(page.locator(".archive-day")).to_contain_text("申请已审批")
            check("日期归档包含退款申请与审批的独立历史节点")

            verify_daily_chat(context, url, check, report)

            # 上传资料仅写入隔离浏览器内的独立 IndexedDB。
            page.locator('.head-actions [data-action="upload"]').click()
            page.locator("#upload-file").set_input_files({"name": "空文件.txt", "mimeType": "text/plain", "buffer": b""})
            page.locator("#upload-submit").click()
            expect(page.locator("#upload-error")).to_contain_text("文件为空")
            page.locator("#upload-file").set_input_files({"name": "probe.pdf", "mimeType": "text/html", "buffer": b"<script>window.parent.assetXss=1</script>"})
            page.locator("#upload-submit").click()
            expect(page.locator("#upload-error")).to_contain_text("类型与扩展名不一致")
            page.locator("#upload-file").set_input_files({"name": "probe.pdf", "mimeType": "application/pdf", "buffer": b"<script>window.parent.assetXss=1</script>"})
            page.locator("#upload-submit").click()
            expect(page.locator("#upload-error")).to_contain_text("文件头")
            check("伪装 PDF 被 MIME 和文件头校验拒绝", page.evaluate("window.assetXss === undefined"))
            content = "客户补充资料\n<img src=x onerror=window.assetXss=1>\n此行应以纯文本展示。"
            page.locator("#upload-file").set_input_files({"name": "客户补充资料.txt", "mimeType": "text/plain", "buffer": content.encode("utf-8")})
            page.locator("#upload-name").fill('客户补充资料 <script>window.assetXss=1</script>')
            page.locator("#upload-customer").select_option("c1")
            page.locator("#upload-employee").select_option("e1")
            page.locator("#upload-submit").click()
            expect(page.locator("#upload")).not_to_be_visible()
            expect(page.locator("#detail-title")).to_contain_text("客户补充资料")
            expect(page.locator("#detail .document-paper")).to_contain_text("<img src=x")
            check("上传标题和正文安全转义", page.evaluate("window.assetXss === undefined"))
            uploaded = page.evaluate("AssetDemo.getState().drawer.id")
            page.reload()
            page.wait_for_function("window.assetDemoReady === true")
            check("上传资料及明确关系在刷新后恢复", page.evaluate("id=>{const a=AssetDemo.getData().assets.find(a=>a.id===id);return !!a&&a.customers[0]==='c1'&&a.employees[0]==='e1';}", uploaded))
            page.locator('.head-actions [data-action="upload"]').click()
            png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9ZQmcAAAAASUVORK5CYII=")
            page.locator("#upload-file").set_input_files({"name": "补充图片.png", "mimeType": "image/png", "buffer": png})
            page.locator("#upload-submit").click()
            expect(page.locator("#detail-title")).to_have_text("补充图片")
            detail_tab("extraction")
            expect(page.locator("#detail .extract-box").first).to_contain_text("未调用识别或总结服务")
            check("新上传图片留存原件，提取状态如实显示待处理")
            page.keyboard.press("Escape")

            page.locator('.head-actions [data-action="upload"]').click()
            pdf_data = demo_pdf()
            page.locator("#upload-file").set_input_files({"name": "补充协议.pdf", "mimeType": "application/pdf", "buffer": pdf_data})
            page.locator("#upload-submit").click()
            expect(page.locator("#detail-title")).to_have_text("补充协议")
            expect(page.locator("#detail .preview-box")).to_contain_text("PDF 原件已留存")
            pdf_mime = page.evaluate("async()=>{const a=AssetDemo.getData().assets.find(a=>a.id===AssetDemo.getState().drawer.id);return (await fetch(a.versions[0].original)).headers.get('Content-Type');}")
            with page.expect_download() as pdf_download:
                page.get_by_role("button", name="下载 PDF 原件").click()
            check("有效PDF按正确内容类型留存且原始字节可下载", pdf_mime == "application/pdf" and Path(pdf_download.value.path()).read_bytes() == pdf_data)
            page.keyboard.press("Escape")

            page.locator('.head-actions [data-action="upload"]').click()
            page.locator("#upload-file").set_input_files({"name": "长名称.txt", "mimeType": "text/plain", "buffer": b"long title test"})
            page.locator("#upload-name").fill("A" * 100)
            page.locator("#upload-submit").click()
            expect(page.locator("#detail-title")).to_have_text("A" * 100)
            page.set_viewport_size({"width": 320, "height": 800})
            expect(page.locator('#detail [data-action="drawer-close"]')).to_be_in_viewport(ratio=1)
            close_bounds = page.locator('#detail [data-action="drawer-close"]').bounding_box()
            check("100字符标题在320px下仍可关闭抽屉", close_bounds["x"] >= 0 and close_bounds["x"] + close_bounds["width"] <= 321)
            page.keyboard.press("Escape")
            page.set_viewport_size({"width": 1440, "height": 1000})

            nav("board")
            expect(page.locator(".board-kpi")).to_have_count(6)
            expect(page.locator(".board-kpi strong").first).to_have_text("12,480")
            expect(page.locator(".risk-pie svg path")).to_have_count(5)
            expect(page.locator(".risk-legend li")).to_have_count(6)
            expect(page.locator(".risk-legend li.total")).to_contain_text("1,182")
            expect(page.locator(".risk-highlight")).to_contain_text("占覆盖客户 3.1%")
            expect(page.locator(".trend-dot")).to_have_count(7)
            expect(page.locator(".trend-summary")).to_contain_text("30 日峰值")
            expect(page.locator(".trend-note")).to_contain_text("见顶")
            check("看板展示资产、客户、风控饼图分布与单线风险趋势")
            page.locator('[data-action="board-range"][data-id="30"]').click()
            expect(page.locator(".trend-dot")).to_have_count(30)
            expect(page.locator(".board-kpi em").first).to_contain_text("近 30 日新增 +1182")
            check("时间范围切换同时更新趋势区间与增量口径")
            page.locator('.board-kpi[data-id="cases"]').click()
            expect(page.locator("h1")).to_have_text("咨诉与退款")
            check("看板指标可下钻到明细页")

            for page_id, label in [("board", "数据资产看板"), ("all", "资产检索"), ("material", "营销素材"), ("customers", "客户档案"), ("sales", "销售档案"), ("live", "文字直播间"), ("report", "每日研报"), ("contract", "合同档案"), ("product", "商品档案"), ("order", "订单与服务"), ("call", "外呼记录"), ("cases", "咨诉与退款"), ("sources", "数据来源"), ("dates", "按日期归档")]:
                nav(page_id)
                expect(page.locator("h1")).to_have_text(label)
            check("全部十四个页面入口可以正常切换")

            for width in (1280, 900, 390):
                page.set_viewport_size({"width": width, "height": 844})
                if width < 620:
                    page.locator("#mobile-nav").select_option("material")
                else:
                    nav("material")
                check(f"{width}px 页面无整体横向溢出", page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"))
                if width == 390:
                    page.screenshot(path=str(OUTPUT / "06-移动端素材.png"), full_page=True)
                    page.locator('[data-asset-row="m1"] .title').click()
                    detail_tab("relations")
                    check("窄屏详情保持在视口内", page.locator("#detail").evaluate("e=>e.getBoundingClientRect().width<=innerWidth"))
                    page.screenshot(path=str(OUTPUT / "07-移动端素材详情.png"))
                    page.keyboard.press("Escape")

            # 展示截图使用全新上下文，排除边界测试上传的探针标题。
            clean_context = browser.new_context(viewport={"width": 390, "height": 844})
            clean_page = clean_context.new_page()
            clean_page.goto(url)
            clean_page.wait_for_function("window.assetDemoReady === true")
            clean_page.locator("#mobile-nav").select_option("material")
            clean_page.screenshot(path=str(OUTPUT / "06-移动端素材.png"), full_page=True)
            clean_page.locator('#main [data-asset-row="m1"] .title').click()
            clean_page.locator('#detail .drawer-tabs [data-id="relations"]').click()
            expect(clean_page.locator('#detail [data-action="drawer-close"]')).to_be_in_viewport(ratio=1)
            clean_page.screenshot(path=str(OUTPUT / "07-移动端素材详情.png"))
            clean_context.close()

            # 本地文件直开也能正常启动和查看媒体。
            direct = context.new_page()
            direct.goto((ROOT / HTML).as_uri())
            direct.wait_for_function("window.assetDemoReady === true")
            check("无需服务器也可直接打开 HTML", direct.locator("h1").inner_text() == "资产检索")
            direct.close()

            for name, digest in BACKUP_HASHES.items():
                actual = hashlib.sha256((ROOT / "bk" / name).read_bytes()).hexdigest().upper()
                check("原备份未修改：" + name, actual == digest)
            check("没有未捕获脚本错误", not report["pageErrors"])
            check("没有浏览器控制台错误", not report["consoleErrors"])
            check("没有失败的资源请求", not report["requestFailures"])
            browser.close()
            report["result"] = "passed"
    except Exception as error:
        report["result"] = "failed"
        report["failure"] = str(error)
        raise
    finally:
        server.shutdown()
        server.server_close()
        (OUTPUT / "verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"验证报告：{OUTPUT / 'verification.json'}", flush=True)


if __name__ == "__main__":
    main()
