const PAPERS = [
  {
    id: 'c:treeofthoughts',
    title: 'Tree of Thoughts: Deliberate Problem Solving with Large Language Models',
    authors: ['Shunyu Yao', 'Dian Yu', 'Jeffrey Zhao', 'et al.'],
    year: 2023,
    venue: 'NeurIPS 2023',
    arxiv: 'https://arxiv.org/abs/2305.10601',
    topics: ['Reasoning', 'Planning'],
    abstract: 'Tree of Thoughts (ToT) 框架允许LLM在解决问题时进行深思熟虑的决策，通过探索多个推理路径、自我评估选择，并在必要时回溯以做出全局选择。',
    why: 'LLM推理的经典工作，提出思维树框架，显著提升复杂问题解决能力'
  },
  {
    id: 'c:react',
    title: 'ReAct: Synergizing Reasoning and Acting in Language Models',
    authors: ['Shunyu Yao', 'Jeffrey Zhao', 'Dian Yu', 'et al.'],
    year: 2022,
    venue: 'ICLR 2023',
    arxiv: 'https://arxiv.org/abs/2210.03629',
    topics: ['Reasoning', 'Tool Use', 'Agent Framework'],
    abstract: 'ReAct框架将推理（生成思维链）和行动（调用外部工具）交错进行，使LLM能够在动态环境中执行复杂任务，解决幻觉和错误传播问题。',
    why: 'Agent领域奠基工作之一，提出推理+行动的范式'
  },
  {
    id: 'c:toolformer',
    title: 'Toolformer: Language Models Can Teach Themselves to Use Tools',
    authors: ['Timo Schick', 'Jane Dwivedi-Yu', 'Roberto Dessì', 'et al.'],
    year: 2023,
    venue: 'NeurIPS 2023',
    arxiv: 'https://arxiv.org/abs/2302.04761',
    topics: ['Tool Use', 'LLM Training'],
    abstract: 'Toolformer训练LM在自监督方式下学习调用外部工具（计算器、搜索引擎、翻译系统等），决定何时调用、传什么参数，并将结果融入后续token预测。',
    why: '工具调用学习的经典工作'
  },
  {
    id: 'c:reflexion',
    title: 'Reflexion: Language Agents with Verbal Reinforcement Learning',
    authors: ['Noah Shinn', 'Federico Cassano', 'Ashwin Gopinath', 'et al.'],
    year: 2023,
    venue: 'NeurIPS 2023',
    arxiv: 'https://arxiv.org/abs/2303.11366',
    topics: ['Agent Framework', 'Post-Training', 'Memory'],
    abstract: 'Reflexion通过口头反馈强化学习让Agent自我反思，从之前的失败中学习，不需要更新模型权重，通过在episodic memory中保存反思来提升后续性能。',
    why: 'Agent自我反思机制的代表性工作'
  },
  {
    id: 'c:voyager',
    title: 'Voyager: An Open-Ended Embodied Agent with Large Language Models',
    authors: ['Guanzhi Wang', 'Yuqi Xie', 'Yunfan Jiang', 'et al.'],
    year: 2023,
    venue: 'NeurIPS 2023',
    arxiv: 'https://arxiv.org/abs/2305.16291',
    topics: ['Embodied Agent', 'Agent Framework', 'Memory'],
    abstract: 'Voyager是Minecraft中的第一个终身学习Agent，由LLM驱动，包含自动课程、技能库和迭代提示机制，能够持续探索、获得新技能而不需要人类干预。',
    why: '开放式探索+技能库的经典Agent架构'
  },
  {
    id: 'c:autogpt',
    title: 'AutoGPT: An Autonomous GPT-4 Experiment',
    authors: ['Significant Gravitas'],
    year: 2023,
    venue: 'Open Source',
    url: 'https://github.com/Significant-Gravitas/AutoGPT',
    topics: ['Agent Framework', 'Multi-step Planning'],
    abstract: '早期开源自主Agent项目，展示了LLM自主分解目标、使用工具、浏览网页、编写代码完成复杂任务的能力，掀起了Agent开发热潮。',
    why: '引爆自主Agent浪潮的标志性开源项目'
  },
  {
    id: 'c:rlhf',
    title: 'Training language models to follow instructions with human feedback',
    authors: ['Long Ouyang', 'Jeff Wu', 'Xu Jiang', 'et al.'],
    year: 2022,
    venue: 'NeurIPS 2022',
    arxiv: 'https://arxiv.org/abs/2203.02155',
    topics: ['Post-Training', 'Alignment', 'RLHF'],
    abstract: 'InstructGPT论文，详细介绍了通过人类反馈强化学习（RLHF）对齐语言模型，使其能够更好地遵循人类指令，成为ChatGPT的基础技术。',
    why: 'RLHF对齐技术的奠基性工作'
  },
  {
    id: 'c:dpo',
    title: 'Direct Preference Optimization: Your Language Model is Secretly a Reward Model',
    authors: ['Rafael Rafailov', 'Archit Sharma', 'Eric Mitchell', 'et al.'],
    year: 2023,
    venue: 'NeurIPS 2023',
    arxiv: 'https://arxiv.org/abs/2305.18290',
    topics: ['Post-Training', 'Alignment', 'DPO'],
    abstract: 'DPO直接从偏好数据优化策略，无需单独训练奖励模型和强化学习循环，大大简化了LLM对齐流程，成为RLHF的主流替代方案。',
    why: '直接偏好优化，简化LLM后训练流程'
  },
  {
    id: 'c:rag',
    title: 'Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks',
    authors: ['Patrick Lewis', 'Ethan Perez', 'Aleksandra Piktus', 'et al.'],
    year: 2020,
    venue: 'NeurIPS 2020',
    arxiv: 'https://arxiv.org/abs/2005.11401',
    topics: ['RAG', 'Knowledge Retrieval'],
    abstract: '提出检索增强生成（RAG），参数化记忆（seq2seq）和非参数化记忆（维基百科向量索引）结合，解决知识密集型NLP任务中的幻觉问题。',
    why: 'RAG技术的开山之作'
  },
  {
    id: 'c:cot',
    title: 'Chain-of-Thought Prompting Elicits Reasoning in Large Language Models',
    authors: ['Jason Wei', 'Xuezhi Wang', 'Dale Schuurmans', 'et al.'],
    year: 2022,
    venue: 'NeurIPS 2022',
    arxiv: 'https://arxiv.org/abs/2201.11903',
    topics: ['Reasoning', 'Prompt Engineering'],
    abstract: '思维链提示（CoT）通过在提示中提供分步推理示例，引导LLM生成逐步推理过程，显著提升算术、常识和符号推理任务的性能。',
    why: 'LLM推理能力激发的经典工作'
  },
  {
    id: 'c:gpt4',
    title: 'GPT-4 Technical Report',
    authors: ['OpenAI'],
    year: 2023,
    venue: 'Technical Report',
    arxiv: 'https://arxiv.org/abs/2303.08774',
    topics: ['LLM Training', 'VLM', 'Multimodal'],
    abstract: 'GPT-4技术报告，介绍了大规模多模态模型的训练、能力、评估和对齐，展示了在专业考试和各种基准上的人类水平表现。',
    why: '首个大规模多模态基础模型，推动VLM发展'
  },
  {
    id: 'c:llava',
    title: 'LLaVA: Large Language and Vision Assistant',
    authors: ['Haotian Liu', 'Chunyuan Li', 'Qingyang Wu', 'Yong Jae Lee'],
    year: 2023,
    venue: 'NeurIPS 2023',
    arxiv: 'https://arxiv.org/abs/2304.08485',
    topics: ['VLM', 'Multimodal', 'Open-Source'],
    abstract: 'LLaVA通过将预训练视觉编码器和LLM连接，使用GPT-4生成的多模态指令遵循数据微调，构建了一个强大的开源视觉语言助手。',
    why: '开源VLM的代表性工作'
  },
];
window.PAPERS = PAPERS;
