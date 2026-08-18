# Agent Daily - 每日Agent/LLM论文推荐

自动推荐每日最新Agent与大模型相关论文，数据源来自 arXiv 和 Hugging Face Daily Papers。

## 覆盖方向

- **Agentic Search / RAG**: 智能检索、浏览器Agent、检索增强生成
- **Agent Safety**: 安全对齐、越狱攻击、红队测试、Prompt Injection
- **Error Attribution**: 错误归因、失败定位、根因分析
- **Post-Training**: RLHF、DPO、GRPO、偏好优化、后训练对齐
- **LLM Training**: 预训练、SFT、Scaling Law、数据工程
- **VLM Training**: 视觉语言模型、多模态训练
- **Multi-Agent**: 多智能体协作、通信、辩论
- **Tool Use**: 工具调用、Function Calling
- **Reasoning**: CoT、ToT、数学/代码推理
- **Planning & Memory**: 任务规划、长短记忆
- **Computer Use**: GUI操作、浏览器/桌面Agent
- **Hallucination**: 幻觉、事实性问题
- **Interpretability**: 可解释性、模型编辑
- **Evaluation**: Agent评测、Benchmark

## 功能特性

- **今日推荐**：每日最新论文，按热度排序
- **最新论文**：最近 7 天内的所有匹配论文
- **往期论文**：最近 5 年历史归档论文，按月份分组展示
- **精选论文**：25+领域经典高影响力论文
- **收藏功能**：本地收藏感兴趣的论文
- **主题筛选**：支持按20+主题标签筛选
- **中文翻译**：每篇论文都提供 🇨🇳 中文 按钮，直达 hjfy.top 翻译页面
- **自动更新**：GitHub Actions 每日自动构建，持续积累历史数据

## 自动部署

项目使用 GitHub Actions 自动每日更新：

- **定时运行**：每天 UTC 00:25 自动执行抓取和构建
- **数据积累**：history.json 是只追加的数据库，永不删除历史数据
- **自动部署**：构建完成后自动部署到 GitHub Pages

### 手动回填历史数据

如果需要一次性回填多年历史：
1. 前往仓库 Actions 页面
2. 选择 "Agent Daily Build & Deploy" workflow
3. 点击 "Run workflow"
4. 在 `backfill_years` 输入框填写要回填的年数（如 5）
5. 运行工作流即可

本地回填命令：
```bash
python build/backfill_years.py --years 5 --max-per-month 150 --page-size 100
```

## 本地开发

```bash
# 启动本地服务器
python server.py --port 8766

# 手动构建每日数据
python build/build_daily.py
```

访问 http://localhost:8766 查看效果。

## 线上地址

https://wozengyi.github.io/agent-daily/
