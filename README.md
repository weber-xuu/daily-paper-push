# 📚 每日论文推送

[![GitHub Pages](https://img.shields.io/badge/GitHub%20Pages-在线查看-orange)](https://weber-xuu.github.io/daily-paper-push/)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

> 每天上午 9:00 自动搜索并推送**多模态推理 (Multimodal Reasoning)** 领域的最新 arXiv 论文到飞书，同时生成精美的学术网页。

---

## ✨ 功能特性

| 功能 | 说明 |
|------|------|
| 🔍 **自动搜索** | 每天定时搜索 arXiv 最新多模态推理论文 |
| 🛡️ **三层降级** | arXiv API → Semantic Scholar → DeepSeek API，确保稳定获取 |
| 🤖 **AI 解读** | 使用大模型对每篇论文进行深度解读 |
| 📱 **飞书推送** | 自动推送到飞书消息 |
| 🌐 **精美网页** | 自动生成并部署学术网页到 GitHub Pages |
| 📂 **按领域归档** | 🎬视频理解 · 🤖具身导航 · 🧮数学推理 · 🎨跨模态生成 |
| 🔎 **实时搜索** | 搜索今日+历史论文标题/作者 |
| 📊 **统计面板** | 覆盖领域、推送时间线可视化 |

---

## 🌐 在线网页

**https://weber-xuu.github.io/daily-paper-push/**

![screenshot](https://img.shields.io/badge/深蓝%2B橙色-学术风设计-blue)

网页特性：
- 🎨 深蓝+橙色学术风配色，左侧橙色 accent bar
- 📝 摘要可展开/收起
- 📅 历史记录页面
- 🔎 实时搜索（含历史记录匹配）
- 📊 点击 🏷️ 覆盖领域 → 领域分布 + 推送时间线

---

## 🏗️ 技术栈

| 层面 | 技术 |
|------|------|
| 前端 | 原生 HTML + CSS + JavaScript（Google Fonts: Noto Serif/Sans SC） |
| 后端 | Python 3（定时脚本 + 网页构建） |
| 数据源 | arXiv API / Semantic Scholar API / DeepSeek API |
| AI 解读 | DeepSeek V4 Pro |
| 部署 | GitHub Pages |
| 推送 | 飞书开放平台 |
| 定时 | Hermes Agent Cron |

---

## 📁 项目结构

```
.
├── index.html          # 学术网页（自动生成）
├── papers.json         # 当日论文数据
├── history.json        # 历史推送记录
├── build_v2.py         # 网页构建脚本
└── .git/               # Git 仓库（for GitHub Pages）
```

> 定时脚本位于 Hermes Agent skill 目录：
> `~/.hermes/skills/research/daily-paper-push/scripts/push_papers.py`

---

## 🚀 本地运行

```bash
# 1. 生成网页
cd web && python3 build_v2.py

# 2. 本地预览
open index.html

# 3. 完整推送（搜索论文 + 解读 + 推送飞书 + 部署）
python3 scripts/push_papers.py
```

需要配置 `~/.hermes/.env`：
```env
LLM_API_KEY=your_key
LLM_API_URL=https://api.deepseek.com/v1/chat/completions
LLM_MODEL=deepseek-v4-pro
FEISHU_APP_ID=your_app_id
FEISHU_APP_SECRET=your_secret
PAPER_TARGET_USER=your_open_id
GITHUB_TOKEN=ghp_xxxx
```

---

## 📊 覆盖领域

论文按关键词自动归类至以下子领域：

| 领域 | 图标 | 代表关键词 |
|------|------|------------|
| Video Understanding | 🎬 | video, temporal, motion, pose, streaming |
| Embodied & Navigation | 🤖 | navigation, VLN, robot, gesture, habitat |
| Cross-Modal Generation | 🎨 | generation, synthesis, diffusion, image editing |
| Math & Geometry | 🧮 | math, geometry, arithmetic, calculation |
| Chain-of-Thought | 🔗 | chain of thought, science QA, step-by-step |
| Document & Chart | 📈 | document, chart, diagram, OCR, table |
| VQA & Visual | 📊 | VQA, visual reasoning, spatial reasoning |

---

## 👤 作者

由 **栗子 (Hermes Agent)** 自动生成和维护。
