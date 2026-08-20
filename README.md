# Agent Daily - 每日Agent/LLM论文推荐

自动推荐每日最新大模型/Agent相关论文，日更数据源来自 arXiv 和 Hugging Face Daily Papers，5 年历史回填使用 Semantic Scholar bulk search 补充会议/期刊信息。

## 功能特性

- **今日推荐**：每日最新论文，按热度排序
- **最新论文**：最近 7 天内的高相关论文，首页保持轻量
- **往期论文**：最近 5 年历史归档论文，按年份/月分片懒加载
- **全库搜索**：输入关键词后按需加载搜索索引，覆盖 history.json 中的全部论文
- **类型筛选**：支持按会议、期刊、预印快速筛选，历史回填会保留 venue / publication type 元数据
- **收藏功能**：本地收藏感兴趣的论文
- **主题筛选**：支持按 Agentic Search、Agent安全、错误归因、后训练、VLM、LLM训练、Multi-Agent、RAG、Reasoning、Tool Use等20+主题标签筛选
- **中文翻译**：每篇论文都提供 🇨🇳 中文 按钮，直达 hjfy.top 翻译页面
- **不遗漏保障**：每日运行回溯14天窗口，确保arXiv延迟上线的论文不会漏掉
- **自动更新**：GitHub Actions 每 3 小时自动构建，历史数据只追加永不删除，持续积累

## 主题覆盖

Agentic Search（智能体检索）、Agent Safety（智能体安全）、Attribution（错误归因）、Post-Training（后训练）、VLM（视觉语言模型）、LLM训练、Multi-Agent（多智能体）、Tool Use（工具调用）、Reasoning（推理）、RAG（检索增强生成）、Alignment（对齐）、Planning（规划）、Memory（记忆）、Fine-tuning（微调）、Benchmark（评测基准）、Code Agent（代码智能体）、Embodied Agent（具身智能体）、Agent Framework（智能体框架）、Prompt Engineering（提示工程）、Distillation（蒸馏）、Quantization（量化）、Open-Source（开源模型）

## 自动部署

项目使用 GitHub Actions 自动高频更新：

- **定时运行**：每 3 小时自动执行抓取和构建（UTC `35 */3 * * *`）
- **数据积累**：history.json 是只追加的数据库，永不删除历史数据
- **历史回填**：手动运行或 `[backfill-5y]` 触发时使用 Semantic Scholar 按年份分页抓取，不设置总量或年度上限
- **轻量首屏**：daily.json 只包含首页最新论文；往期按年份分片，搜索索引按需加载
- **自动部署**：有数据变化、手动运行或代码更新时自动部署到 GitHub Pages

## 线上地址

https://wozengyi.github.io/agent-daily/
