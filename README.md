# Embodied Daily - 每日具身智能论文推荐

自动推荐每日最新具身智能(Embodied AI)相关论文，数据源来自 arXiv 和 Hugging Face Daily Papers。

## 功能特性

- **今日推荐**：每日最新论文，按热度排序
- **最新论文**：最近 7 天内的所有匹配论文
- **往期论文**：最近 5 年历史归档论文（5000+篇），按月份分组展示
- **精选论文**：领域经典高影响力论文
- **收藏功能**：本地收藏感兴趣的论文
- **主题筛选**：支持按 VLA、WAM(World Action Models)、Manipulation、Humanoid、World Model、RL 等 20+ 主题标签筛选
- **中文翻译**：每篇论文都提供 🇨🇳 中文 按钮，直达 hjfy.top 翻译页面
- **自动更新**：GitHub Actions 每日自动构建，持续积累历史数据

## 数据来源

- **arXiv**：覆盖 cs.RO, cs.AI, cs.CV, cs.LG, cs.MA, eess.SY, stat.ML, cs.HC 等分类
- **Hugging Face Daily Papers**：社区每日热门论文
- **主题覆盖**：VLA, WAM, 机械臂操作, 人形机器人, 运动控制, 导航, 世界模型, Sim2Real, 灵巧手, 模仿学习, 强化学习, LLM Agent, 遥操作, 移动操作, 双臂机器人, 数据集, 开源, 模拟器, 基础模型, 3D感知, 多任务, 触觉, 具身视觉, 硬件 等

## 自动部署

项目使用 GitHub Actions 自动每日更新：

- **定时运行**：每天 UTC 00:20 自动执行抓取和构建
- **数据积累**：history.json 是只追加的数据库，永不删除历史数据
- **自动部署**：构建完成后自动部署到 GitHub Pages

### 手动回填历史数据

如果需要一次性回填多年历史：
1. 前往仓库 Actions 页面
2. 选择 "Daily paper build" workflow
3. 点击 "Run workflow"
4. 在 ackfill_years 输入框填写要回填的年数（如 5）
5. 运行工作流即可

本地回填命令：
`ash
python build/backfill_years.py --years 5 --max-per-month 200 --page-size 100
`

## 本地开发

`ash
# 启动本地服务器
python server.py --port 8765

# 手动构建每日数据
python build/build_daily.py
`

访问 http://localhost:8765 查看效果。

## 线上地址

https://wozengyi.github.io/embodied-daily/
