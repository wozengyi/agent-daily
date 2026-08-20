#!/usr/bin/env python3
"""
Agent Daily: build daily bundle of LLM/VLM Agent papers from HF + arXiv.
Pure stdlib, runs in GitHub Actions with no pip install.
"""
import json, re, sys, time, ssl, urllib.request, urllib.parse, xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / 'data'
HIST_PATH = DATA_DIR / 'history.json'
OUT_PATH = DATA_DIR / 'daily.json'
LATEST_PATH = DATA_DIR / 'latest.json'
SEARCH_INDEX_PATH = DATA_DIR / 'search-index.json'
ARCHIVE_DIR = DATA_DIR / 'archive'
CTX = ssl.create_default_context()
BOOTSTRAP_START = '/* AGENT_DAILY_BOOTSTRAP_START */'
BOOTSTRAP_END = '/* AGENT_DAILY_BOOTSTRAP_END */'

# ---------- Relevance & topic rules ----------
AGENT_HINTS = [
    'agent', 'agents', 'agentic', 'llm agent', 'multi-agent', 'multiagent',
    'large language model agent', 'foundation model agent', 'autonomous agent',
    'tool use', 'tool-use', 'tool augmented', 'function calling',
    'planning', 'reasoning', 'chain of thought', 'tree of thought', 'react',
    'retrieval augmented', 'rag', 'agentic search', 'retrieval-augmented generation',
    'safety', 'alignment', 'jailbreak', 'red team', 'hallucination', 'attribution',
    'post-training', 'post training', 'fine-tuning', 'finetuning', 'sft', 'dpo', 'rft', 'grpo', 'rlhf', 'reinforcement learning from human',
    'instruction tuning', 'preference optimization', 'direct preference',
    'vlm', 'vision-language model', 'vision language model', 'large vision-language',
    'llm training', 'language model training', 'training large language', 'pretraining', 'pre-training',
    'code agent', 'browser agent', 'web agent', 'computer use', 'computer-using agent',
    'agent memory', 'long-term memory', 'short-term memory',
    'benchmark', 'evaluation', 'evaluating agents', 'agent benchmark',
    'interpretability', 'mechanistic interpretability', 'model editing',
    'multi-modal agent', 'multimodal agent',
    'world model for agents', 'self-correction', 'self-improvement', 'reflection',
    'tool learning', 'tool-augmented language model',
    'agent error', 'error attribution', 'failure attribution', 'mistake attribution',
    'agent safety', 'llm safety', 'language model safety', 'ai safety',
    'adversarial attack on llm', 'adversarial attack on agent', 'prompt injection',
]

NEGATIVE_HINTS = [
    'robot', 'robotic', 'robotics', 'manipulation', 'humanoid', 'grasping',
    'navigation', 'locomotion', 'uav', 'drone', 'self-driving', 'autonomous driving',
    'wireless', 'communication', 'network protocol', 'wireless sensor',
    'medical image', 'clinical trial', 'drug discovery', 'protein', 'genomic',
    'financial', 'stock market', 'trading', 'portfolio', 'e-commerce',
    'power system', 'smart grid', 'energy management',
    'veterinary', 'agricultural', 'crop', 'livestock',
    'chemical reaction', 'catalyst', 'chemistry synthesis',
    'battery', 'fuel cell', 'solar cell',
]

TOPIC_RULES = [
    ('Agentic Search', [r'agentic search', r'search agent', r'web browsing agent', r'browser agent', r'retrieval-augmented', r'\bRAG\b', r'retrieval augmented generation']),
    ('Agent Safety', [r'agent safety', r'llm safety', r'language model safety', r'ai safety', r'jailbreak', r'prompt injection', r'red team', r'adversarial attack', r'misuse', r'robustness.*agent']),
    ('Error Attribution', [r'error attribution', r'failure attribution', r'mistake attribution', r'fault localization.*agent', r'root cause.*agent', r'agent failure', r'error analysis.*agent']),
    ('Post-Training', [r'post[- ]training', r'rlhf', r'reinforcement learning from human', r'dpo\b', r'direct preference optimization', r'grpo', r'group relative policy', r'ipo\b', r'kto\b', r'preference optimization', r'reward model']),
    ('LLM Training', [r'large language model training', r'llm training', r'pretraining', r'pre[- ]training', r'scaling law', r'data selection', r'training data', r'sft\b', r'supervised fine[- ]tun']),
    ('VLM Training', [r'vision[- ]language model', r'\bvlm\b', r'large vision-language', r'multimodal (pre)?training', r'visual instruction tuning', r'vision-language.*train']),
    ('Multi-Agent', [r'multi[- ]agent', r'multiagent', r'multi agent system', r'agent collaboration', r'agent communication', r'agent debate']),
    ('Tool Use', [r'tool use', r'tool-use', r'function calling', r'tool learning', r'tool augmented', r'api calling']),
    ('Reasoning', [r'reasoning', r'chain[- ]of[- ]thought', r'cot\b', r'tree[- ]of[- ]thought', r'graph[- ]of[- ]thought', r'formal reasoning', r'mathematical reasoning']),
    ('Planning', [r'\bplanning\b', r'plan generation', r'task planning', r'goal planning', r'agent planning', r'replan']),
    ('Memory', [r'memory mechanism', r'long[- ]term memory', r'short[- ]term memory', r'working memory', r'agent memory', r'experience replay', r'memory bank']),
    ('Computer Use', [r'computer use', r'computer-using agent', r'web agent', r'gui agent', r'browser agent', r'desktop agent', r'computer control']),
    ('Code Agent', [r'code agent', r'coding agent', r'programming agent', r'software engineering agent', r'code generation.*agent', r'debugging agent']),
    ('Hallucination', [r'hallucination', r'factuality', r'hallucin', r'grounded generation', r'faithfulness.*model', r'factual consistency']),
    ('Evaluation', [r'benchmark', r'evaluation.*(agent|llm|model)', r'\bevals\b', r'agent benchmark', r'leaderboard']),
    ('Alignment', [r'alignment', r'value alignment', r'constitutional ai', r'helpful.*harmless', r'helpfulness and harmlessness']),
    ('Interpretability', [r'interpretability', r'mechanistic interpretability', r'model editing', r'causal tracing', r'circuit analysis', r'neuron', r'representation engineering']),
    ('Fine-tuning', [r'fine[- ]tun', r'\bLoRA\b', r'\bQLoRA\b', r'parameter[- ]efficient', r'peft\b', r'instruction tuning']),
    ('Reflection', [r'self[- ]correction', r'self[- ]improvement', r'reflection', r'self[- ]critique', r'iterative refinement']),
    ('Multimodal Agent', [r'multimodal agent', r'visual agent', r'video agent', r'embodied language agent', r'multi[- ]modal tool']),
    ('RL for LLM', [r'reinforcement learning.*(llm|language model|reasoning)', r'policy gradient.*language', r'online rl.*llm', r'offline rl.*language']),
    ('Data Engine', [r'data engine', r'synthetic data', r'data synthesis', r'data filtering', r'data pruning', r'deduplication']),
    ('Agent Framework', [r'agent framework', r'agent architecture', r'agent infrastructure', r'agent system design']),
    ('World Model', [r'world model', r'latent dynamics model', r'environment model.*agent']),
]

# ---------- Utilities ----------
def log(*a): print('[build]', *a, file=sys.stderr, flush=True)

def fetch(url, timeout=60, retries=5, backoff=8):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0 AgentDaily/1.0'})
            with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
                return r.read().decode('utf-8', errors='replace')
        except Exception as e:
            if i == retries-1: 
                log(f'fetch failed after {retries} retries: {url[:60]}... {e}')
                return ''
            time.sleep(backoff * (i+1))
    return ''

def arxiv_id_from_url(u):
    m = re.search(r'arxiv\.org/abs/([0-9]{4}\.[0-9]{4,5})(v\d+)?', u or '')
    return m.group(1) if m else None

def norm_paper_id(pid):
    return re.sub(r'v\d+$', '', str(pid))

# ---------- Topic & relevance ----------
def is_relevant(text):
    t = ' ' + text.lower() + ' '
    if any(re.search(r'\b'+re.escape(h)+r'\b', t) for h in NEGATIVE_HINTS):
        if any(re.search(r'\b'+re.escape(h)+r'\b', t) for h in ['agent', 'agents', 'agentic', 'llm', 'large language model', 'vlm', 'vision-language']):
            pass
        else:
            return False
    return any(re.search(r'\b'+re.escape(h)+r'\b', t) for h in AGENT_HINTS)

def classify_topics(title, abstract):
    text = f"{title}. {abstract or ''}".lower()
    topics = []
    for name, patterns in TOPIC_RULES:
        for pat in patterns:
            if re.search(pat, text, re.I):
                topics.append(name); break
    return topics

# ---------- Sources ----------
def fetch_hf_days(days=14):
    papers = []
    for d in range(days):
        date = (datetime.now(timezone.utc) - timedelta(days=d)).strftime('%Y-%m-%d')
        try:
            raw = fetch(f'https://huggingface.co/api/daily_papers?date={date}', timeout=30)
            data = json.loads(raw)
        except Exception as e:
            log(f'hf skip {date}: {e}'); continue
        if not isinstance(data, list): continue
        for it in data:
            p = it.get('paper', {})
            pid = norm_paper_id(p.get('id') or arxiv_id_from_url(p.get('absUrl','')))
            if not pid: continue
            title = p.get('title','').replace('\n',' ').strip()
            authors = [a.get('name','') for a in p.get('authors',[])]
            summary = (p.get('summary') or '').replace('\n',' ').strip()
            if not is_relevant(title + ' ' + summary): continue
            topics = classify_topics(title, summary)
            if not topics: continue
            papers.append({
                'id': f'arxiv:{pid}',
                'title': title, 'authors': authors, 'abstract': summary,
                'date': date, 'upvotes': int(it.get('paper',{}).get('upvotes',0) or 0),
                'source': 'hf', 'arxiv': f'https://arxiv.org/abs/{pid}',
                'pdf': f'https://arxiv.org/pdf/{pid}.pdf',
                'hfUrl': it.get('url') or f'https://huggingface.co/papers/{pid}',
                'url': f'https://arxiv.org/abs/{pid}', 'topics': topics, 'tags': topics[:5]
            })
        time.sleep(1.0)
    return papers

def fetch_page(url):
    raw = fetch(url, timeout=60, retries=3, backoff=10)
    for _ in range(2):
        if '<feed' in raw and '<entry>' in raw: return raw
        time.sleep(8)
        raw = fetch(url, timeout=60, retries=2, backoff=5)
    return raw

def parse_arxiv_xml(raw):
    ns = {'a':'http://www.w3.org/2005/Atom'}
    try: root = ET.fromstring(raw)
    except: return []
    out = []
    for e in root.findall('a:entry', ns):
        title = (e.findtext('a:title', default='', namespaces=ns) or '').replace('\n',' ').strip()
        summ = (e.findtext('a:summary', default='', namespaces=ns) or '').replace('\n',' ').strip()
        url = ''; pid = ''
        for l in e.findall('a:id', ns):
            url = (l.text or '').strip()
            pid = arxiv_id_from_url(url)
            if pid: break
        if not pid: continue
        published = (e.findtext('a:published', default='', namespaces=ns) or '')[:10]
        updated = (e.findtext('a:updated', default='', namespaces=ns) or '')[:10]
        authors = []
        for a in e.findall('a:author', ns):
            n = a.findtext('a:name', default='', namespaces=ns)
            if n: authors.append(n.strip())
        out.append({'pid': pid, 'title': title, 'abstract': summ, 'date': updated or published,
                    'authors': authors, 'arxiv': f'https://arxiv.org/abs/{pid}', 'pdf': f'https://arxiv.org/pdf/{pid}.pdf'})
    return out

def fetch_arxiv(lookback_days=7, per_query=100, queries=None):
    if queries is None:
        queries = [
            'all:agent', 'all:"llm agent"', 'all:"multi-agent"', 'all:"tool use"',
            'all:"agentic"', 'all:RAG', 'all:"retrieval augmented"',
            'all:"agent safety"', 'all:"llm safety"', 'all:jailbreak', 'all:"prompt injection"',
            'all:"error attribution"', 'all:"post-training"', 'all:RLHF', 'all:DPO', 'all:GRPO',
            'all:"fine-tuning" llm', 'all:"vision language model"', 'all:VLM',
            'all:"reasoning" "language model"', 'all:"chain of thought"',
            'all:"world model" agent', 'all:"code agent"', 'all:"web agent"', 'all:"computer use" agent',
        ]
    out = []
    seen = set()
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=lookback_days)
    for q in queries:
        url = (f'http://export.arxiv.org/api/query?search_query={urllib.parse.quote(q)}'
               f'&start=0&max_results={per_query}&sortBy=submittedDate&sortOrder=descending')
        try:
            raw = fetch_page(url)
            if not raw:
                log(f'arxiv query {q[:30]}... empty response, skipping'); time.sleep(6.5); continue
            for p in parse_arxiv_xml(raw):
                d = p['date']
                try:
                    if datetime.fromisoformat(d).date() < start: continue
                except: pass
                if not is_relevant(p['title'] + ' ' + p['abstract']): continue
                topics = classify_topics(p['title'], p['abstract'])
                if not topics: continue
                key = norm_paper_id(p['pid'])
                if key in seen: continue
                seen.add(key)
                p['id'] = f'arxiv:{key}'
                p['source'] = 'arxiv'
                p['upvotes'] = 0
                p['topics'] = topics
                p['tags'] = topics[:5]
                p['url'] = p['arxiv']
                out.append(p)
            log(f'arxiv query {q[:30]}... kept {len(out)} total so far')
        except Exception as e:
            log(f'arxiv query {q[:30]}... error: {e}')
        time.sleep(6.5)
    return out

# ---------- History management ----------
def load_history():
    if HIST_PATH.exists():
        try: return json.loads(HIST_PATH.read_text(encoding='utf-8'))
        except: pass
    return {'generatedAt': None, 'papers': {}}

def save_history(hist):
    DATA_DIR.mkdir(exist_ok=True)
    HIST_PATH.write_text(json.dumps(hist, ensure_ascii=False, indent=2), encoding='utf-8')

def merge_into_history(hist, papers):
    added = 0
    today = datetime.now(timezone.utc).isoformat()
    hist.setdefault('papers', {})
    for p in papers:
        key = p['id']
        cur = hist['papers'].get(key)
        if not cur:
            hist['papers'][key] = dict(p); added += 1
        else:
            cur['upvotes'] = max(int(cur.get('upvotes',0)), int(p.get('upvotes',0)))
            cur['topics'] = list(dict.fromkeys(list(cur.get('topics') or []) + list(p.get('topics') or [])))[:8]
            if p.get('hfUrl'): cur['hfUrl'] = p['hfUrl']
    hist['generatedAt'] = today
    return added

def topic_counts(papers):
    counts = {}
    for p in papers:
        for topic in p.get('topics') or p.get('tags') or []:
            counts[topic] = counts.get(topic, 0) + 1
    return counts

def compact_search_paper(p):
    keep = {
        'id', 'title', 'authors', 'date', 'published', 'source', 'topics', 'tags',
        'arxiv', 'pdf', 'url', 'hfUrl', 'upvotes', 'venue', 'publicationKind',
        'publicationTypes', 'citationCount',
    }
    out = {k: p.get(k) for k in keep if p.get(k) not in (None, '', [])}
    abstract = ' '.join((p.get('abstract') or '').split())
    if abstract:
        out['abstract'] = abstract[:360]
    return out

def compact_display_paper(p, abstract_limit=720):
    out = compact_search_paper(p)
    abstract = ' '.join((p.get('abstract') or '').split())
    if abstract:
        out['abstract'] = abstract[:abstract_limit]
    return out

def write_latest_bundle(bundle):
    latest = dict(bundle)
    latest['papers'] = [compact_display_paper(p, abstract_limit=900) for p in bundle.get('papers', [])]
    latest['archive'] = []
    LATEST_PATH.write_text(json.dumps(latest, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    log(f'wrote {LATEST_PATH}: count={len(latest["papers"])}')

def write_bootstrap_html(light_json):
    index_path = ROOT / 'index.html'
    if not index_path.exists():
        return
    html = index_path.read_text(encoding='utf-8')
    start = html.find(BOOTSTRAP_START)
    end = html.find(BOOTSTRAP_END)
    if start < 0 or end < 0 or end < start:
        return
    replacement = BOOTSTRAP_START + '\nwindow.__BUNDLE__=' + light_json + ';\n'
    html = html[:start] + replacement + html[end:]
    index_path.write_text(html, encoding='utf-8')

def write_search_index(hist):
    papers = sorted(
        hist.get('papers', {}).values(),
        key=lambda p: ((p.get('date') or '0000-00-00'), int(p.get('upvotes') or 0)),
        reverse=True,
    )
    index = {
        'generatedAt': hist.get('generatedAt'),
        'count': len(papers),
        'papers': [compact_search_paper(p) for p in papers],
    }
    SEARCH_INDEX_PATH.write_text(json.dumps(index, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    log(f'wrote {SEARCH_INDEX_PATH}: count={len(papers)}')

def write_archive_shards(hist, bundle):
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    for old in ARCHIVE_DIR.glob('*.json'):
        old.unlink()
    recent_cutoff = bundle.get('recentCutoff') or '9999-99-99'
    archive_cutoff = bundle.get('archiveCutoff') or '0000-00-00'
    papers = [
        p for p in hist.get('papers', {}).values()
        if archive_cutoff <= (p.get('date') or '0000-00-00') < recent_cutoff
    ]
    def keyf(p):
        return ((p.get('date') or '0000-00-00'),
                1 if p.get('source')=='hf' else 0,
                int(p.get('upvotes') or 0),
                len(p.get('topics') or []))
    papers = sorted(papers, key=keyf, reverse=True)
    by_year = {}
    for p in papers:
        year = (p.get('date') or '0000')[:4]
        if year.isdigit():
            by_year.setdefault(year, []).append(p)
    index = {
        'generatedAt': hist.get('generatedAt'),
        'archiveTotal': len(papers),
        'topicCounts': topic_counts(papers),
        'recentCutoff': recent_cutoff,
        'archiveCutoff': archive_cutoff,
        'years': [],
    }
    for year in sorted(by_year.keys(), reverse=True):
        items = by_year[year]
        months = {}
        for p in items:
            ym = (p.get('date') or '')[:7]
            if ym:
                months[ym] = months.get(ym, 0) + 1
        (ARCHIVE_DIR / f'{year}.json').write_text(
            json.dumps({'year': year, 'count': len(items), 'papers': items}, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
        index['years'].append({
            'year': year,
            'count': len(items),
            'months': [{'month': m, 'count': months[m]} for m in sorted(months.keys(), reverse=True)],
            'path': f'data/archive/{year}.json',
        })
    (DATA_DIR / 'archive-index.json').write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding='utf-8')
    log(f'wrote archive shards: years={len(index["years"])} total={index["archiveTotal"]}')

# ---------- Bundle ----------
def build_bundle(hist, recent_days=7, archive_days=5*365, limit=80, archive_limit=0):
    log('Fetching HF daily papers...')
    hf = fetch_hf_days(days=14)
    log(f'Got {len(hf)} HF papers')
    log('Fetching arXiv papers...')
    arx = fetch_arxiv(lookback_days=7, per_query=300)
    log(f'Got {len(arx)} arXiv papers')
    by_id = {p['id']: dict(p) for p in arx}
    for p in hf:
        cur = by_id.get(p['id'])
        if cur:
            cur['source'] = 'hf'
            cur['upvotes'] = max(int(cur.get('upvotes',0)), int(p.get('upvotes',0)))
            cur['hfUrl'] = p.get('hfUrl')
            cur['url'] = p['url']
            cur['topics'] = list(dict.fromkeys((p.get('topics') or []) + (cur.get('topics') or [])))[:8]
            cur['tags'] = cur['topics'][:5]
            if p.get('date'): cur['date'] = p['date']
        else:
            by_id[p['id']] = dict(p)
    papers = list(by_id.values())
    added = merge_into_history(hist, papers)
    all_hist = list(hist['papers'].values())
    today = datetime.now(timezone.utc).date()
    recent_cutoff = (today - timedelta(days=recent_days)).isoformat()
    archive_cutoff = (today - timedelta(days=archive_days)).isoformat()
    def keyf(p):
        return ((p.get('date') or '0000-00-00'),
                1 if p.get('source')=='hf' else 0,
                int(p.get('upvotes') or 0),
                len(p.get('topics') or []))
    today_iso = today.isoformat()
    visible_hist = [p for p in all_hist if (p.get('date') or '0000-00-00') <= today_iso]
    recent = sorted([p for p in visible_hist if (p.get('date') or '0000-00-00') >= recent_cutoff], key=keyf, reverse=True)
    archive = sorted([p for p in visible_hist
                       if archive_cutoff <= (p.get('date') or '0000-00-00') < recent_cutoff],
                      key=keyf, reverse=True)
    archive_total = len(archive)
    recent_total = len(recent)
    if limit is not None:
        recent = recent[:limit]
    if archive_limit is not None:
        archive = archive[:archive_limit]
    warnings = []
    if added == 0:
        warnings.append('zero_new_today')
    return {
        'generatedAt': hist.get('generatedAt'),
        'recentDays': recent_days,
        'archiveDays': archive_days,
        'recentCutoff': recent_cutoff,
        'archiveCutoff': archive_cutoff,
        'addedToday': added,
        'historyTotal': len(hist.get('papers',{})),
        'topicCounts': topic_counts(all_hist),
        'count': len(recent),
        'recentTotal': recent_total,
        'archiveCount': len(archive),
        'archiveTotal': archive_total,
        'sources': {
            'hf': sum(1 for p in recent if p.get('source')=='hf'),
            'arxiv': sum(1 for p in recent if p.get('source')=='arxiv'),
            'semanticScholar': sum(1 for p in recent if p.get('source')=='semantic-scholar'),
        },
        'archiveSources': {
            'hf': sum(1 for p in archive if p.get('source')=='hf'),
            'arxiv': sum(1 for p in archive if p.get('source')=='arxiv'),
            'semanticScholar': sum(1 for p in archive if p.get('source')=='semantic-scholar'),
        },
        'warnings': warnings,
        'notes': ['archive is split by year under data/archive/ for fast lazy loading; data/history.json keeps the complete database'],
        'papers': recent,
        'archive': archive,
    }

def save(hist, bundle):
    DATA_DIR.mkdir(exist_ok=True)
    HIST_PATH.write_text(json.dumps(hist, ensure_ascii=False, indent=2), encoding='utf-8')
    write_latest_bundle(bundle)
    light_bundle = dict(bundle)
    light_bundle['papers'] = [compact_display_paper(p, abstract_limit=900) for p in bundle.get('papers', [])[:36]]
    light_bundle['archive'] = []
    light_bundle['count'] = len(light_bundle['papers'])
    light_bundle['latestPath'] = 'data/latest.json'
    light_json = json.dumps(light_bundle, ensure_ascii=False, separators=(',', ':'))
    OUT_PATH.write_text(light_json, encoding='utf-8')
    write_bootstrap_html(light_json)
    write_archive_shards(hist, bundle)
    write_search_index(hist)
    (DATA_DIR / 'data.js').write_text('window.__BUNDLE__=' + light_json + ';\n', encoding='utf-8')

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--recent', type=int, default=7)
    ap.add_argument('--archive', type=int, default=5*365)
    ap.add_argument('--limit', type=int, default=None, help='Max recent papers (default: all)')
    ap.add_argument('--archive-limit', type=int, default=None, help='Max archive papers (default: all)')
    args = ap.parse_args()
    hist = load_history()
    log(f'loaded history: {len(hist.get("papers",{}))} papers')
    bundle = build_bundle(hist, recent_days=args.recent, archive_days=args.archive,
                          limit=args.limit, archive_limit=args.archive_limit)
    save(hist, bundle)
    log(f'done: new+recent={bundle["count"]} archive={bundle["archiveCount"]} total={bundle["historyTotal"]} added={bundle["addedToday"]}')

if __name__ == '__main__':
    main()
