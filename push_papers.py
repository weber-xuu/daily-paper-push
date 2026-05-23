#!/usr/bin/env python3
"""
每日论文推送脚本
推送多模态推理领域的最新论文到飞书 + 生成网页 + 论文解读
使用 arxiv skill 的搜索功能
"""

import urllib.request
import urllib.parse
import json
import os
import sys
import subprocess
import time
from datetime import datetime

# 加载 .env 文件
def extract_paper_figures(arxiv_id):
    """从 arXiv HTML 版本提取论文前 2 张图片（通常是框架图）"""
    if not arxiv_id:
        return []
    
    import re
    figures = []
    
    # 尝试多个 HTML 源
    html_urls = [
        (f"https://arxiv.org/html/{arxiv_id}", f"https://arxiv.org/html/{arxiv_id}"),
        (f"https://ar5iv.labs.arxiv.org/html/{arxiv_id}", f"https://ar5iv.labs.arxiv.org/html/{arxiv_id}"),
    ]
    
    for html_url, base_url in html_urls:
        try:
            req = urllib.request.Request(
                html_url,
                headers={"User-Agent": "Mozilla/5.0 (compatible; HermesBot/1.0)"}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status != 200:
                    continue
                html = resp.read().decode('utf-8', errors='replace')
            
            # 找 <figure> 标签
            figure_blocks = re.findall(
                r'<figure[^>]*>(.*?)</figure>',
                html, re.DOTALL | re.IGNORECASE
            )
            
            count = 0
            for fig_html in figure_blocks:
                if count >= 2:
                    break
                # 提取 img src
                img_match = re.search(r'<img[^>]+src="([^"]+)"', fig_html, re.IGNORECASE)
                if not img_match:
                    continue
                img_src = img_match.group(1)
                if img_src.startswith('data:'):
                    continue
                
                # 处理相对路径
                if img_src.startswith('/'):
                    img_src = base_url.rstrip('/') + img_src
                elif not img_src.startswith('http'):
                    img_src = base_url.rstrip('/') + '/' + img_src
                
                # 提取 caption
                cap_match = re.search(r'<figcaption[^>]*>(.*?)</figcaption>', fig_html, re.DOTALL | re.IGNORECASE)
                caption = ''
                if cap_match:
                    caption = re.sub(r'<[^>]+>', '', cap_match.group(1)).strip()
                    caption = re.sub(r'\s+', ' ', caption)[:200]
                
                figures.append({
                    "url": img_src,
                    "caption": caption or f"Figure {count+1}"
                })
                count += 1
            
            if figures:
                break  # 成功获取了图片，不再尝试其他源
                
        except Exception:
            continue
    
    return figures


def load_env_file():
    env_file = os.path.expanduser("~/.hermes/.env")
    if os.path.exists(env_file):
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key.strip(), value.strip())

load_env_file()

# ============ 配置 ============
PAPER_DOMAIN = os.environ.get("PAPER_DOMAIN", "multimodal reasoning")
PAPER_COUNT = int(os.environ.get("PAPER_COUNT", "5"))
FEISHU_APP_ID = os.environ.get("FEISHU_APP_ID", "")
FEISHU_APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "")
TARGET_USER = os.environ.get("PAPER_TARGET_USER", "ou_becaaa9a41aec605926a9c5b660f6a2b")

# arxiv skill 脚本路径
ARXIV_SCRIPT = os.path.expanduser("~/.hermes/skills/research/arxiv/scripts/search_arxiv.py")
WEB_DIR = os.path.expanduser("~/.hermes/skills/research/daily-paper-push/web")
PAPERS_JSON = os.path.join(WEB_DIR, "papers.json")
HISTORY_JSON = os.path.join(WEB_DIR, "history.json")

# LLM 解读配置
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_API_URL = os.environ.get("LLM_API_URL", "https://api.openai.com/v1/chat/completions")
LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-4o-mini")


def get_feishu_token():
    """获取飞书 tenant_access_token"""
    if not FEISHU_APP_ID or not FEISHU_APP_SECRET:
        raise ValueError("FEISHU_APP_ID 和 FEISHU_APP_SECRET 未配置")
    
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    data = json.dumps({"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    
    with urllib.request.urlopen(req, timeout=10) as response:
        result = json.loads(response.read())
        token = result.get("tenant_access_token", "")
        if not token:
            raise ValueError(f"获取 token 失败: {result}")
        return token


def search_papers_via_arxiv_skill():
    """使用 arxiv skill 搜索论文（带重试）"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            cmd = [
                sys.executable, ARXIV_SCRIPT,
                PAPER_DOMAIN,
                "--max", str(PAPER_COUNT),
                "--sort", "date"
            ]
            
            print(f"执行命令: {' '.join(cmd)} (attempt {attempt + 1}/{max_retries})")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                papers = parse_arxiv_output(result.stdout)
                if papers:
                    return papers
                print("arxiv skill 返回空结果")
            else:
                print(f"arxiv skill 搜索失败: {result.stderr}")
                
            # 如果失败且不是最后一次，等待后重试
            if attempt < max_retries - 1:
                wait = 5 * (attempt + 1)
                print(f"等待 {wait} 秒后重试...")
                time.sleep(wait)
                
        except subprocess.TimeoutExpired:
            print("arxiv skill 搜索超时")
        except Exception as e:
            print(f"arxiv skill 调用失败: {e}")
    
    return []


def search_papers_via_semantic_scholar():
    """使用 Semantic Scholar API 作为备用源"""
    try:
        query = urllib.parse.quote(PAPER_DOMAIN)
        url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={query}&fields=title,authors,year,abstract,externalIds,url&limit={PAPER_COUNT}&sort=publicationDate:desc"
        
        print(f"尝试 Semantic Scholar API...")
        req = urllib.request.Request(url, headers={'User-Agent': 'HermesAgent/1.0'})
        
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            papers = data.get('data', [])
            
            if not papers:
                print("Semantic Scholar 返回空结果")
                return []
            
            results = []
            for p in papers:
                authors_list = p.get('authors', [])
                authors = ', '.join(a.get('name', '') for a in authors_list[:5])
                
                # 获取 arXiv ID
                external = p.get('externalIds', {})
                arxiv_id = external.get('ArXiv', '')
                
                paper = {
                    "title": p.get('title', 'Unknown'),
                    "id": arxiv_id or p.get('paperId', 'unknown'),
                    "date": str(p.get('year', datetime.now().year)),
                    "authors": authors or 'Unknown',
                    "summary": p.get('abstract') or '',
                    "link": f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else (p.get('url') or ''),
                    "categories": []
                }
                results.append(paper)
            
            print(f"✓ Semantic Scholar 获取 {len(results)} 篇论文")
            return results
            
    except urllib.error.HTTPError as e:
        if e.code == 429:
            print("Semantic Scholar API 也被限流 (429)")
        else:
            print(f"Semantic Scholar API HTTP 错误: {e.code}")
        return []
    except Exception as e:
        print(f"Semantic Scholar API 调用失败: {e}")
        return []


def search_papers_via_llm():
    """使用 DeepSeek API 检索顶级会议论文作为最终备用源"""
    if not LLM_API_KEY:
        print("未配置 LLM API，跳过 LLM 论文检索")
        return []
    
    try:
        print("尝试使用 DeepSeek API 检索论文...")
        
        prompt = f"""你是一位资深的学术文献检索专家。请严格按以下要求检索关于「{PAPER_DOMAIN}」领域的最新学术论文：

## 检索要求

1. **时间范围**：优先推荐 2024-2025 年的论文，最多包含 1-2 篇 2023 年的经典/高引论文
2. **会议/期刊来源**：优先从以下顶级会议/期刊中选择：
   - 机器学习：NeurIPS, ICML, ICLR
   - 计算机视觉：CVPR, ICCV, ECCV
   - NLP：ACL, EMNLP, NAACL
   - AI 综合：AAAI, IJCAI
   - 多模态：MM (ACM Multimedia)
3. **真实性**：只推荐真实存在的论文，不要编造
4. **多样性**：尽量覆盖不同会议/角度，避免同一作者的论文过多

## 输出格式

对每篇论文，请严格按以下格式输出：

[序号]. [论文标题]
   Authors: [作者1], [作者2], ...
   Venue: [会议/期刊名] [年份]
   Date: [发表时间，格式 YYYY-MM 或 YYYY]
   Abstract: [摘要，200-300字]
   Link: [论文链接，优先 arXiv 链接，或 OpenReview/官方链接]

请确保输出 {PAPER_COUNT} 篇论文。"""

        data = json.dumps({
            "model": LLM_MODEL,
            "messages": [
                {"role": "system", "content": "你是一位学术论文检索专家，熟悉 NeurIPS, ICML, ICLR, CVPR, ICCV, ECCV, ACL, EMNLP, AAAI 等顶级会议的最新研究。你只推荐真实存在的论文，绝不编造。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 3000
        }).encode()
        
        req = urllib.request.Request(LLM_API_URL, data=data, headers={
            "Authorization": f"Bearer {LLM_API_KEY}",
            "Content-Type": "application/json"
        }, method="POST")
        
        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read())
            content = result["choices"][0]["message"]["content"]
            
            # 解析 LLM 返回的论文列表
            papers = parse_llm_paper_output(content)
            if papers:
                print(f"✓ DeepSeek API 获取 {len(papers)} 篇论文")
                return papers
            else:
                print("DeepSeek API 返回结果解析失败")
                return []
            
    except Exception as e:
        print(f"DeepSeek API 调用失败: {e}")
        return []


def parse_llm_paper_output(content):
    """解析 LLM 返回的论文文本为结构化数据"""
    papers = []
    lines = content.strip().split('\n')
    
    current_paper = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # 匹配论文标题行: "1. Title" 或 "[1]. Title" 或 "1]. Title"
        if (line[0].isdigit() or line.startswith('[')) and ('.' in line[:6] or ']' in line[:6]):
            if current_paper and current_paper.get('title'):
                papers.append(current_paper)
            
            # 提取标题 - 移除序号前缀
            title = line
            # 移除开头的 [ 或数字
            while title and (title[0].isdigit() or title[0] in '[ ]'):
                title = title[1:]
            # 移除开头的 . 
            title = title.lstrip('.').strip()
            
            current_paper = {
                "title": title,
                "id": "",
                "date": "",
                "authors": "",
                "summary": "",
                "link": "",
                "categories": [],
                "venue": ""
            }
        
        # 匹配 Authors 行
        elif line.lower().startswith("authors:") and current_paper:
            current_paper["authors"] = line.split(":", 1)[1].strip()
        
        # 匹配 Venue 行
        elif line.lower().startswith("venue:") and current_paper:
            current_paper["venue"] = line.split(":", 1)[1].strip()
            current_paper["categories"] = [current_paper["venue"]]
        
        # 匹配 Date 行
        elif line.lower().startswith("date:") and current_paper:
            current_paper["date"] = line.split(":", 1)[1].strip()
        
        # 匹配 Abstract 行
        elif line.lower().startswith("abstract:") and current_paper:
            current_paper["summary"] = line.split(":", 1)[1].strip()
        
        # 匹配 Link 行
        elif line.lower().startswith("link:") and current_paper:
            current_paper["link"] = line.split(":", 1)[1].strip()
        
        # 如果当前行不是以关键字开头，可能是上一行的续行
        elif current_paper and not any(line.lower().startswith(k) for k in ['authors:', 'venue:', 'date:', 'abstract:', 'link:']):
            # 续接摘要
            if current_paper.get("summary"):
                current_paper["summary"] += " " + line
    
    if current_paper and current_paper.get('title'):
        papers.append(current_paper)
    
    # 清理数据
    for p in papers:
        if not p.get("link"):
            p["link"] = "https://arxiv.org/search/?query=" + urllib.parse.quote(p["title"])
        if not p.get("date"):
            p["date"] = str(datetime.now().year)
        if not p.get("authors"):
            p["authors"] = "Unknown"
        if not p.get("summary"):
            p["summary"] = "暂无摘要"
        # 生成一个 ID
        if not p.get("id"):
            p["id"] = p["title"].lower().replace(' ', '-')[:30]
    
    return papers


def parse_arxiv_output(output):
    """解析 arxiv skill 的输出为结构化数据"""
    papers = []
    lines = output.strip().split('\n')
    
    current_paper = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # 匹配论文标题行
        if line[0].isdigit() and '. ' in line:
            if current_paper:
                papers.append(current_paper)
            title = line.split('. ', 1)[1].strip()
            current_paper = {
                "title": title,
                "id": "",
                "date": "",
                "authors": "",
                "summary": "",
                "link": "",
                "categories": []
            }
        
        # 匹配 ID 和日期行
        elif line.startswith("ID:") and current_paper:
            parts = line.replace("ID:", "").strip().split("|")
            id_part = parts[0].strip().split()[0]
            current_paper["id"] = id_part.split("v")[0] if "v" in id_part else id_part
            
            for part in parts:
                if "Published:" in part:
                    current_paper["date"] = part.replace("Published:", "").strip()
        
        # 匹配作者行
        elif line.startswith("Authors:") and current_paper:
            current_paper["authors"] = line.replace("Authors:", "").strip()
        
        # 匹配类别行
        elif line.startswith("Categories:") and current_paper:
            cats = line.replace("Categories:", "").strip()
            current_paper["categories"] = [c.strip() for c in cats.split(",")]
        
        # 匹配摘要行
        elif line.startswith("Abstract:") and current_paper:
            summary = line.replace("Abstract:", "").strip()
            # 只移除末尾明确标记的省略号（来自旧版脚本的截断标记）
            if summary.endswith("...") and len(summary) < 350:
                summary = summary[:-3]
            current_paper["summary"] = summary
        
        # 匹配链接行
        elif line.startswith("Links:") and current_paper:
            links = line.replace("Links:", "").strip()
            for link in links.split("|"):
                link = link.strip()
                if "arxiv.org/abs" in link:
                    current_paper["link"] = link
                    break
    
    if current_paper:
        papers.append(current_paper)
    
    return papers


def analyze_paper(paper):
    """使用 LLM 解读论文"""
    if not LLM_API_KEY:
        print(f"未配置 LLM API，跳过论文 {paper['id']} 的解读")
        return None
    
    try:
        prompt = f"""请对以下学术论文进行深度解读，用中文回答：

论文标题：{paper['title']}
作者：{paper['authors']}
摘要：{paper['summary']}

请从以下几个方面进行解读（每个方面 2-3 句话）：

1. **核心创新点**：这篇论文的主要贡献是什么？解决了什么问题？
2. **方法概述**：使用了什么方法/技术？
3. **实验结果**：主要实验结果和性能如何？
4. **意义与影响**：这项工作对领域有什么影响？
5. **局限性与未来方向**：论文提到的局限性或未来工作是什么？

请用简洁清晰的语言，适合研究人员快速理解。"""

        data = json.dumps({
            "model": LLM_MODEL,
            "messages": [
                {"role": "system", "content": "你是一位资深的学术论文解读专家，擅长用简洁清晰的语言解释复杂的学术概念。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 1500
        }).encode()
        
        req = urllib.request.Request(LLM_API_URL, data=data, headers={
            "Authorization": f"Bearer {LLM_API_KEY}",
            "Content-Type": "application/json"
        }, method="POST")
        
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read())
            analysis = result["choices"][0]["message"]["content"]
            return analysis
            
    except Exception as e:
        print(f"论文 {paper['id']} 解读失败: {e}")
        return None


def generate_web_data(papers):
    """生成网页数据文件"""
    today = datetime.now().strftime("%Y-%m-%d")
    
    # 确保目录存在
    os.makedirs(WEB_DIR, exist_ok=True)
    
    # 生成今日数据
    data = {
        "date": today,
        "domain": PAPER_DOMAIN,
        "paper_count": len(papers),
        "total_count": len(papers),
        "categories": list(set(cat for p in papers for cat in p.get("categories", []))),
        "papers": papers
    }
    
    with open(PAPERS_JSON, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"✓ 网页数据已保存: {PAPERS_JSON}")
    
    # 更新历史记录
    history = []
    if os.path.exists(HISTORY_JSON):
        try:
            with open(HISTORY_JSON, 'r', encoding='utf-8') as f:
                history = json.load(f)
        except:
            history = []
    
    # 添加今日记录
    history_entry = {
        "date": today,
        "count": len(papers),
        "titles": [p["title"] for p in papers]
    }
    
    # 去重并保留最近 30 天
    history = [h for h in history if h["date"] != today]
    history.insert(0, history_entry)
    history = history[:30]
    
    with open(HISTORY_JSON, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    
    print(f"✓ 历史记录已更新: {HISTORY_JSON}")


def generate_html(papers):
    """生成静态 HTML 网页（调用 build_v2.py 美化模板）"""
    import subprocess
    build_script = os.path.join(WEB_DIR, 'build_v2.py')
    result = subprocess.run(
        [sys.executable, build_script],
        capture_output=True, text=True,
        cwd=WEB_DIR
    )
    if result.returncode != 0:
        print(f"✗ HTML 生成失败: {result.stderr}")
    else:
        print(result.stdout.strip())


def deploy_to_github_pages():
    """自动部署到 GitHub Pages"""
    try:
        # 检查是否是 git 仓库
        git_dir = os.path.join(WEB_DIR, '.git')
        if not os.path.exists(git_dir):
            print("⚠ 未找到 git 仓库，跳过 GitHub Pages 部署")
            print(f"  请手动部署: cd {WEB_DIR} && git push origin main")
            return False
        
        # 添加所有更改
        result_add = subprocess.run(
            ['git', '-C', WEB_DIR, 'add', '.'],
            capture_output=True,
            text=True
        )
        
        # 检查是否有更改要提交
        result_status = subprocess.run(
            ['git', '-C', WEB_DIR, 'status', '--porcelain'],
            capture_output=True,
            text=True
        )
        
        if not result_status.stdout.strip():
            print("✓ 没有更改需要部署")
            return True
        
        # 提交更改
        today = datetime.now().strftime("%Y-%m-%d")
        result_commit = subprocess.run(
            ['git', '-C', WEB_DIR, 'commit', '-m', f"Update papers for {today}"],
            capture_output=True,
            text=True
        )
        
        if result_commit.returncode != 0:
            print(f"⚠ Git commit 失败: {result_commit.stderr}")
            return False
        
        # 推送到 GitHub (使用 token 鉴权)
        gh_token = os.environ.get('GITHUB_TOKEN', '')
        repo_url = 'https://weber-xuu.github.io/daily-paper-push/'
        push_url = f'https://{gh_token}@github.com/weber-xuu/daily-paper-push.git' if gh_token else repo_url
        result_push = subprocess.run(
            ['git', '-C', WEB_DIR, 'push', push_url, 'main'],
            capture_output=True,
            text=True
        )
        
        if result_push.returncode == 0:
            print("✓ GitHub Pages 部署成功！")
            print(f"  访问地址: {repo_url}")
            return True
        else:
            print(f"✗ Git push 失败: {result_push.stderr}")
            return False
            
    except Exception as e:
        print(f"✗ GitHub Pages 部署出错: {e}")
        return False


def build_message(papers_list, source="arXiv"):
    """构建推送消息"""
    today = datetime.now().strftime("%Y-%m-%d")
    msg = f"[每日多模态推理论文推送] ({today})\n"
    msg += f"来源: {source}\n\n"
    
    if papers_list:
        msg += f"共 {len(papers_list)} 篇最新论文：\n\n"
        for i, p in enumerate(papers_list, 1):
            msg += f"{i}. {p['title']}\n"
            msg += f"   作者: {p['authors']}\n"
            msg += f"   日期: {p['date']}\n"
            msg += f"   摘要: {p['summary']}...\n"
            msg += f"   链接: {p['link']}\n\n"
    else:
        msg += "今日论文获取失败，请稍后重试。\n"
    
    msg += "---\n"
    msg += "🌐 网页版: https://weber-xuu.github.io/daily-paper-push/\n"
    msg += "由栗子（Hermes Agent）自动推送"
    return msg


def send_feishu_message(token, message):
    """发送飞书消息"""
    url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id"
    data = json.dumps({
        "receive_id": TARGET_USER,
        "msg_type": "text",
        "content": json.dumps({"text": message})
    }).encode()
    
    req = urllib.request.Request(url, data=data, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    })
    
    with urllib.request.urlopen(req, timeout=10) as response:
        result = json.loads(response.read())
        return result.get("code") == 0


def main():
    """主函数"""
    print(f"[{datetime.now()}] 开始执行论文推送...")
    print(f"搜索领域: {PAPER_DOMAIN}")
    print(f"推送数量: {PAPER_COUNT}")
    
    papers_list = []
    source = ""
    
    # 第 1 层：arXiv API
    papers_list = search_papers_via_arxiv_skill()
    if papers_list:
        source = "arXiv"
        print(f"✓ 从 arXiv 成功获取 {len(papers_list)} 篇论文")
    else:
        print("⚠ arXiv 获取失败，尝试备用源...")
        
        # 第 2 层：Semantic Scholar
        papers_list = search_papers_via_semantic_scholar()
        if papers_list:
            source = "Semantic Scholar"
            print(f"✓ 从 Semantic Scholar 成功获取 {len(papers_list)} 篇论文")
        else:
            print("⚠ Semantic Scholar 也失败，尝试 DeepSeek API...")
            
            # 第 3 层：DeepSeek API 检索顶级会议论文
            papers_list = search_papers_via_llm()
            if papers_list:
                source = "DeepSeek (LLM 检索)"
                print(f"✓ 从 DeepSeek API 成功获取 {len(papers_list)} 篇论文")
    
    # 获取飞书 token（无论成功与否都需要）
    try:
        token = get_feishu_token()
        print("\n飞书 token 获取成功")
    except Exception as e:
        print(f"获取飞书 token 失败: {e}")
        return 1
    
    # 如果完全无法获取论文，发送通知告知用户
    if not papers_list:
        print("\n✗ 所有数据源均失败，发送通知消息...")
        error_msg = f"""[每日多模态推理论文推送] ({datetime.now().strftime('%Y-%m-%d')})

⚠️ 今日论文获取失败

原因：arXiv API、Semantic Scholar API 和 DeepSeek API 均无法获取论文

建议：
• 这是临时性问题，通常几小时后会自动恢复
• 您可以稍后手动访问 https://arxiv.org/list/cs.AI/recent 查看最新论文
• 明天的定时推送将自动重试

---
由栗子（Hermes Agent）自动推送"""
        try:
            if send_feishu_message(token, error_msg):
                print("✓ 已发送失败通知到飞书")
            else:
                print("✗ 发送失败通知失败")
        except Exception as e:
            print(f"发送失败通知出错: {e}")
        return 1
    
    # 2. 论文解读
    print("\n开始论文解读...")
    for i, paper in enumerate(papers_list):
        print(f"  解读第 {i+1}/{len(papers_list)} 篇: {paper['title'][:50]}...")
        analysis = analyze_paper(paper)
        if analysis:
            paper["analysis"] = analysis
            print(f"  ✓ 解读完成")
        else:
            print(f"  ✗ 解读失败或跳过")

    # 2.5 提取论文图片
    print("\n提取论文框架图...")
    for i, paper in enumerate(papers_list):
        aid = paper.get("id", "")
        if aid:
            print(f"  提取第 {i+1}/{len(papers_list)} 篇图片: {paper['title'][:40]}...")
            figures = extract_paper_figures(aid)
            if figures:
                paper["figures"] = figures
                print(f"  ✓ 获取 {len(figures)} 张图")
            else:
                print(f"  - 无图片或ar5iv不可用")

    # 3. 生成网页数据
    print("\n生成网页数据...")
    generate_web_data(papers_list)
    
    # 4. 生成静态网页
    print("生成静态网页...")
    generate_html(papers_list)
    
    # 5. 部署到 GitHub Pages
    print("\n部署到 GitHub Pages...")
    deploy_to_github_pages()
    
    # 6. 构建推送消息
    message = build_message(papers_list, source)
    
    # 7. 发送消息
    try:
        if send_feishu_message(token, message):
            print("✓ 论文推送成功！")
        else:
            print("✗ 论文推送失败")
            return 1
    except Exception as e:
        print(f"发送消息失败: {e}")
        return 1
    
    print(f"\n{'='*50}")
    print("所有任务完成！")
    print(f"数据来源: {source}")
    print(f"网页文件位置: {WEB_DIR}")
    print(f'在线网页: https://weber-xuu.github.io/daily-paper-push/')
    print(f"论文数据: {PAPERS_JSON}")
    print(f"{'='*50}")
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
