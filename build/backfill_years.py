"""Backfill arXiv history for up to `years` years, month by month, paging through results.

Results are classified/deduplicated and merged into data/history.json so subsequent
daily builds can serve them through the "往期" (Archive) tab.
"""
import time, re, json, urllib.request, urllib.parse, sys, xml.etree.ElementTree as ET
from datetime import date, datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'build'))
import build_daily as bd

ARXIV_NS = {'a':'http://www.w3.org/2005/Atom'}

def fetch_page(query, start, max_results=100):
    params = {
        'search_query': query,
        'sortBy': 'submittedDate',
        'sortOrder': 'descending',
        'start': start,
        'max_results': max_results,
    }
    url = 'https://export.arxiv.org/api/query?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0 EmbodiedDaily/Backfill'})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=45, context=bd.CTX) as r:
                return r.read()
        except Exception as e:
            wait = 5*(attempt+1)
            print(f'  retry {attempt+1}/5 in {wait}s: {e}', file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError(f'failed to fetch {url}')

def parse(xml_bytes):
    root = ET.fromstring(xml_bytes)
    total = int(root.findtext('{http://a9.com/-/spec/opensearch/1.1/}totalResults') or 0)
    entries = []
    for e in root.findall('a:entry', ARXIV_NS):
        raw_id = (e.findtext('a:id', default='', namespaces=ARXIV_NS) or '').strip()
        m = re.search(r'(\d{4}\.\d{4,5})', raw_id)
        if not m: continue
        arxid = m.group(1)
        title = ' '.join((e.findtext('a:title', default='', namespaces=ARXIV_NS) or '').split())
        summ = ' '.join((e.findtext('a:summary', default='', namespaces=ARXIV_NS) or '').split())
        pub = (e.findtext('a:published', default='', namespaces=ARXIV_NS) or '')[:10]
        upd = (e.findtext('a:updated', default='', namespaces=ARXIV_NS) or '')[:10]
        authors = []
        for a in e.findall('a:author', ARXIV_NS):
            n = a.findtext('a:name', default='', namespaces=ARXIV_NS)
            if n: authors.append(n.strip())
        cats = [c.attrib.get('term','') for c in e.findall('a:category', ARXIV_NS)]
        entries.append({
            'id': f'arxiv:{arxid}',
            'title': title,
            'abstract': summ,
            'authors': ', '.join(authors),
            'date': pub or upd,
            'published': pub,
            'arxiv': f'https://arxiv.org/abs/{arxid}',
            'pdf': f'https://arxiv.org/pdf/{arxid}.pdf',
            'upvotes': 0,
            'categories': cats,
            'source': 'arxiv',
        })
    return total, entries

def month_ranges(years):
    end = date.today() - timedelta(days=8)  # exclude last 7 days (covered by daily builds)
    start = date(end.year - years, end.month, 1)
    # iterate months from start to end
    y, m = start.year, start.month
    while True:
        if m == 12:
            ny, nm = y+1, 1
        else:
            ny, nm = y, m+1
        mstart = date(y,m,1)
        mend = date(ny,nm,1) - timedelta(days=1)
        if mstart > end: break
        yield mstart, min(mend, end)
        y, m = ny, nm

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--years', type=int, default=5)
    ap.add_argument('--max-per-month', type=int, default=300, help='cap papers fetched per month to keep runtime reasonable')
    ap.add_argument('--page-size', type=int, default=100)
    ap.add_argument('--sleep', type=float, default=3.2)
    args = ap.parse_args()

    cats = ['cs.AI','cs.CL','cs.LG','cs.CV','cs.SE','cs.IR','cs.HC','stat.ML']
    cat_query = ' OR '.join([f'cat:{c}' for c in set(cats)])
    # Broad agent/LLM query. This over-retrieves; is_relevant() filters down.
    kws = [
        'agent','agentic','"llm agent"','"multi agent"','"multi-agent"',
        '"tool use"','"function calling"','"tool learning"',
        '"agentic search"','"web agent"','"browser agent"','"computer use"',
        '"agent safety"','"llm safety"','jailbreak','"prompt injection"',
        '"error attribution"','"failure attribution"',
        '"post training"','post-training','rlhf','dpo','grpo','"preference optimization"',
        '"large language model training"','"llm training"','pretraining','"instruction tuning"',
        '"vision language model"','vlm','"visual instruction tuning"',
        'reasoning','"chain of thought"','"tree of thought"',
        'planning','memory','reflection','"self correction"',
        '"code agent"','"software engineering agent"',
        'benchmark','evaluation','alignment','hallucination','interpretability',
    ]
    def kw_expr(k):
        if k.startswith('"') and k.endswith('"'):
            return 'all:' + k.replace(' ', '+')
        return f'all:{k.replace(" ","+")}' if ' ' in k else f'all:{k}'

    hist = bd.load_history()
    papers = hist.setdefault('papers', {})
    before = len(papers)
    total_added = 0

    months = list(month_ranges(args.years))
    print(f'Backfilling {len(months)} months, {args.years} years back (max {args.max_per_month} per month)')

    for i,(ms,me) in enumerate(months,1):
        print(f'[{i}/{len(months)}] {ms}..{me}', flush=True)
        month_added = 0
        seen_month = set()
        for kw in kws:
            if month_added >= args.max_per_month:
                break
            q = f'({cat_query}) AND {kw_expr(kw)} AND submittedDate:[{ms.strftime("%Y%m%d")}0000 TO {me.strftime("%Y%m%d")}2359]'
            try:
                xml = fetch_page(q, start=0, max_results=args.page_size)
                total, entries = parse(xml)
            except Exception as e:
                print(f'  skip keyword {kw}: {e}', file=sys.stderr)
                time.sleep(args.sleep)
                continue
            if not entries:
                time.sleep(args.sleep)
                continue
            for ent in entries:
                if month_added >= args.max_per_month:
                    break
                if ent['id'] in papers or ent['id'] in seen_month: continue
                seen_month.add(ent['id'])
                text = f"{ent['title']} {ent['abstract']} {' '.join(ent.get('categories',[]))}"
                topics = bd.classify_topics(ent['title'], ent['abstract'])
                if not bd.is_relevant(text):
                    continue
                ent['topics'] = topics
                ent['tags'] = topics[:5]
                papers[ent['id']] = ent
                total_added += 1; month_added += 1
            time.sleep(args.sleep)
        print(f'  +{month_added} new, total so far {len(papers)}', flush=True)
        time.sleep(args.sleep)
        # Persist incrementally so interruptions don't lose progress
        hist['generatedAt'] = datetime.now(timezone.utc).isoformat()
        bd.save_history(hist)

    # Regenerate bundle using the augmented history
    bundle = bd.build_bundle(hist, recent_days=7, archive_days=args.years*365, limit=80, archive_limit=0)
    bd.OUT_PATH.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding='utf-8')
    bd.write_archive_shards(hist, bundle)
    bd.write_search_index(hist)
    print(f'Done. history: {before} -> {len(papers)} (+{total_added}), '
          f'latest={bundle["count"]}, archive={bundle["archiveCount"]}')

if __name__ == '__main__':
    main()
