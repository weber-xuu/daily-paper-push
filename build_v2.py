#!/usr/bin/env python3
"""Build beautified index.html from papers.json and history.json."""
import json, os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PAPERS_JSON = os.path.join(SCRIPT_DIR, 'papers.json')
HISTORY_JSON = os.path.join(SCRIPT_DIR, 'history.json')
INDEX_HTML = os.path.join(SCRIPT_DIR, 'index.html')

with open(PAPERS_JSON, 'r', encoding='utf-8') as f:
    papers_data = json.load(f)

history_data = []
if os.path.exists(HISTORY_JSON):
    with open(HISTORY_JSON, 'r', encoding='utf-8') as f:
        history_data = json.load(f)

papers_json = json.dumps(papers_data, ensure_ascii=False, indent=2)
history_json = json.dumps(history_data, ensure_ascii=False, indent=2)

# Build category classification
CATEGORIES = {
    "VQA & Visual": {"keywords": ["vqa", "visual question", "visual reasoning", "visual entailment", "image reasoning", "spatial reasoning", "scene understanding"], "icon": "📊"},
    "Chain-of-Thought": {"keywords": ["chain of thought", "cot", "science qa", "step-by-step", "reasoning chain", "explainable", "thought chains", "explanation"], "icon": "🔗"},
    "Document & Chart": {"keywords": ["document", "chart", "diagram", "infographic", "table", "ocr", "document understanding", "layout"], "icon": "📈"},
    "Video Understanding": {"keywords": ["video", "temporal", "action recognition", "frame", "motion", "pose", "camera", "streaming", "tracking"], "icon": "🎬"},
    "Embodied & Nav": {"keywords": ["navigation", "vln", "embodied", "robot", "manipulation", "gesture", "agent", "habitat", "action model", "visuomotor"], "icon": "🤖"},
    "Math & Geometry": {"keywords": ["math", "mathematical", "geometry", "arithmetic", "numeric", "algebra", "calculation", "equation"], "icon": "🧮"},
    "Cross-Modal Gen": {"keywords": ["generation", "image generation", "text-to-image", "cross-modal", "image editing", "video generation", "synthesis", "diffusion", "controlled generation"], "icon": "🎨"},
}
def classify_paper(title, summary):
    text = (title + " " + summary).lower()
    results = []
    for cat_name, cat_info in CATEGORIES.items():
        score = sum(1 for kw in cat_info["keywords"] if kw in text)
        if score > 0:
            results.append((score, cat_name, cat_info["icon"]))
    results.sort(key=lambda x: -x[0])
    if not results:
        return [("Other", "📌")]
    top_score = results[0][0]
    return [(name, icon) for score, name, icon in results if score >= top_score * 0.4]

cat_counts = {}
for p in papers_data.get("papers", []):
    cats = classify_paper(p.get("title", ""), p.get("summary", ""))
    for cat_name, icon in cats:
        if cat_name not in cat_counts:
            cat_counts[cat_name] = {"count": 0, "icon": icon}
        cat_counts[cat_name]["count"] += 1
cat_json = json.dumps(cat_counts, ensure_ascii=False)


# Build paper cards
cards = []
for i, p in enumerate(papers_data.get('papers', [])):
    tags = ''.join([f'<span class="tag category">{c}</span>' for c in p.get('categories', [])])
    analysis = ''
    if p.get('analysis'):
        analysis = '<div class="analysis-section"><div class="analysis-header"><span class="analysis-icon">💡</span><span class="analysis-label">论文解读</span></div><div class="analysis-content">' + p['analysis'].replace('\n', '<br>') + '</div></div>'
    aid = p.get('id', '')
    pdf = f"https://arxiv.org/pdf/{aid}" if aid and (aid.replace('.', '').isdigit() or 'arxiv' in aid.lower()) else p.get('link', '#')
    s = p.get('summary', '') or '暂无摘要'
    cards.append(f'''<article class="paper-card" data-title="{p.get('title','').lower()}" data-authors="{p.get('authors','').lower()}">
    <div class="paper-accent-bar"></div>
    <div class="paper-main">
        <div class="paper-header">
            <div class="paper-header-top"><span class="paper-number">{i+1}</span><h2 class="paper-title">{p.get('title','Unknown')}</h2></div>
            <div class="paper-meta"><span class="meta-item"><span class="meta-icon">👤</span> {p.get('authors','Unknown')}</span><span class="meta-item"><span class="meta-icon">📅</span> {p.get('date','N/A')}</span><span class="meta-item"><span class="meta-icon">🏷️</span> {aid or 'N/A'}</span></div>
            <div class="tags">{tags}</div>
        </div>
        <div class="paper-body">
            <div class="paper-abstract">
                <div class="abstract-header"><span class="abstract-icon">📝</span><span class="abstract-label">摘要</span></div>
                <div class="abstract-content" id="abstract-{i}">{s}</div>
                <button class="abstract-toggle" onclick="toggleAbstract({i})"><span class="toggle-text">展开</span><span class="toggle-icon">▼</span></button>
            </div>
            {analysis}
        </div>
        <div class="paper-actions">
            <a href="{p.get('link','#')}" target="_blank" class="btn btn-primary"><span>📄</span> 查看原文</a>
            <a href="{pdf}" target="_blank" class="btn btn-secondary"><span>📥</span> PDF</a>
        </div>
    </div>
</article>''')

cards_html = '\n'.join(cards)

# History
hist_items = []
for e in history_data:
    ts = ''.join([f'<div class="history-title">{t}</div>' for t in e.get('titles', [])])
    hist_items.append(f'''<div class="history-item" data-date="{e['date']}">
    <div class="history-date">📅 {e['date']}</div><div class="history-count">共 {e.get('count',0)} 篇论文</div><div class="history-titles">{ts}</div>
</div>''')
history_html = '\n'.join(hist_items)

# Stats
tc = papers_data.get('total_count', len(papers_data.get('papers', [])))
pc = len(papers_data.get('papers', []))
stats = f'''<div class="stats-bar" id="stats-bar">
    <div class="stat-card"><div class="stat-icon">📄</div><div class="stat-number" id="stat-today">{pc}</div><div class="stat-label">今日论文</div></div>
    <div class="stat-card"><div class="stat-icon">📚</div><div class="stat-number" id="stat-total">{tc}</div><div class="stat-label">累计推送</div></div>
    <div class="stat-card clickable" id="stat-card-days" onclick="toggleStatsDetail()"><div class="stat-icon">🏷️</div><div class="stat-number" id="stat-cats">-</div><div class="stat-label">覆盖领域 <span style="font-size:0.7rem;opacity:0.6;">▸</span></div></div>
</div>'''

CSS = '''<style>
:root {
    --primary: #1e3a5f; --primary-light: #2c5282; --secondary: #4a5568;
    --accent: #dd6b20; --accent-light: #ed8936; --accent-soft: #fff5eb;
    --text: #2d3748; --text-light: #718096; --text-muted: #a0aec0;
    --bg: #f7fafc; --card-bg: #ffffff; --border: #e2e8f0; --border-light: #edf2f7;
    --shadow: 0 1px 3px rgba(0,0,0,0.06); --shadow-md: 0 4px 6px rgba(0,0,0,0.05);
    --shadow-hover: 0 20px 40px rgba(0,0,0,0.1);
    --radius-sm: 8px; --radius-md: 12px; --radius-lg: 16px;
    --transition: all 0.25s cubic-bezier(0.4,0,0.2,1);
}
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:'Noto Sans SC',-apple-system,BlinkMacSystemFont,sans-serif; background:var(--bg); color:var(--text); line-height:1.7; -webkit-font-smoothing:antialiased; }
header { background:linear-gradient(135deg,var(--primary) 0%,#0f2744 100%); color:white; padding:4rem 0 3.5rem; text-align:center; position:relative; overflow:hidden; }
header::before { content:''; position:absolute; top:-30%; right:-5%; width:400px; height:400px; background:radial-gradient(circle,rgba(221,107,32,0.15) 0%,transparent 70%); border-radius:50%; }
header::after { content:''; position:absolute; bottom:-20%; left:-10%; width:300px; height:300px; background:radial-gradient(circle,rgba(255,255,255,0.05) 0%,transparent 70%); border-radius:50%; }
header h1 { font-family:'Noto Serif SC',serif; font-size:2.8rem; font-weight:700; margin-bottom:0.75rem; position:relative; letter-spacing:-0.02em; }
header .subtitle { font-size:1.15rem; opacity:0.85; font-weight:300; letter-spacing:0.02em; }
header .date { display:inline-block; margin-top:1.25rem; padding:0.5rem 1.75rem; background:rgba(255,255,255,0.12); backdrop-filter:blur(10px); border-radius:50px; font-size:0.95rem; border:1px solid rgba(255,255,255,0.10); }
nav { background:rgba(255,255,255,0.95); backdrop-filter:blur(20px); border-bottom:1px solid var(--border-light); padding:0.875rem 0; position:sticky; top:0; z-index:100; box-shadow:var(--shadow); }
.nav-container { max-width:1100px; margin:0 auto; padding:0 2rem; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:1rem; }
.nav-links { display:flex; gap:0.5rem; background:var(--bg); padding:0.375rem; border-radius:50px; }
.nav-links a { color:var(--text-light); text-decoration:none; font-weight:500; font-size:0.9rem; transition:var(--transition); cursor:pointer; padding:0.5rem 1.25rem; border-radius:50px; border:none; background:transparent; }
.nav-links a:hover { color:var(--text); background:rgba(255,255,255,0.8); }
.nav-links a.active { color:white; background:var(--primary); box-shadow:0 2px 8px rgba(30,58,95,0.3); }
.search-box { display:flex; align-items:center; background:var(--bg); border-radius:50px; padding:0.6rem 1.25rem; border:2px solid transparent; transition:var(--transition); min-width:260px; }
.search-box:focus-within { border-color:var(--accent-light); background:white; box-shadow:0 0 0 4px rgba(221,107,32,0.10); }
.search-box input { border:none; background:none; outline:none; font-family:inherit; width:100%; font-size:0.9rem; color:var(--text); }
.search-box input::placeholder { color:var(--text-muted); }
.search-box .search-icon { color:var(--text-muted); margin-right:0.5rem; }
.container { max-width:1100px; margin:0 auto; padding:2rem; }
.stats-bar { display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:1rem; margin-bottom:2.5rem; }
.stat-card { background:var(--card-bg); padding:1.5rem 1rem; border-radius:var(--radius-md); box-shadow:var(--shadow); text-align:center; transition:var(--transition); border:1px solid var(--border-light); }
.stat-card:hover { transform:translateY(-3px); box-shadow:var(--shadow-md); }
.stat-icon { font-size:1.75rem; margin-bottom:0.5rem; }
.stat-number { font-size:2rem; font-weight:700; color:var(--primary); line-height:1; }
.stat-label { color:var(--text-light); font-size:0.85rem; margin-top:0.4rem; font-weight:500; }
.stat-card.clickable { cursor:pointer; }
.stat-card.clickable:hover { border-color:var(--accent-light); }
.history-search-results { background:var(--card-bg); border-radius:var(--radius-md); padding:1.25rem 1.5rem; box-shadow:var(--shadow); border:1px solid var(--border-light); margin-top:1.5rem; }
.history-search-results h3 { font-size:0.95rem; color:var(--accent); margin-bottom:0.75rem; font-weight:600; }
.history-search-item { padding:0.5rem 0; border-bottom:1px solid var(--border-light); font-size:0.88rem; }
.history-search-item:last-child { border-bottom:none; }
.history-search-item .hs-title { color:var(--primary); font-weight:500; }
.history-search-item .hs-meta { color:var(--text-light); font-size:0.8rem; margin-top:0.2rem; }
.stats-detail { background:var(--card-bg); border-radius:var(--radius-md); padding:1.5rem; box-shadow:var(--shadow); border:1px solid var(--border-light); margin-top:1.5rem; display:none; }
.stats-detail.show { display:block; }
.stats-detail h3 { color:var(--primary); font-size:1.1rem; margin-bottom:1rem; font-weight:600; }
.stats-detail .timeline { display:flex; flex-direction:column; gap:0.6rem; }
.stats-detail .tl-row { display:flex; align-items:center; gap:0.75rem; font-size:0.88rem; }
.stats-detail .tl-date { color:var(--accent); font-weight:600; min-width:85px; }
.stats-detail .tl-count { color:var(--text-light); }
.stats-detail .tl-bar { flex:1; height:6px; background:var(--border-light); border-radius:3px; overflow:hidden; }
.stats-detail .tl-fill { height:100%; background:var(--accent); border-radius:3px; transition:width 0.5s ease; }
.papers-grid { display:grid; gap:1.5rem; }
.paper-card { background:var(--card-bg); border-radius:var(--radius-lg); box-shadow:var(--shadow); overflow:hidden; transition:var(--transition); border:1px solid var(--border-light); display:flex; }
.paper-card:hover { box-shadow:var(--shadow-hover); transform:translateY(-3px); }
.paper-card.hidden { display:none; }
.paper-accent-bar { width:4px; background:linear-gradient(180deg,var(--accent) 0%,var(--accent-light) 100%); flex-shrink:0; }
.paper-main { flex:1; min-width:0; }
.paper-header { padding:1.5rem 2rem 1rem; background:linear-gradient(135deg,#fafbfc 0%,#f7f8fa 100%); border-bottom:1px solid var(--border-light); }
.paper-header-top { display:flex; align-items:flex-start; gap:0.875rem; }
.paper-number { display:inline-flex; align-items:center; justify-content:center; width:36px; height:36px; background:linear-gradient(135deg,var(--accent) 0%,var(--accent-light) 100%); color:white; border-radius:10px; font-weight:700; font-size:0.95rem; flex-shrink:0; box-shadow:0 2px 8px rgba(221,107,32,0.3); }
.paper-title { font-family:'Noto Serif SC',serif; font-size:1.25rem; font-weight:600; color:var(--primary); line-height:1.5; flex:1; }
.paper-meta { display:flex; gap:1.25rem; margin-top:0.875rem; flex-wrap:wrap; padding-left:2.75rem; }
.meta-item { font-size:0.82rem; color:var(--text-light); display:flex; align-items:center; gap:0.35rem; }
.meta-icon { opacity:0.7; }
.tags { display:flex; gap:0.5rem; flex-wrap:wrap; margin-top:0.75rem; padding-left:2.75rem; }
.tag { padding:0.3rem 0.85rem; background:var(--accent-soft); color:var(--accent); border-radius:50px; font-size:0.78rem; font-weight:600; letter-spacing:0.02em; }
.tag.category { background:#edf2f7; color:var(--secondary); }
.paper-body { padding:1.5rem 2rem; }
.paper-abstract { margin-bottom:1rem; }
.abstract-header { display:flex; align-items:center; gap:0.5rem; margin-bottom:0.75rem; }
.abstract-icon { font-size:1rem; }
.abstract-label { font-weight:600; color:var(--primary); font-size:0.95rem; }
.abstract-content { color:var(--text); line-height:1.85; font-size:0.92rem; max-height:120px; overflow:hidden; position:relative; transition:max-height 0.4s ease; }
.abstract-content.expanded { max-height:2000px; }
.abstract-content::after { content:''; position:absolute; bottom:0; left:0; right:0; height:40px; background:linear-gradient(transparent,white); transition:opacity 0.3s; }
.abstract-content.expanded::after { opacity:0; }
.abstract-toggle { display:inline-flex; align-items:center; gap:0.35rem; margin-top:0.75rem; padding:0.4rem 1rem; background:transparent; border:1px solid var(--border); border-radius:50px; color:var(--text-light); font-size:0.82rem; font-weight:500; cursor:pointer; transition:var(--transition); font-family:inherit; }
.abstract-toggle:hover { border-color:var(--accent-light); color:var(--accent); background:var(--accent-soft); }
.toggle-icon { transition:transform 0.3s; font-size:0.75rem; }
.abstract-toggle.expanded .toggle-icon { transform:rotate(180deg); }
.analysis-section { background:linear-gradient(135deg,#fff9f5 0%,#fff5ed 100%); border:1px solid #fed7aa; border-radius:var(--radius-md); padding:1.25rem 1.5rem; margin-top:1.25rem; }
.analysis-header { display:flex; align-items:center; gap:0.5rem; margin-bottom:0.75rem; }
.analysis-icon { font-size:1.1rem; }
.analysis-label { font-weight:700; color:var(--accent); font-size:0.95rem; }
.analysis-content { color:var(--text); line-height:1.85; font-size:0.9rem; }
.paper-actions { display:flex; gap:0.875rem; padding:1rem 2rem; background:#fafbfc; border-top:1px solid var(--border-light); }
.btn { padding:0.6rem 1.25rem; border-radius:var(--radius-sm); text-decoration:none; font-size:0.88rem; font-weight:600; transition:var(--transition); display:inline-flex; align-items:center; gap:0.4rem; border:none; cursor:pointer; font-family:inherit; letter-spacing:0.01em; }
.btn-primary { background:linear-gradient(135deg,var(--accent) 0%,var(--accent-light) 100%); color:white; box-shadow:0 2px 8px rgba(221,107,32,0.3); }
.btn-primary:hover { transform:translateY(-1px); box-shadow:0 4px 12px rgba(221,107,32,0.4); }
.btn-secondary { background:white; color:var(--text); border:1px solid var(--border); }
.btn-secondary:hover { border-color:var(--accent-light); color:var(--accent); background:var(--accent-soft); }
footer { text-align:center; padding:3rem 2rem; color:var(--text-light); border-top:1px solid var(--border-light); margin-top:3rem; background:white; }
footer a { color:var(--accent); text-decoration:none; font-weight:500; }
footer a:hover { text-decoration:underline; }
.page-section { display:none; }
.page-section.active { display:block; }
.history-list { display:grid; gap:1rem; }
.history-item { background:var(--card-bg); border-radius:var(--radius-md); padding:1.5rem; box-shadow:var(--shadow); border:1px solid var(--border-light); cursor:pointer; transition:var(--transition); }
.history-item:hover { box-shadow:var(--shadow-md); transform:translateY(-2px); border-color:var(--accent-light); }
.history-date { font-weight:700; color:var(--primary); font-size:1.1rem; margin-bottom:0.4rem; }
.history-count { color:var(--text-light); font-size:0.88rem; margin-bottom:0.75rem; font-weight:500; }
.history-titles { display:flex; flex-direction:column; gap:0.4rem; }
.history-title { font-size:0.88rem; color:var(--text); padding-left:1.25rem; position:relative; line-height:1.5; }
.history-title::before { content:''; position:absolute; left:0.25rem; top:0.5rem; width:6px; height:6px; background:var(--accent); border-radius:50%; }
.about-content { background:var(--card-bg); border-radius:var(--radius-lg); padding:2.5rem; box-shadow:var(--shadow); border:1px solid var(--border-light); max-width:800px; margin:0 auto; }
.about-content h2 { font-family:'Noto Serif SC',serif; color:var(--primary); margin-bottom:1.25rem; font-size:1.7rem; }
.about-content h3 { color:var(--accent); margin-top:1.75rem; margin-bottom:0.75rem; font-size:1.15rem; font-weight:600; }
.about-content p { margin-bottom:1rem; line-height:1.8; }
.about-content ul { margin-left:1.5rem; margin-bottom:1rem; }
.about-content li { margin-bottom:0.5rem; line-height:1.7; }
.about-content code { background:var(--bg); padding:0.2rem 0.5rem; border-radius:4px; font-size:0.9rem; color:var(--accent); font-weight:600; }
.about-content a { color:var(--accent); text-decoration:none; font-weight:500; }
.about-content a:hover { text-decoration:underline; }
.search-results-info { text-align:center; padding:1rem; color:var(--text-light); font-size:0.9rem; margin-bottom:1rem; }
.search-results-info .highlight { color:var(--accent); font-weight:700; }
.empty-state { text-align:center; padding:4rem 2rem; color:var(--text-light); }
.empty-state-icon { font-size:4rem; margin-bottom:1rem; opacity:0.5; }
@media (max-width:768px) {
    header { padding:2.5rem 0 2rem; } header h1 { font-size:2rem; }
    .nav-container { flex-direction:column; align-items:stretch; }
    .nav-links { justify-content:center; }
    .search-box { width:100%; min-width:unset; }
    .paper-header,.paper-body { padding:1.25rem; }
    .paper-title { font-size:1.1rem; }
    .paper-meta { padding-left:0; } .tags { padding-left:0; }
    .paper-actions { flex-wrap:wrap; padding:1rem 1.25rem; }
    .about-content { padding:1.5rem; }
    .container { padding:1.25rem; }
}
</style>'''

html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>每日论文推送 - 多模态推理</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;600;700&family=Noto+Sans+SC:wght@300;400;500;700&display=swap" rel="stylesheet">
{CSS}
</head>
<body>
<header>
    <h1>📚 每日论文推送</h1>
    <p class="subtitle">多模态推理 (Multimodal Reasoning) 领域最新研究</p>
    <div class="date" id="header-date">{papers_data.get('date', '')}</div>
</header>
<nav>
    <div class="nav-container">
        <div class="nav-links">
            <a href="#" class="active" data-page="today">今日推送</a>
            <a href="#" data-page="history">历史记录</a>
            <a href="#" data-page="about">关于</a>
        </div>
        <div class="search-box">
            <span class="search-icon">🔍</span>
            <input type="text" placeholder="搜索论文标题、作者..." id="search-input">
        </div>
    </div>
</nav>
<main class="container">
    {stats}
    <div class="page-section active" id="page-today">
        <div id="search-info" class="search-results-info" style="display:none;"></div>
        <div class="stats-detail" id="stats-detail"><h3>📊 推送时间线</h3><div class="timeline" id="stats-timeline"></div></div>
        <div class="papers-grid" id="papers-container">{cards_html}</div>
    </div>
    <div class="page-section" id="page-history">
        <div class="history-list" id="history-container">{history_html}</div>
    </div>
    <div class="page-section" id="page-about">
        <div class="about-content">
            <h2>关于每日论文推送</h2>
            <p>这是一个自动化论文推送系统，每天定时搜索并推送多模态推理 (Multimodal Reasoning) 领域的最新 arXiv 论文。</p>
            <h3>🎯 功能特性</h3>
            <ul><li><strong>自动推送</strong>：每天上午 9:00 自动获取最新论文</li><li><strong>多层降级</strong>：arXiv API → Semantic Scholar → DeepSeek API，确保稳定获取</li><li><strong>论文解读</strong>：使用 AI 对每篇论文进行深度解读</li><li><strong>历史记录</strong>：查看过往推送记录</li><li><strong>在线搜索</strong>：实时搜索论文标题和作者</li></ul>
            <h3>🔧 技术栈</h3>
            <ul><li>前端：原生 HTML + CSS + JavaScript</li><li>部署：GitHub Pages</li><li>数据源：arXiv API / Semantic Scholar API / DeepSeek API</li><li>推送：飞书机器人</li></ul>
            <h3>📁 项目结构</h3>
            <ul><li><code>index.html</code> - 网页主体</li><li><code>papers.json</code> - 当日论文数据</li><li><code>history.json</code> - 历史推送记录</li></ul>
            <h3>🔗 相关链接</h3>
            <ul><li>GitHub 仓库：<a href="https://github.com/LGSA-code/daily-paper-push" target="_blank">LGSA-code/daily-paper-push</a></li><li>arXiv 搜索：<a href="https://arxiv.org/search/?query=multimodal+reasoning" target="_blank">arxiv.org</a></li></ul>
            <h3>👤 关于作者</h3>
            <p>由 <strong>栗子 (Hermes Agent)</strong> 自动生成和维护。</p>
            <p>如有问题或建议，欢迎通过飞书联系。</p>
        </div>
    </div>
</main>
<footer>
    <p>由 <a href="#" onclick="showPage('about');return false;">栗子 (Hermes Agent)</a> 自动生成 · 数据来自 arXiv</p>
    <p style="margin-top:0.5rem;font-size:0.85rem;opacity:0.8;">每日上午 9:00 自动更新</p>
</footer>
<script>
const papersData = {papers_json};
const historyData = {history_json};
const catData = {cat_json};
function showPage(n) {{
    document.querySelectorAll('.page-section').forEach(s=>s.classList.remove('active'));
    var t=document.getElementById('page-'+n);if(t)t.classList.add('active');
    document.querySelectorAll('.nav-links a').forEach(l=>{{l.classList.remove('active');if(l.dataset.page===n)l.classList.add('active')}});
    var sb=document.getElementById('stats-bar');if(sb)sb.style.display=n==='today'?'grid':'none';
    window.scrollTo({{top:0,behavior:'smooth'}});
}}
document.querySelectorAll('.nav-links a').forEach(l=>l.addEventListener('click',function(e){{e.preventDefault();showPage(this.dataset.page)}}));
function toggleAbstract(i) {{
    var c=document.getElementById('abstract-'+i);var b=c.parentElement.querySelector('.abstract-toggle');var t=b.querySelector('.toggle-text');
    if(c.classList.contains('expanded')){{c.classList.remove('expanded');b.classList.remove('expanded');t.textContent='展开'}}
    else{{c.classList.add('expanded');b.classList.add('expanded');t.textContent='收起'}}
}}
function setupSearch() {{
    var inp=document.getElementById('search-input');var inf=document.getElementById('search-info');
    var histDiv=document.getElementById('history-search-results');
    inp.addEventListener('input',function(e) {{
        var kw=e.target.value.toLowerCase().trim();
        var cards=document.querySelectorAll('.paper-card');
        if(!kw){{cards.forEach(c=>c.classList.remove('hidden'));inf.style.display='none';if(histDiv)histDiv.style.display='none';return;}}
        // Search today's cards
        var v=0;cards.forEach(c=>{{var m=c.dataset.title.includes(kw)||c.dataset.authors.includes(kw)||c.textContent.toLowerCase().includes(kw);if(m){{c.classList.remove('hidden');v++}}else c.classList.add('hidden')}});
        // Search history
        var hResults=[];
        historyData.forEach(function(day){{
            day.titles.forEach(function(t,i){{
                if(t.toLowerCase().includes(kw)){{
                    hResults.push({{title:t,date:day.date,count:day.count}});
                }}
            }});
        }});
        var parts=['找到 <span class="highlight">'+v+'</span> 篇相关论文（今日推送）'];
        if(hResults.length>0){{
            parts.push('，历史记录中还有 <span class="highlight">'+hResults.length+'</span> 篇');
            // Show history results section
            if(!histDiv){{
                histDiv=document.createElement('div');
                histDiv.id='history-search-results';
                histDiv.className='history-search-results';
                document.getElementById('papers-container').after(histDiv);
            }}
            var hHtml='<h3>📅 历史记录中的匹配结果</h3>';
            hResults.forEach(function(r){{hHtml+='<div class="history-search-item"><div class="hs-title">'+r.title+'</div><div class="hs-meta">📅 '+r.date+'</div></div>'}});
            histDiv.innerHTML=hHtml;
            histDiv.style.display='block';
        }}else{{if(histDiv)histDiv.style.display='none';}}
        inf.style.display='block';inf.innerHTML=parts.join('');
        if(!document.getElementById('page-today').classList.contains('active'))showPage('today');
    }});
}}
function updateStats() {{
    document.getElementById('stat-today').textContent=papersData.papers?papersData.papers.length:0;
    document.getElementById('stat-total').textContent=historyData.reduce((s,h)=>s+(h.count||0),0);
    document.getElementById('stat-cats').textContent=Object.keys(catData).length;
    document.getElementById('header-date').textContent=papersData.date||new Date().toISOString().split('T')[0];
    // Build timeline for stats detail
    var maxC=Math.max(1,...historyData.map(h=>h.count||0));
    var tl=document.getElementById('stats-timeline');
    if(tl){{
        var catKeys=Object.keys(catData).sort((a,b)=>catData[b].count-catData[a].count);
        var html='<h3>📊 覆盖领域</h3>';
        catKeys.forEach(function(c){{
            var d=catData[c];
            html+='<div class="tl-row"><span class="tl-date">'+d.icon+' '+c+'</span><span class="tl-count">'+d.count+' 篇</span><div class="tl-bar"><div class="tl-fill" style="width:'+(100*d.count/papersData.papers.length)+'%"></div></div></div>';
        }});
        html+='<h3 style="margin-top:1.25rem;">📅 推送时间线</h3>';
        html+=historyData.map(h=>'<div class="tl-row"><span class="tl-date">📅 '+h.date+'</span><span class="tl-count">'+h.count+' 篇</span><div class="tl-bar"><div class="tl-fill" style="width:'+(100*(h.count||0)/maxC)+'%"></div></div></div>').join('');
        tl.innerHTML=html;
    }}
}}
function toggleStatsDetail() {{
    var d=document.getElementById('stats-detail');
    if(!d)return;
    var btn=document.getElementById('stat-card-days');
    if(d.classList.contains('show')){{d.classList.remove('show');if(btn)btn.style.borderColor='';}}
    else{{d.classList.add('show');if(btn)btn.style.borderColor='var(--accent-light)';}}
}}
function init(){{setupSearch();updateStats();}}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
</script>
</body>
</html>'''

with open(INDEX_HTML, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"OK: {os.path.getsize(INDEX_HTML):,} bytes → {INDEX_HTML}")
