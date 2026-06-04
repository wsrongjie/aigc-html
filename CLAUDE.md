# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

**投顾视频平台** — 基于 AI 大模型的短视频自动制作平台，面向投顾/理财顾问场景。

核心创作链路：**台词 → 主体管理 → 分镜 → 成片合成**

## 常用命令

### Python 环境
- 启动口播台词语音合成服务：`python 口播台词/server.py`（端口 8000，依赖 fastapi + dashscope）
- 运行 SSML 语音合成 Demo：`python 口播台词/ssml_demo.py`
- 分镜自动评测（仅规则校验，不调 LLM）：`python 台词转分镜测评/evaluate_storyboards.py --dry-run`
- 分镜自动评测（规则 + LLM 裁判）：`python 台词转分镜测评/evaluate_storyboards.py --llm --rank`
- 分镜直评（本地规则评分，不调 API）：`python 台词转分镜测评/direct_judge_storyboards.py`

### 环境依赖
- 语音合成需设置 `DASHSCOPE_API_KEY` 或在代码中传入
- LLM 评测需设置 `OPENAI_API_KEY` 和 `OPENAI_BASE_URL`（兼容接口）
- 主要依赖：`fastapi`、`uvicorn`、`dashscope`、`openpyxl`、`openai`

## 代码架构

### 目录结构

```
AIGC/
├── AI视频原型/                  # HTML 交互式原型
│   ├── 3.0b版本/                # 主版本原型（17个页面）
│   ├── video/                   # 视频流程专用页面
│   ├── audio/                   # 音频管理页面
│   └── 草稿/                    # 废弃版本
├── 口播台词/                    # 语音合成服务
│   ├── server.py                # FastAPI + CosyVoice 合成后端
│   ├── ssml_demo.py             # SSML 合成测试脚本
│   ├── index.html               # 前端页面
│   ── cosyvoice-ssml-studio.html
├── 台词转分镜测评/              # 分镜质量评测系统
│   ├── evaluate_storyboards.py  # 主评测脚本（规则+LLM）
│   ├── direct_judge_storyboards.py  # 本地直评脚本（不调 API）
│   └── 分镜自动评测方案.md       # 评测方案文档
├── ssml/                        # SSML 音频样例
└── cosyvoice/                   # CosyVoice 相关
```

### 核心模块说明

**1. 语音合成服务（口播台词/server.py）**

FastAPI 后端，提供两个核心接口：
- `POST /api/synthesize` — 调用阿里云 CosyVoice TTS 合成音频，支持 SSML 格式（rate/pitch/volume/break）
- `GET /api/validate` — 验证 Dashscope API Key 是否有效

关键数据流：前端传入台词列表（含语速/音调/音量/停顿参数） → 构建 SSML → 调用 CosyVoice → 返回 base64 音频

**2. 分镜评测系统（台词转分镜测评/）**

两套脚本共享同一套评测逻辑：

- `evaluate_storyboards.py` — 双层评测：
  - **规则层**：JSON 有效性、字段完整度、台词覆盖率、时长偏差、动作重复率、固定场景约束命中率，综合输出 100 分制规则分
  - **LLM 裁判层**：7 维度评分（台词切分/镜头节奏/画面可执行性/动作设计/情绪匹配/人物一致性/修改成本），支持同组匿名横评排名

- `direct_judge_storyboards.py` — 纯本地评分，基于各模型的历史风格特征（MODEL_STYLE 字典）做校准，不调用外部 API

输入：Excel 文件（台词簿.xlsx），每行包含台词、模型名、分镜 JSON 结果
输出：追加评测列的 Excel 文件 + 模型汇总表

**3. HTML 原型（AI视频原型/3.0b版本/）**

纯静态 HTML 原型，无构建工具，直接用浏览器打开即可。

核心页面流程：
- `index.html` — 导航首页，分 5 大板块：资产（主体/音频/视频）、导演台、全部工具、个人中心
- `step1-台词创建` → `step2-主体管理` → `step3-分镜管理` → `step4-成片合成`（导演台核心链路）
- `主体管理-首页/创建主体` — 人物角色管理
- `语音首页/新建语音模型` — CosyVoice 音色管理

所有页面使用统一的设计系统（CSS 变量定义在 index.html 中）：主色 `#2f6bff`，侧边栏深色 `#1C1C1E`，圆角 12px。

## 关键设计约束

- 分镜用于"固定人物角色、固定背景、正面对镜口播、上半身/中近景"的视频生成场景
- 视频生成模型使用 wan2.7 系列（wan2.7-image 生图、wan2.7-t2v 视频）
- 语音合成使用 cosyvoice-v3.5-plus
- 文本处理使用 qwen3.6-plus
- 积分换算：1 元 = 10 积分
