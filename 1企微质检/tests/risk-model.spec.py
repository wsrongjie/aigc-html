"""验证风控模型管理原型的业务边界、核心交互与响应式布局。"""
import functools
import json
import os
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(Path.home() / "AppData/Local/ms-playwright"))
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "risk-model"
OUT.mkdir(parents=True, exist_ok=True)


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


server = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(ROOT)))
threading.Thread(target=server.serve_forever, daemon=True).start()
url = f"http://127.0.0.1:{server.server_port}/风控质检-交互原型.html"
report = {"checks": [], "errors": [], "failed_requests": []}


def check(name, condition=True):
    assert condition, name
    report["checks"].append(name)
    print("通过：" + name, flush=True)


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": 1440, "height": 960}, reduced_motion="reduce")
    page = context.new_page()
    page.on("pageerror", lambda error: report["errors"].append(str(error)))
    page.on("requestfailed", lambda request: report["failed_requests"].append(request.url))
    page.goto(url)
    page.wait_for_selector("#risk-model-app")

    check("进入风控模型管理首页", page.locator("[data-page='models']").get_attribute("aria-current") == "page")
    check("模型列表以表格展示", page.locator("#model-table tbody tr").count() >= 4)
    check("侧栏包含规则模型计划结果四个业务入口", page.locator(".side-nav [data-nav]").count() == 4)
    check("模型列表未使用业务场景作为模型字段", page.locator("#model-table").get_by_text("企微").count() == 0)
    page.screenshot(path=str(OUT / "01-模型列表.png"), full_page=True)

    page.locator("[data-action='open-model']").first.click()
    expect(page.locator("#detail-title")).to_contain_text("模型")
    check("模型详情为独立二级页面", page.locator("[data-view='model-detail']").is_visible())
    check("详情提供测试与版本页签", page.locator("[data-detail-tab='tests']").count() == 1 and page.locator("[data-detail-tab='versions']").count() == 1)
    page.locator("[data-detail-tab='rules']").click()
    check("详情展示已关联多条规则", page.locator("#bound-rule-table tbody tr").count() >= 3)
    page.screenshot(path=str(OUT / "02-模型详情.png"), full_page=True)

    page.locator("[data-action='back-list']").click()
    page.locator("#model-table tbody tr").nth(3).locator("[data-action='open-model']").first.click()
    page.locator("[data-detail-tab='tests']").click()
    check("未测试草稿不展示虚构验证指标", "尚未执行测试验证" in page.locator(".tab-content").inner_text() and page.locator(".metric-card").count() == 0)
    page.locator("[data-detail-tab='versions']").click()
    check("未发布草稿不展示虚构发布历史", "当前仍是草稿" in page.locator(".tab-content").inner_text())
    page.locator("[data-detail-tab='overview']").click()
    page.locator("[data-action='edit-model']").click()
    check("继续配置时保留原负责人", page.locator("#model-owner").input_value() == "陈嘉")
    page.locator("[data-action='next-step']").click()
    page.locator("[data-action='next-step']").click()
    page.locator("[data-action='next-step']").click()
    page.locator("[data-action='run-test']").click()
    page.wait_for_selector("[data-test-state='passed']")
    page.locator("[data-action='test-mode'][data-mode='compare']").click()
    check("草稿即使完成测试也不能冒充已发布对比基线", "当前是首个版本" in page.locator("[data-step-panel='4']").inner_text())
    page.locator("[data-action='cancel-editor']").first.click()
    page.locator("[data-action='create-model']").click()
    expect(page.locator("#editor-title")).to_contain_text("新建风控模型")
    editor_labels = " ".join(page.locator("[data-model-config] label").all_inner_texts())
    for forbidden in ("检查员工", "企微账号", "直播间", "素材来源", "执行日期", "运行时间"):
        check(f"模型配置不包含业务计划字段：{forbidden}", forbidden not in editor_labels)

    page.locator("#model-name").fill("行情波动营销风险模型")
    page.locator("[data-action='next-step']").click()
    expect(page.locator("[data-step-panel='2']")).to_be_visible()
    check("规则库支持关联多条规则", page.locator("[data-rule-check]").count() >= 6)
    page.locator("#rule-domain").select_option(label="投顾服务合规")
    check("规则领域筛选可以缩小候选范围", page.locator("[data-rule-row]:visible").count() == 2)
    page.locator("#rule-domain").select_option("all")
    page.locator("[data-rule-check]").nth(0).check()
    page.locator("[data-rule-check]").nth(1).check()
    page.locator("[data-rule-check]").nth(2).check()
    page.locator("[data-action='next-step']").click()

    expect(page.locator("[data-step-panel='3']")).to_be_visible()
    page.locator("#model-sensitivity").select_option("high")
    page.locator("[data-rule-override]").first.click()
    check("规则级参数支持覆盖模型默认值", page.locator("[data-override-panel]").first.is_visible())
    check("规则级配置控件具有明确标签", page.locator("[data-override-panel]").first.locator("select,input").evaluate_all("els=>els.every(el=>el.labels&&el.labels.length===1)"))
    page.screenshot(path=str(OUT / "02A-规则级识别配置.png"), full_page=True)
    page.locator("[data-action='next-step']").click()

    expect(page.locator("[data-step-panel='4']")).to_be_visible()
    check("技术验证完成前禁止进入发布", page.locator("[data-action='next-step']").is_disabled())
    page.locator("[data-action='run-test']").click()
    page.wait_for_selector("[data-test-state='passed']")
    check("测试验证展示总体与规则级指标", page.locator(".metric-card").count() >= 6 and page.locator("#test-rule-table tbody tr").count() == 3)
    page.locator("[data-action='sample-detail']").first.click()
    check("异常样本可以查看原文、证据和人工标注", page.locator("#sample-dialog").is_visible() and "否定语义" in page.locator("#sample-dialog").inner_text())
    page.locator("[data-action='close-sample']").click()
    page.locator("[data-action='sample-detail']").nth(1).click()
    check("异常样本与当前规则行保持一致", "夸大历史业绩或胜率" in page.locator("#sample-dialog").inner_text() and "R-002" in page.locator("#sample-dialog").inner_text())
    page.locator("[data-action='close-sample']").click()
    page.locator("[data-action='test-mode'][data-mode='single']").click()
    page.locator("#single-sample").fill("今天天气不错，我们改天再聊。")
    page.locator("[data-action='run-single']").click()
    check("单条调试不会为无风险输入生成不存在的命中", "未发现已选规则" in page.locator("[data-step-panel='4']").inner_text())
    page.locator("#single-sample").fill("这个产品肯定不会亏，本金和收益我都可以保证。")
    page.locator("[data-action='run-single']").click()
    check("单条样本调试根据输入和已选规则展示命中证据", "明确承诺保本或收益" in page.locator("[data-step-panel='4']").inner_text() and "肯定不会亏" in page.locator("[data-step-panel='4']").inner_text())
    page.locator("[data-action='test-mode'][data-mode='compare']").click()
    check("首个版本没有基线时展示对比空状态", "当前是首个版本" in page.locator("[data-step-panel='4']").inner_text())
    page.locator("[data-action='test-mode'][data-mode='dataset']").click()
    page.screenshot(path=str(OUT / "03-测试验证.png"), full_page=True)
    page.locator("[data-action='prev-step']").click()
    page.locator("#model-sensitivity").select_option("low")
    page.locator("[data-action='next-step']").click()
    check("识别参数变化后旧测试立即失效", page.locator("[data-test-state='passed']").count() == 0 and page.locator("[data-action='next-step']").is_disabled())
    page.locator("[data-action='run-test']").click()
    page.wait_for_selector("[data-test-state='passed']")
    page.locator("[data-action='next-step']").click()

    expect(page.locator("[data-step-panel='5']")).to_be_visible()
    page.locator("[data-action='publish-model']").click()
    expect(page.locator("#publish-dialog")).to_be_visible()
    check("业务指标未达标采用风险提示而非技术硬阻断", "填写发布原因" in page.locator("#publish-dialog").inner_text())
    page.screenshot(path=str(OUT / "03A-发布风险提示.png"), full_page=True)
    page.locator("#publish-reason").fill("当前处于行情波动期，优先保证风险召回，接受阶段性误报。")
    page.locator("[data-action='confirm-publish']").click()
    expect(page.locator("#detail-title")).to_contain_text("行情波动营销风险模型")
    check("发布后形成只读版本", page.locator("[data-model-status='published']").count() == 1)
    check("发布快照冻结了每条规则版本", page.evaluate("RiskModelDemo.getModels().find(x=>x.name==='行情波动营销风险模型').rules.every(x=>!!x.ruleVersion)"))
    page.locator("[data-detail-tab='tests']").click()
    check("发布后测试页读取本次88.2分预警结果", "88.2%" in page.locator(".tab-content").inner_text() and "指标预警" in page.locator(".tab-content").inner_text())
    page.locator("[data-detail-tab='logs']").click()
    check("操作记录保留风险接受原因", "优先保证风险召回" in page.locator("[data-publish-reason]").inner_text())
    page.screenshot(path=str(OUT / "04-发布后详情.png"), full_page=True)

    page.locator("[data-detail-tab='overview']").click()
    published_name = page.locator("#detail-title").inner_text()
    published_code = page.locator(".detail-hero .eyebrow").inner_text().split(" · ")[0]
    page.locator("[data-action='new-version']").click()
    check("创建新版本保留模型名称和稳定编号", page.locator("#model-name").input_value() == published_name and page.locator("#model-code").input_value() == published_code)
    check("创建新版本不会误加副本标识", "副本" not in page.locator("#model-name").input_value() and "COPY" not in page.locator("#model-code").input_value())
    page.evaluate("rules.find(x=>x.id==='R-001').version='v9.0'")
    page.locator("[data-action='next-step']").click()
    page.locator("[data-action='next-step']").click()
    page.locator("[data-action='next-step']").click()
    page.locator("[data-action='run-test']").click()
    page.wait_for_selector("[data-test-state='passed']")
    page.locator("[data-action='test-mode'][data-mode='compare']").click()
    check("版本对比读取真实已发布基线快照", "v1.0.0" in page.locator("[data-step-panel='4']").inner_text() and "差异 0.0" in page.locator("[data-step-panel='4']").inner_text())
    page.locator("[data-action='test-mode'][data-mode='dataset']").click()
    page.locator("[data-action='next-step']").click()
    check("新版本发布确认显示真实目标版本", "发布 v1.1.0" in page.locator("[data-step-panel='5']").inner_text())
    page.locator("[data-action='publish-model']").click()
    page.locator("#publish-reason").fill("新版本扩大召回，保留上一版本完整快照备查。")
    page.locator("[data-action='confirm-publish']").click()
    check("新版本保留旧版本完整配置快照", page.evaluate("RiskModelDemo.getModels().find(x=>x.name==='行情波动营销风险模型').versionHistory.length") == 1)
    check("规则版本号与冻结正文版本始终一致", page.evaluate("(()=>{const m=RiskModelDemo.getModels().find(x=>x.name==='行情波动营销风险模型');return m.rules.every(b=>m.ruleSnapshot.find(s=>s.id===b.ruleId)?.version===b.ruleVersion)})()"))
    page.locator("[data-detail-tab='versions']").click()
    check("历史版本可展开查看冻结配置", page.locator(".tab-content details").count() == 1)
    page.locator("[data-action='back-list']").click()

    page.locator("[data-action='create-model']").click()
    page.locator("#model-name").fill("异步隔离验证A")
    page.locator("[data-action='next-step']").click()
    page.locator("[data-rule-check]").first.check()
    page.locator("[data-action='next-step']").click()
    page.locator("[data-action='next-step']").click()
    page.locator("[data-action='run-test']").click()
    page.locator("[data-action='cancel-editor']").first.click()
    page.locator("[data-action='create-model']").click()
    page.wait_for_timeout(700)
    check("离开旧测试后异步结果不会污染新模型", page.evaluate("RiskModelDemo.getState().editor.testState") == "pending")
    page.locator("[data-action='cancel-editor']").first.click()
    context.close()

    for width, height, name in ((1024, 800, "05-笔记本"), (390, 844, "06-窄屏")):
        context = browser.new_context(viewport={"width": width, "height": height}, reduced_motion="reduce")
        page = context.new_page()
        page.on("pageerror", lambda error: report["errors"].append(str(error)))
        page.on("requestfailed", lambda request: report["failed_requests"].append(request.url))
        page.goto(url)
        page.wait_for_selector("#risk-model-app")
        check(f"{width}px 无整页横向溢出", page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"))
        check(f"{width}px 可进入模型列表", page.locator("#model-table").count() == 1)
        if width == 390:
            page.locator("[data-action='create-model']").click()
            page.locator("#model-name").fill("窄屏规则选择验证")
            page.locator("[data-action='next-step']").click()
            check("390px 规则候选行内容不被裁切", page.locator("#rule-list").evaluate("el=>el.scrollWidth<=el.clientWidth+1"))
        page.screenshot(path=str(OUT / f"{name}.png"), full_page=True)
        context.close()

    check("无脚本错误与失败资源", not report["errors"] and not report["failed_requests"])
    report["result"] = "passed"
    (OUT / "verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    browser.close()

server.shutdown()
