# DESIGN.md — 企业数据资产中心交互原型设计系统

> 记录 `数据资产交互设计.html` 的现有 HTML/CSS/JS 系统，作为后续设计决策的独立参考。不改动结构与脚本，仅捕获视觉语言、页面架构、交互模式与数据模型。

## 1. 系统概览

**产品定位**：企业数据资产中心交互原型，面向合规质检、营销合规过程监管、素材合规质检场景。所有业务数据均为虚构演示数据，不构成真实业务结论。

**技术栈**：单文件静态 HTML/CSS/JS，无构建工具，直接用浏览器打开。依赖原生 `<dialog>` 抽屉、CSS Grid/Flexbox、原生 SVG 图标。

**核心创作链路**：来源接入 → 资产检索 → 客户/销售档案 → 数据看板 → 评测上下文导出。

## 2. 视觉系统（三层 CSS）

文件内嵌三层样式，后层覆盖前层，只改视觉语言，不动结构与脚本。

### 第一层：基础紧凑样式（第 9-157 行）
- 色板：`--blue:#1B4A44`（深蓝绿主色），`--nav:#17243a`（深色侧边栏），`--bg:#f5f7fb`。
- 圆角：`--radius:10px`。字体：Microsoft YaHei UI / PingFang SC / Noto Sans CJK SC。
- 按钮：`.btn` 默认白底灰边，`.btn.primary` 蓝色实心。输入框焦点带蓝色光晕。
- 侧边栏固定 216px，顶栏粘性 65px，主体区 `margin-left:216px`。

### 第二层：视觉升级层（第 158-1126 行，ID 无）
- 色板：`--blue:#2f5de0`，`--nav:#101b2d`，`--radius:14px`，背景带径向渐变。
- 按钮圆角 9px，带 hover 阴影与轻微位移；输入框圆角 9px；侧边栏渐变深色背景。
- 卡片、统计卡、面板统一带 `box-shadow` 与 hover 上浮。

### 第三层：设计系统 v2「台账 · LEDGER INK」（第 1213-1629 行，ID `design-system-v2`）
- 方向：暖纸 + 墨黑 + 朱砂。用发丝线替代投影，等宽数字替代花体数字。
- 色板：`--paper:#EFEBE3`，`--ink:#14171A`，`--accent:#AD4322`（朱砂），`--pine:#1B4A44`（松墨），`--gold:#8A6B32`。
- 兼容旧变量：`--blue` 映射为 `--pine`，`--bg` 映射为 `--paper`，避免蓝色残留。
- 细节：`border-radius:3px`（极小圆角），数字强制 `tabular-nums`，滚动条发丝线，页面入场微动画（`ds-rise` / `ds-fade`，`prefers-reduced-motion` 降级）。

## 3. 页面架构与导航

### 壳体（Shell）
- 固定左侧导航栏（`.sidebar`）：品牌、租户（演示企业）、分组导航（资产浏览 / 内容与资料 / 业务记录 / 数据管理）、页脚标语。
- 粘性顶栏（`.topbar`）：面包屑、移动端菜单下拉、全局搜索、演示标识、用户头像。
- 主体区（`.main`）：页面内容容器，带响应式 padding。
- 四个 `<dialog>` 抽屉：`#detail`（资产详情）、`#board-detail`（看板明细列表）、`#source-dialog`（接口配置/同步/日志）、`#eval-dialog`（评测上下文）。
- 全局 Toast（#toast）。

### 导航分组（`navGroups`）
| 组 | 入口 | 图标 | 说明 |
|---|---|---|---|
| 资产浏览 | 数据资产看板 / 资产检索 / 按日期归档 / 客户档案 / 销售档案 | grid/search/calendar/users/user | 主数据入口 |
| 内容与资料 | 营销素材 / 文字直播间 / 每日研报 / 合同档案 | layers/live/file/contract | 内容类资产 |
| 业务记录 | 商品档案 / 订单与服务 / 外呼记录 / 咨诉与退款 | order/order/call/case | 业务记录类资产 |
| 数据管理 | 数据来源 | database | 接口拉取配置 |

每个导航项带条目数计数（`.nav-count`）。

## 4. 核心页面模块

### 4.1 数据资产看板（`board`）
- 时间范围切换：近 7 日 / 近 30 日。
- 7 个 KPI 卡片：本期新增客户、成交笔数、成交金额、退款订单数、退款金额、退款率、净成交金额。
- 成交与退款趋势图（柱状 + 折线双轴）。
- 退款原因分布（饼图 + 明细列表 + 退款洞察）。
- 商品成交表现（进阶/基础服务对比）。
- 退款处理跟进（未完成退款列表）。
- 资产规模与增长（新增归集数 + 每日趋势图）。
- 分类资产规模（按类别：聊天消息、营销素材、外呼记录、合同、订单、咨诉事项、退款申请、研报、直播场次、直播动作、素材审核、商品档案）。
- 档案覆盖与完整性（客户目录覆盖率、销售目录覆盖率、覆盖客户评估率、已支付订单合同齐备率）。
- 统计口径说明（details 展开）。

### 4.2 资产检索（`all`）
- 全局搜索 + 资产类型 / 来源系统 / 日期范围 / 关联客户 / 相关销售 / 文件形式筛选。
- 已选条件标签（可移除）。
- 列表 / 卡片视图切换，分页。
- 资产行显示：类型图标、标题、来源编号、关联客户、相关销售、来源/时间、来源状态、查看按钮。

### 4.3 按日期归档（`dates`）
- 日期索引横向滚动，点击日期查看当天发生记录。
- 时间线按时间倒序排列，每条带类型芯片、标题、内容、来源、查看关联记录按钮。
- 聊天消息类型时：按销售或客户分组，二级目录（人员 → 对接对象 → 消息详情），支持当日聊天归档。

### 4.4 客户档案（`customers`）
**客户目录页**：
- 检索方式：综合 / 客户编号 / 手机号 / 来源客户ID / 客户姓名。
- 筛选：来源系统、对接销售、风控状态、对接团队、服务状态、最近归档更新日期。
- 表格列：客户/编号、联系方式（脱敏）、来源系统、对接销售/团队、服务状态、风控状态、最近归档更新、操作。

**客户二级档案页**（标签页）：
- 档案总览（概览 + 风控状态 + 对接人员 + 适当性摘要 + 获客与服务）
- 客户信息（基础身份、证件与实名、联系方式、跨系统身份、信息来源）
- 沟通记录（企微会话时间线，支持评测选择）
- 投资者适当性（KYC 快照，不重新评分）
- 交易与服务（订单快照）
- 内容与直播（实际收到的内容版本）
- 合同与回访
- 咨诉与退款

**风控判定**（演示规则 `riskRules`）：扫描客户侧表达命中关键词（投诉、退费、违规销售、亏损抱怨、服务不满），结合咨诉/退款事项状态判定等级：未评估 / 正常 / 关注 / 投诉意向 / 投诉处理中 / 已完结。

**评测上下文**（Eval Context Pack）：
- 多选记录（支持区间选择、Shift 点击、全选/清空）。
- 评测目标：投诉意向 / 客户画像 / 服务风险归因。
- 盲评模式：隐藏风险等级、评估历史与处置结论。
- 补齐上下文：选中记录前后各 1 条。
- 输出：Markdown，包含客户基本面、业务事实、记录时间线、口径与限制；已脱敏（姓名→编号、手机号/证件号/微信号脱敏）。
- 支持复制 Markdown 或下载 .md。

### 4.5 销售档案（`sales`）
- 员工目录：按团队 / 账号情况筛选，展开企微账号明细。
- 员工二级档案页（标签页）：全部记录 / 聊天归档 / 关联客户 / 内容使用 / 外呼记录。
- 账号筛选器：可多选企微账号，筛选时间线与实际对接客户。

### 4.6 商品档案（`product`）
- 商品分类 / 等级 / 状态 / 来源系统筛选。
- 商品详情标签页：商品信息 / 关联订单 / 客户与销售 / 合同与退款 / 关联内容 / 来源与历史。
- 价格与可售配置、历史配置快照、订单成交记录、产品引用依据。

### 4.7 数据来源（`sources`）
- 7 个模拟数据来源：企微会话存档、订单管理系统、合规管理系统、文字直播服务、投研内容库、外呼记录服务。
- 每个来源卡片：接口地址、拉取策略、连接检测、最近同步、最近成功快照、下次计划。
- 操作：配置接口、模拟同步、运行日志、暂停/恢复。
- 模拟同步场景：成功返回 / 认证失败 / 接口超时 / 字段映射异常。
- 认证凭据仅本次会话，不写入本地存储。

## 5. 详情抽屉（`#detail`）

打开任意资产后以右侧抽屉展示，支持嵌套栈（`state.stack`）与返回。

**通用标签页**：
- 预览 / 原始内容：图片 / 视频 / 音频 / 文档原件预览，版本选择器，档案信息 KV。
- 结构化内容：文字识别 / 转写 / 视频总结 / 原文整理，处理记录。
- 关联记录：实际发送记录表格、关联对象、同客户业务记录。
- 关联商品（如有）：商品引用卡片、订单成交快照。
- 送审与审核：审核历史时间线、全部版本概览。
- 来源与历史：来源标识、版本留存、来源处理历史。

**对话资产**：聊天消息气味（员工/客户区分）、附件媒体气泡、来源账号标签。

**直播资产**：公共直播内容（逐条）、场次档案、客户动作列表。

## 6. 交互模式

### 状态管理（`state`）
- 页面级：`page`、`query`、`type`、`format`、`source`、`start`、`end`、`customerId`、`salesId`、`layout`、`pageNo` 等。
- 抽屉级：`drawer`（kind/id/tab/versionId/threadId/highlight）、`stack`（历史抽屉栈）。
- 评测级：`evalSel`（ids/anchor）、`evalTarget`、`evalBlind`、`evalPad`、`evalExports`。
- 客户档案：`customerProfile`（id/tab/threadId/highlight/origin）。
- 销售档案：`salesProfile`（id/tab/threadId/highlight/accountIds/origin）。

### 事件委托
- 全局 `click` 委托到 `[data-action]`，统一处理导航、打开资产/客户/销售、标签页切换、评测操作、账号筛选、抽屉操作、版本选择、导出等。
- 全局 `input` / `change` / `submit` / `keydown` 委托处理搜索防抖（180ms）、筛选条件变更、回车执行检索。

### 无障碍
- 所有按钮带 `aria-label` / `aria-pressed` / `aria-current`。
- `<dialog>` 原生模态，Esc 关闭，点击 backdrop 外侧关闭。
- `:focus-visible` 统一轮廓样式。
- `prefers-reduced-motion` 禁用动画与过渡。
- SVG 图标 `aria-hidden="true"`。

## 7. 数据模型（虚构演示）

### 核心实体
| 实体 | 关键字段 | 数量 |
|---|---|---|
| assets | id, type, title, source, sourceId, time, employees[], customers[], status, fields, versions[], extract, description, original, unlinked | ~200+（含生成的订单流水） |
| customers | id, name, code, wecom, union, open, phone, product, tags, since, directoryOnly, directorySales[], identitySources[], identities[] | 6 静态 + 114 目录样本 |
| employees | id, name, code, team, role, accounts[], accountIds[], color | 4 静态 + 37 目录样本 |
| conversations | id, customerId, employeeId, account, accountId | 7 + 1 重客户 |
| messages | id, conversationId, sender, time, text, assetId, versionId | 32 + 重客户消息 |
| liveActions | id, liveId, customerId, time, action, text | 8 + 重客户动作 |
| reviews | id, assetId, versionId, submitted, reviewed, submitter, reviewer, result, note, source, reference, scope | 5 + 衍生 |
| sources | id, name, short, icon, scope, snapshot | 7 |
| businessSeeds | order, contract, call, case, refund 业务种子 | 16 |
| boardAssessments | 风险评估历史 | 9 |
| complaintWarnings | 咨诉预警（客户、原因、时间、状态、引语） | 18 |
| productSeeds | 商品配置（基础/进阶/历史/专项） | 4 |
| deal流水 | 30 天模拟订单、合同、退款 | 程序生成 |

### 资产类型（`types`）
material（营销素材）、conversation（聊天会话）、live（文字直播）、report（每日研报）、contract（合同资料）、product（商品档案）、order（订单服务）、call（外呼记录）、case（咨诉事项）、refund（退款申请）。

### 文件形式（`formats`）
image（海报图片）、video（视频）、text（文字）、audio（音频）、pdf（PDF文档）。

### 风险规则（`riskRules`）
- R-T0 投诉意向：投诉/监管/举报/12386/曝光/起诉
- R-REFUND 投诉意向：退费/退款/退钱/终止服务/解约/不做了
- R-SALES 投诉意向：稳赚/保本/承诺收益/代操作/包赚
- R-LOSS 关注：一直亏/亏了/亏死/骗人/太差
- R-SERVICE 关注：太慢/有点慢/没人管/联系不上/服务不到位/不回复

## 8. 响应式断点

| 断点 | 变化 |
|---|---|
| ≥1600px | 主体 padding 32px 40px，资产/人员网格 4 列 |
| ≤1200px | 侧边栏 200px，网格 2 列，表格 padding 减小 |
| ≤900px | 侧边栏 72px（仅图标），品牌居中，导航项无文字 |
| ≤620px | 侧边栏隐藏，移动端菜单下拉，单列布局，卡片全宽 |

各 CSS 层均有独立响应式覆盖，第三层（LEDGER INK）有专门的 `@media(max-width:1200/900/620px)` 微调。

## 9. 输出与导出

- 客户档案脱敏 JSON 导出（`customerProfileExport`）。
- 销售档案 JSON 导出（`salesProfileExport`）。
- 商品档案 JSON 导出（`productExportRecord`）。
- 当前范围结构化索引 JSON 导出（`exportIndex`，包含资产、查询上下文、归档日期）。
- 看板明细列表 JSON 导出。
- 接口模拟日志 JSON 导出。
- 评测上下文 Markdown 复制 / 下载。

## 10. 已知约束与演示边界

- 所有数据为虚构演示，不接入真实后台；接口配置为模拟同步，不发送真实请求。
- 认证凭据不落盘，刷新后需重新输入。
- 风控判定为演示规则，未接入质检模型。
- 未提供字段显示“未提供”，不从姓名、证件、订单或聊天推断缺失值。
- 商品配置更新与订单成交快照分别留存，不相互覆盖。
- 客户、销售、账号按稳定 ID 去重，同名不自动合并。

## 11. 文件位置

- 原型文件：`1_原型/数据资产交互设计.html`（3360 行，单文件自包含）
- 设计文档：`DESIGN.md`（本文件）
- 产品文档：`PRODUCT.md`
