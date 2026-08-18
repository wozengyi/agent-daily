"""Rewrite build_daily.py with wider coverage, 7d arXiv rolling window, persistent history."""
import os, re, sys, json, time, ssl, urllib.request, urllib.parse, urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
import argparse

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / 'data'
HISTORY_PATH = DATA_DIR / 'history.json'
OUT_PATH = DATA_DIR / 'daily.json'

UA = 'Mozilla/5.0 (EmbodiedDaily/1.1; +https://github.com/)'
CTX = ssl.create_default_context()

# ---- Keyword rules (wider set) ----
EMBODIMENT_KW_BROAD = [
    'embodied', 'embodied ai', 'embodied agent',
    'robot', 'robotic', 'robotics', 'robot learning',
    'manipulation', 'manipulator', 'manipulat',
    'grasp', 'grasping', 'dexter',
    'humanoid', 'whole-body', 'whole body control', 'anthropomorphic',
    'locomotion', 'legged', 'biped', 'quadruped', 'gait',
    'navigation', 'pointnav', 'objectnav', 'visual navigation', 'slam',
    'teleoperation', 'tele-op', 'teleop', 'vr control',
    'bimanual', 'dual-arm', 'aloha',
    'mobile manipulation',
    'sim2real', 'sim-to-real', 'domain randomization',
    'vla', 'vision-language-action', 'vision language action', 'vision-language policy',
    'diffusion policy', 'behavior cloning', 'imitation learning', 'learning from demonstration',
    'world model for robot', 'video world model', 'world action model', 'world-action model',
    'rl for robot', 'reinforcement learning robot',
    'affordance', 'motion planning',
    'huggingface',
    # Platforms / labs / well-known systems (important for recall)
    'unitree', 'boston dynamics', 'atlas', 'spot', 'figure 0', 'figure-0', 'optimus',
    '1x ', 'physical intelligence', 'pi0', 'π0',
    'shadow hand', 'allegro hand', 'barrett hand', 'wam', 'whole-arm manipulator',
    'franka', 'panda', 'kuka', 'ur5', 'ur10', 'sawyer', 'baxter', 'fetch robot',
    'aloha', 'droid dataset', 'bridge data', 'open x-embodiment',
    'rt-1', 'rt-2', 'rt-3', 'octo', 'openvla',
    'habitat', 'isaac lab', 'isaac sim', 'mani skill', 'robosuite', 'mujoco',
]
STRONG_KWS = [
    'robot','robotic','robotics','embodied','manipulat','grasp','humanoid','locomotion','navigation',
    'teleop','dexter','bimanual','legged','vla','sim2real','unitree','allegro','shadow hand','barrett',
    'franka','panda','kuka','aloha','mujoco','habitat','isaac','robosuite','dexterous'
]

TOPIC_RULES = [
    ('VLA', [r'\bvla\b', r'vision[- ]language[- ]action', r'vision.language.action',
             r'vision[- ]language[- ]to[- ]action', r'vision[- ]language[- ]policy',
             r'rt-?\d\b', r'robotics transformer', r'openvla', r'\bocto\b', r'pi_?0', r'π_?0',
             r'vision[- ]language[- ]model.*(policy|robot|control|action|manipulation)',
             r'language[- ]conditioned (policy|control|manipulation|action)',
             r'language[- ]guided (policy|control|manipulation)']),
        ('Manipulation', [r'robotic manipulation', r'manipulation (task|policy|skill|of|robot|objects|object|scene|grasp|dexterous|bimanual)', r'pick[- ]and[- ]place', r'robotic arm', r'contact-rich', r'whole-arm', r'wam', r'object manipulation', r'manipulator (arm|control|kinematic)']),
    ('Grasping', [r'\bgrasp(ing|er)?\b', r'6-?dof grasp', r'graspnet', r'anygrasp']),
    ('Humanoid', [r'humanoid', r'whole[- ]body control', r'anthropomorphic',
                  r'figure[- ]?0\d?', r'optimus', r'\b1x\b', r'unitree g\d', r'\batlas\b']),
    ('Locomotion', [r'locomotion', r'quadruped', r'biped(al)?', r'legged robot', r'gait', r'\bspot\b']),
    ('Navigation', [r'navigation', r'pointnav', r'objectnav', r'visual navigation', r'\bslam\b',
                    r'exploration', r'path planning']),
    ('World Model', [r'world model', r'video world model', r'latent dynamics', r'world action model']),
    # Note: 'WAM' in robotics also refers to Barrett Whole-Arm Manipulator, so we also add
    # a Hardware rule for Barrett WAM to keep that tag when only the arm is mentioned.

    ('Sim2Real', [r'sim2real', r'sim-to-real', r'domain random', r'domain adaptation']),
    ('Dexterous', [r'dexter(ous|ity)', r'in-hand manipulation', r'shadow hand', r'allegro hand',
                   r'barrett hand']),
    ('Imitation Learning', [r'imitation learning', r'behavior cloning', r'learning from demonstrations?',
                            r'diffusion policy', r'action chunk', r'act\b.*(policy|model|transformer)']),
    ('Reinforcement Learning', [r'reinforcement learning', r'policy gradient', r'\bppo\b', r'\bsac\b',
                                r'\brl\b.*policy']),
    ('LLM Agent', [r'large language model', r'\bllm\b', r'code as policies', r'saycan',
                   r'inner monologue', r'progprompt']),
    ('Teleoperation', [r'teleoperation', r'tele[- ]op(eration)?', r'remote operation', r'vr control']),
    ('Mobile Manipulation', [r'mobile manipulation', r'mobile manipulator', r'wheel.*arm']),
    ('Bimanual', [r'bimanual', r'dual[- ]arm', r'two[- ]hand', r'\baloha\b']),
    ('Dataset', [r'dataset', r'benchmark', r'open[- ]x', r'bridge data', r'open [x-]embodiment',
                 r'\bdroid\b']),
    ('Open-Source', [r'open[- ]source', r'open[- ]weights']),
    ('Simulator', [r'simulator', r'habitat', r'isaac(\s?sim|\s?lab|gym|\sgym)', r'mani[sk]ill',
                   r'robosuite', r'mujoco', r'pybullet', r'sapien']),
    ('Foundation Models', [r'foundation model', r'generalist policy', r'robot foundation model',
                           r'general-purpose robot']),
    ('3D / Perception', [r'point cloud', r'3d (perception|representation|tracking|reconstruction)',
                         r'\bnerf\b', r'gaussian splat', r'object-centric', r'pose estimation']),
    ('Multi-task', [r'multi[- ]task', r'multitask', r'task generalization']),
    ('Tactile', [r'tactile', r'touch sensor', r'gel(sight|slim)']),
    ('Embodied Vision', [r'embodied (vision|ai|agent)', r'embodied question answering', r'\beqa\b']),
    ('Hardware', [r'\bfranka\b', r'\bpanda\b', r'\bkuka\b', r'\bur[ -]?\d', r'\bsawyer\b', r'\bbaxter\b',
                  r'\bfetch\b', r'\bunitree\b', r'\ballegro\b', r'shadow hand', r'barrett hand',
                  r'barrett\s+wam\b', r'\bwam\b\s*(arm|manipulator)', r'\baloha\b']),
    ('Autonomous Driving', [r'autonomous driving', r'self[- ]driving', r'driving policy',
                            r'urban driving', r'vehicle control']),
]

def classify_topics(text):
    t = text.lower()
    topics = []
    for name, pats in TOPIC_RULES:
        for pat in pats:
            if re.search(pat, t, flags=re.IGNORECASE):
                topics.append(name); break
    if not topics and re.search(r'robot|robotic|embodied', t):
        topics.append('Robotics')
    # World Action Models (WAMs). The bare token 'WAM' is ambiguous (Barrett arm / Wannier / etc.),
    # so only treat it as WAM when either the full phrase appears, or 'WAM' appears WITHOUT
    # Barrett/arm/manipulator context in a paper that already has robotics keywords.
    wam_phrase = re.search(r'world[ -]?action[ -]?model', t, re.I)
    wam_acronym = bool(re.search(r'\bWAM\b', t)) and not re.search(
        r'barrett|whole[- ]arm|\bWAM\b\s*(arm|manipulator|cable|kinematic|hand)', t, re.I)
    if wam_phrase or wam_acronym:
        topics.append('WAM')
        if 'World Model' not in topics:
            topics.append('World Model')

    # de-dupe preserve order
    seen=set(); out=[]
    for x in topics:
        if x not in seen:
            seen.add(x); out.append(x)
    # If it's autonomous driving with no other embodied content, mark it as out-of-scope separately
    return out

def is_relevant(text, topics):
    t = text.lower()
    # Must explicitly talk about robots/embodied physical systems or a well-known robot platform.
    must_have = re.compile(
        r"\brobot(ics|ic)?\b|\bhumanoid\b|\bembodied\b|\bquadruped\b|\bbiped(al)?\b|\blegged( robot)?\b|"
        r"\blocomotion\b|\bdexter(ous|ity)\b|\bteleop(eration|er)?\b|\bbimanual\b|\bmanipulator\b|"
        r"\brobotic arm\b|\bgrasp(ing|er)?\b|\bmobile manipulation\b|\bsurgical robot\b|\bsim2real\b|"
        r"\bunitree\b|\bboston dynamics\b|\ballegro hand\b|\bshadow hand\b|\bbarrett hand\b|\bfranka\b|"
        r"\bpanda\b(?! )|\bkuka\b|\bur\s?\d\b|\bsawyer\b|\bbaxter\b|\bfetch robot\b|\baloha\b|\bmujoco\b|"
        r"\bisaac( sim| lab|gym)?\b|\bhabitat\b|\brobosuite\b|\bmaniskill\b|\bwam\b|\bwhole[- ]arm\b|"
        r"\brobotic manipulation\b|\bvision[- ]language[- ]action\b|\bvla\b"
    )
    if not must_have.search(t):
        return False
    # Exclude "robotic process automation/assessment" style business-process papers.
    if re.search(r"\brobotic process\b|\brobot process (automation|assessment|mining)\b|\brpa\b", t):
        if not re.search(r"\bmanipulat|\bgrasp|\bhumanoid|\bembodied|\bmobile robot|\brobotic arm|\blegged|\blocomotion|\bnavigat|\bteleop|\bdexter|\bbimanual", t):
            return False
    # Reject obvious non-robotics domains that reuse words like 'policy' / 'agent'.
    bad_domains = re.compile(
        r"financial|stock market|trading|blockchain|cryptocurrency|electronic health record|electronic medical record|"
        r"drug discovery|protein folding|molecular dynamics|natural language processing|recommender system|social network|"
        r"clinical trial|rag poisoning|database transaction|acid-compliant|audit-repair|process assessment|process benchmark"
    )
    if bad_domains.search(t):
        if not re.search(r"\brobot(ic|s)?\b|\bmanipulat|\bgrasp|\bhumanoid|\bembodied|\bsurgical robot", t):
            return False
    return True

def http_get(url, timeout=30):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, context=CTX, timeout=timeout) as r:
        return r.read()

# ---------- Hugging Face ----------
def fetch_hf_days(days=14):
    out = []
    today = datetime.now(timezone.utc).date()
    for i in range(days):
        d = today - timedelta(days=i)
        ds = d.isoformat()
        url = f'https://huggingface.co/api/daily_papers?date={ds}'
        try:
            raw = http_get(url)
            data = json.loads(raw)
        except Exception as e:
            print(f'[hf] skip {ds}: {e}', file=sys.stderr); continue
        if not isinstance(data, list): continue
        for item in data:
            meta = item.get('paper') or item
            pid = meta.get('id') or item.get('id')
            title = (meta.get('title') or '').strip().replace('\n',' ')
            summary = (meta.get('summary') or meta.get('abstract') or '').strip().replace('\n',' ')
            authors = ', '.join([(a.get('name') if isinstance(a,dict) else str(a))
                                 for a in (meta.get('authors') or []) if a])
            upvotes = meta.get('upvotes') or item.get('upvotes') or 0
            pdf = meta.get('pdf')
            aid = re.search(r'(\d{4}\.\d{4,5})', str(pid));
            if not aid: continue
            arxid = aid.group(1)
            text = f'{title} {summary} {authors}'
            topics = classify_topics(text)
            if not is_relevant(text, topics):
                continue
            out.append({
                'id': arxid,
                'title': ' '.join(title.split()),
                'abstract': ' '.join(summary.split()),
                'authors': ' '.join(authors.split()),
                'date': ds,
                'published': ds,
                'url': f'https://huggingface.co/papers/{arxid}',
                'hfUrl': f'https://huggingface.co/papers/{arxid}',
                'arxiv': f'https://arxiv.org/abs/{arxid}',
                'pdf': pdf or f'https://arxiv.org/pdf/{arxid}.pdf',
                'upvotes': int(upvotes or 0),
                'tags': topics[:5],
                'topics': topics,
                'source': 'hf',
            })
        time.sleep(0.2)
    return out

# ---------- arXiv ----------
ARXIV_NS = {'a':'http://www.w3.org/2005/Atom','arxiv':'http://arxiv.org/schemas/atom'}

def parse_arxiv(xml_bytes):
    root = ET.fromstring(xml_bytes)
    entries = []
    for e in root.findall('a:entry', ARXIV_NS):
        raw_id = (e.findtext('a:id', default='', namespaces=ARXIV_NS) or '').strip()
        title = (e.findtext('a:title', default='', namespaces=ARXIV_NS) or '').strip()
        summary = (e.findtext('a:summary', default='', namespaces=ARXIV_NS) or '').strip()
        published = (e.findtext('a:published', default='', namespaces=ARXIV_NS) or '')[:10]
        updated = (e.findtext('a:updated', default='', namespaces=ARXIV_NS) or '')[:10]
        authors = []
        for a in e.findall('a:author', ARXIV_NS):
            nm = a.findtext('a:name', default='', namespaces=ARXIV_NS)
            if nm: authors.append(nm.strip())
        cats = [c.attrib.get('term','') for c in e.findall('a:category', ARXIV_NS)]
        m = re.search(r'(\d{4}\.\d{4,5})', raw_id)
        if not m or not title or not summary: continue
        arxid = m.group(1)
        entries.append({
            'id': arxid,
            'title': ' '.join(title.split()),
            'abstract': ' '.join(summary.split()),
            'authors': ', '.join(authors),
            'date': published or updated,
            'published': published,
            'url': f'https://arxiv.org/abs/{arxid}',
            'arxiv': f'https://arxiv.org/abs/{arxid}',
            'pdf': f'https://arxiv.org/pdf/{arxid}.pdf',
            'upvotes': 0,
            'categories': cats,
            'source': 'arxiv',
        })
    return entries

def fetch_arxiv_max(query, start=0, max_results=200):
    params = {
        'search_query': query,
        'sortBy': 'submittedDate',
        'sortOrder': 'descending',
        'start': start,
        'max_results': max_results,
    }
    url = 'https://export.arxiv.org/api/query?' + urllib.parse.urlencode(params)
    raw = http_get(url, timeout=45)
    return parse_arxiv(raw)

def fetch_arxiv(lookback_days=7, per_query=200):
    """
    Fire multiple arXiv queries to maximize recall.
    We cast a wide net across categories and combine with OR keywords.
    """
    cats = ['cs.RO','cs.AI','cs.CV','cs.LG','cs.MA','eess.SY','stat.ML','cs.HC']
    cat_or = '+OR+'.join([f'cat:{c}' for c in cats])
    # Broad keyword OR on title+abstract
    kw_or = '+OR+'.join([
        'all:embodied','all:robot','all:robotic','all:robotics','all:manipulation','all:manipulator',
        'all:grasping','all:grasp','all:dexterous','all:humanoid','all:locomotion','all:legged',
        'all:navigation','all:teleoperation','all:bimanual','all:sim2real','all:"vision-language-action"',
        'all:"diffusion+policy"','all:"behavior+cloning"','all:"imitation+learning"','all:"world+model"',
        'all:VLA','all:"mobile+manipulation"','all:"end-to-end+control"','all:"motion+planning"',
        'all:unitree','all:"pi+0"','all:π0','all:openvla','all:"open+vla"','all:octo',
        'all:aloha','all:franka','all:allegro','all:mujoco','all:isaac','all:"world+action+model"','ti:WAM','abs:"world+action+model"'
    ])
    queries = [
        f'({cat_or})+AND+({kw_or})',
        # fall-back: explicit robot phrase even without cat matches
        f'ti:"robot"',
        f'ti:"humanoid"',
        f'ti:"VLA"',
        f'ti:"grasping"+OR+ti:"manipulation"',
        f'(ti:WAM+OR+abs:"world action model"+OR+abs:"world-action model"+OR+ti:"world action model")+AND+(all:robot+OR+all:robotic+OR+all:embodied+OR+all:manipulation+OR+all:humanoid+OR+all:navigation)',
    ]
    out, seen = [], set()
    cutoff = (datetime.now(timezone.utc).date() - timedelta(days=lookback_days)).isoformat()
    for q in queries:
        try:
            entries = fetch_arxiv_max(q, start=0, max_results=per_query)
        except Exception as e:
            print(f'[arxiv] query failed ({q[:60]}...): {e}', file=sys.stderr)
            time.sleep(3.1); continue
        kept = 0
        for ent in entries:
            if ent['id'] in seen: continue
            # Only keep papers within the lookback window
            if (ent.get('date') or '0000-00-00') < cutoff: continue
            text = f"{ent['title']} {ent['abstract']} {' '.join(ent.get('categories',[]))}"
            topics = classify_topics(text)
            if not is_relevant(text, topics): continue
            ent['topics'] = topics
            ent['tags'] = topics[:5]
            out.append(ent); seen.add(ent['id']); kept += 1
        print(f'[arxiv] query kept {kept} new entries', file=sys.stderr)
        time.sleep(3.1)  # respect arXiv rate limit
    return out

# ---------- History ----------
def load_history():
    if HISTORY_PATH.exists():
        try:
            data = json.loads(HISTORY_PATH.read_text(encoding='utf-8'))
            if isinstance(data, dict) and 'papers' in data:
                return data
        except Exception:
            pass
    return {'papers': {}, 'generatedAt': None}

def save_history(hist):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_PATH.write_text(json.dumps(hist, ensure_ascii=False, indent=2), encoding='utf-8')

def merge_into_history(hist, new_papers):
    """Merge fetched papers into persistent history by id, never deleting old entries."""
    now = datetime.now(timezone.utc).isoformat()
    papers = hist.setdefault('papers', {})
    added = 0
    for p in new_papers:
        cur = papers.get(p['id'])
        if cur is None:
            papers[p['id']] = p
            added += 1
        else:
            # Update mutable fields (HF upvotes may grow over time)
            cur['upvotes'] = max(int(cur.get('upvotes',0)), int(p.get('upvotes',0)))
            cur['topics'] = list(dict.fromkeys((p.get('topics') or []) + (cur.get('topics') or [])))[:8]
            cur['tags'] = cur['topics'][:5]
            if p.get('source') == 'hf': cur['source'] = 'hf'  # hf as "verified" source
            if p.get('hfUrl'): cur['hfUrl'] = p['hfUrl']
            # Keep earliest date seen
            if not cur.get('date') or (p.get('date') and p['date'] < cur['date']):
                cur['date'] = p['date']
    hist['generatedAt'] = now
    return added

# ---------- Build ----------
def build_bundle(hist, recent_days=7, archive_days=5*365, limit=80, archive_limit=5000):
    hf = fetch_hf_days(days=14)
    arx = fetch_arxiv(lookback_days=7, per_query=200)
    # Merge sources by id (hf wins over arxiv when same id)
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
    # Merge into history
    added = merge_into_history(hist, papers)
    # Build two views:
    #   - recent: last `recent_days` days (shown on the homepage's "最新" panel)
    #   - archive: everything older than `recent_days` but within `archive_days`
    all_hist = list(hist['papers'].values())
    today = datetime.now(timezone.utc).date()
    recent_cutoff = (today - timedelta(days=recent_days)).isoformat()
    archive_cutoff = (today - timedelta(days=archive_days)).isoformat()
    def keyf(p):
        return ((p.get('date') or '0000-00-00'),
                1 if p.get('source')=='hf' else 0,
                int(p.get('upvotes') or 0),
                len(p.get('topics') or []))
    recent = sorted([p for p in all_hist if (p.get('date') or '0000-00-00') >= recent_cutoff], key=keyf, reverse=True)
    archive = sorted([p for p in all_hist
                       if archive_cutoff <= (p.get('date') or '0000-00-00') < recent_cutoff],
                      key=keyf, reverse=True)
    recent = recent[:limit]
    archive = archive[:archive_limit]
    bundle = {
        'generatedAt': hist.get('generatedAt'),
        'recentDays': recent_days,
        'archiveDays': archive_days,
        'recentCutoff': recent_cutoff,
        'archiveCutoff': archive_cutoff,
        'addedToday': added,
        'historyTotal': len(hist.get('papers',{})),
        'count': len(recent),
        'archiveCount': len(archive),
        'sources': {
            'hf': sum(1 for p in recent if p.get('source')=='hf'),
            'arxiv': sum(1 for p in recent if p.get('source')=='arxiv'),
        },
        'archiveSources': {
            'hf': sum(1 for p in archive if p.get('source')=='hf'),
            'arxiv': sum(1 for p in archive if p.get('source')=='arxiv'),
        },
        'warnings': [],
        'papers': recent,
        'archive': archive,
    }
    if bundle['count'] == 0:
        bundle['warnings'].append('zero_papers')
    if added == 0 and len(hist.get('papers',{})) > 50:
        bundle['warnings'].append('zero_new_today')
    return bundle

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--stdout', action='store_true')
    ap.add_argument('--recent', type=int, default=7, help='how many days to show in "latest" (default 7)')
    ap.add_argument('--archive', type=int, default=5*365, help='how many days back the "archive" tab covers (default 365)')
    ap.add_argument('--limit', type=int, default=80, help='max papers shown in "latest"')
    ap.add_argument('--archive-limit', dest='archive_limit', type=int, default=5000, help='max papers shown in "archive"')
    args = ap.parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    hist = load_history()
    bundle = build_bundle(hist, recent_days=args.recent, archive_days=args.archive, limit=args.limit, archive_limit=args.archive_limit)
    save_history(hist)
    OUT_PATH.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'[build] wrote {OUT_PATH}: latest={bundle["count"]} (HF={bundle["sources"]["hf"]}, arXiv={bundle["sources"]["arxiv"]}), '
          f'archive={bundle["archiveCount"]} (HF={bundle["archiveSources"]["hf"]}, arXiv={bundle["archiveSources"]["arxiv"]}), '
          f'addedToday={bundle["addedToday"]}, historyTotal={bundle["historyTotal"]})')
    if bundle['warnings']:
        print('[build] warnings:', ','.join(bundle['warnings']))
    if args.stdout:
        json.dump(bundle, sys.stdout, ensure_ascii=False, indent=2); sys.stdout.write('\n')

if __name__ == '__main__':
    main()
