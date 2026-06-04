# 一键超分按钮接入计划

## Context

用户要求在"创建角色/场景"页面的右侧资产区，在"创建视图"按钮旁边增加一个"一键超分"按钮。按钮需标注 🪙5 积分消耗，点击触发二次确认弹窗（复用页面已有的积分确认弹窗样式）。

## 改动范围

**仅修改一个文件**：`主体管理-创建主体.html`

## 实现方案

### 1. HTML：在 `asset-action-row` 中新增按钮

在现有"创建视图"按钮旁边插入：
```html
<button class="btn btn-sr" type="button" id="srExecuteBtn" disabled>🪙5 · 一键超分</button>
```

复用 `.asset-action-row` 的 flex + gap: 12px 布局，按钮自动并排。

### 2. CSS：新增 `.btn-sr` 样式

给超分按钮一个和"创建视图"区分的绿色风格（参考 AI 生图按钮的绿色用法）：
```css
.btn-sr { border-color: #10b981; background: #10b981; color: #ffffff; }
.btn-sr:hover { background: #059669; border-color: #059669; }
```
禁用状态复用现有 `.btn:disabled` 样式。

### 3. JS：绑定点击事件

- 超分按钮初始禁用（同创建视图，未上传主图时禁用）
- 上传/AI 生图后有主图时解锁
- 点击触发 `openCreditsConfirm(5, executeSuperResolution)` — 复用已有的积分确认弹窗
- `executeSuperResolution()` 模拟超分：2s loading → toast 提示"超分完成"

### 4. 积分消耗逻辑

- 每张 5 积分，弹窗文案："此操作会消耗 🪙5 积分，请确定执行操作"
- 弹窗样式复用页面已有的 `.credits-confirm-overlay` / `.credits-confirm-modal`

## 验证方式

1. 浏览器打开 HTML
2. 未上传图片时超分按钮禁用
3. 上传图片后按钮解锁
4. 点击按钮 → 弹出积分确认弹窗（🪙5）
5. 确认 → 模拟超分完成，toast 提示
