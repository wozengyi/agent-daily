# Embodied Daily · 每日具身智能论文推荐

一个本地运行 / 可部署到 GitHub Pages 的每日具身智能论文小站。

## 数据来源

- **Hugging Face Daily Papers**（最近 14 天的每日热榜）
- **arXiv**（cs.RO / cs.AI / cs.CV / cs.LG 最近提交，按具身关键词筛选）

两源合并后按 arXiv id 去重，按「当天优先 → HF 热度 → 相关性」排序，每天取 Top 60 篇。
具身关键词覆盖：embodied / robot / manipulation / grasping / humanoid / locomotion / navigation / VLA / sim2real / dexterous / bimanual / teleoperation / imitation learning / world model 等。

## 本地使用（最简单）

1. 安装 Python 3.9+（本项目构建脚本只用标准库，无需 pip 装包）。
2. 启动本地服务器：
   ```
   cd embodied-papers
   python server.py --port 8765
   ```
3. 浏览器打开 http://localhost:8765/

- 打开页面时会直接加载 `data/daily.json`（随仓库一起提交的最新数据），很快。
- 点页面底部 **🔄 刷新最新** 会实时访问 HF + arXiv 拉取最新论文（可能需要 15-40 秒，取决于 arXiv 响应）。
- **换一批经典** 轮换经典精选主卡。

## 手动更新 daily.json（不启动服务器）

```
python build/build_daily.py
```

会覆盖写入 `data/daily.json`，再刷新网页即可看到新数据。

## 部署到 GitHub Pages（每天自动更新）

把整个 `embodied-papers/` 目录作为 GitHub 仓库根目录（或子目录 `docs/` 也可）。
仓库里已经包含：

- `.github/workflows/daily.yml`：每天 UTC 00:20（北京时间 08:20）自动跑 `build/build_daily.py`，把新的 `data/daily.json` 提交回仓库，并部署到 GitHub Pages。
- `.nojekyll`：防止 GitHub Pages 把 `_` 开头目录忽略掉。

部署步骤：

1. 新建一个 GitHub 仓库（比如 `embodied-daily`），把本目录所有文件 push 到 `main` 分支根目录。
2. 在仓库 **Settings → Pages** 中：
   - Source 选择 **GitHub Actions**（推荐，用 workflow 里的 deploy job）。
   - 或者选择 **Deploy from a branch** → `main` / `/(root)`。如果用 branch 部署，workflow 里只需要 `build` job 提交新 `data/daily.json`，push 完成后 Pages 会自动重新发布。
3. 打开 **Actions** 标签页，看到 "Daily Papers Build & Deploy" workflow。它会在：
   - 每天 UTC 00:20 自动触发；
   - 你 push 代码到 `main` 时也会触发一次；
   - 可以点 **Run workflow** 手动触发。
4. 几分钟后访问 `https://<你的用户名>.github.io/<仓库名>/`，就能看到当日最新论文。

注意：
- Workflow 使用 `GITHUB_TOKEN` 自动提交 `data/daily.json`。确保仓库 Settings → Actions → Workflow permissions 设为 **Read and write permissions**。
- arXiv API 要求请求之间间隔 ≥3 秒，workflow 里已加 sleep，一次构建大约 20-40 秒。
- 如果你想发到自己的服务器上，只要把整个目录静态托管（Nginx / Caddy / Cloudflare Pages / Vercel 等都行），然后在服务器上用 cron 定时跑 `python build/build_daily.py` 就好。

## 文件结构

```
embodied-papers/
├── index.html               页面
├── styles.css               深色主题
├── app.js                   前端逻辑（加载 JSON、渲染、收藏）
├── papers.js                经典精选论文库（51 篇）
├── server.py                本地开发服务器（含 /api/daily 实时抓取）
├── build/
│   └── build_daily.py       每日构建脚本（HF + arXiv）
├── data/
│   └── daily.json           构建产物：每日新论文 JSON（由 workflow 每天更新）
├── .github/workflows/daily.yml
├── .nojekyll
└── README.md
```

## 功能概览

- **今日最新**：主卡展示当天最火/最新的一篇具身新文，下面是更多新文卡片，带 🧡 HF Daily 或 📄 arXiv 来源标签、👍 点赞数、「N天前」。
- **经典重温**：每天换一个主题，从 51 篇领域代表作里推荐 1 + 3。
- **全部精选**：按主题 / 来源 / 年份筛选；顶部搜索框搜索标题/作者/关键词；搜索栏右侧 HF / arXiv / HF Daily 三个按钮直接跳对应站点搜索。
- **收藏**：☆/★ 按钮收藏，保存在浏览器 localStorage。
- **详情弹窗**：经典论文带推荐理由 + 相关推荐 + 一键搜 HF/arXiv 最新工作。

## 可能的后续扩展

- 接入更多来源：Papers With Code、Semantic Scholar、Google Scholar 提醒。
- 对新文自动生成中文 TL;DR（调用 LLM）。
- 个人化：按关键词/作者/会议过滤并邮件/通知推送。
- 把 `papers.js` 换成可编辑的 YAML/JSON，方便维护自己的关注列表。
