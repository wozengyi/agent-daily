#!/usr/bin/env python3
"""Incrementally backfill multi-year history for Agent Daily."""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from build_daily import load_history, merge_into_history, fetch_arxiv, fetch_hf_days, parse_arxiv_xml, fetch_page, log, classify_topics, is_relevant, norm_paper_id, DATA_DIR, HIST_PATH
from datetime import datetime, timedelta, timezone
import urllib.parse, urllib.request

def fetch_arxiv_month(year, month, per_query=200):
    """Fetch arxiv for one calendar month using date range queries."""
    start = f"{year:04d}{month:02d}010000"
    if month == 12:
        end = f"{year+1:04d}01010000"
    else:
        end = f"{year:04d}{month+1:02d}010000"
    queries = [
        f'all:agent AND submittedDate:[{start} TO {end}]',
        f'all:"llm agent" AND submittedDate:[{start} TO {end}]',
        f'all:"multi-agent" AND submittedDate:[{start} TO {end}]',
        f'all:"tool use" AND submittedDate:[{start} TO {end}]',
        f'all:agentic AND submittedDate:[{start} TO {end}]',
        f'all:RAG AND submittedDate:[{start} TO {end}]',
        f'all:"retrieval augmented" AND submittedDate:[{start} TO {end}]',
        f'all:"agent safety" AND submittedDate:[{start} TO {end}]',
        f'all:"llm safety" AND submittedDate:[{start} TO {end}]',
        f'all:jailbreak AND submittedDate:[{start} TO {end}]',
        f'all:"prompt injection" AND submittedDate:[{start} TO {end}]',
        f'all:"error attribution" AND submittedDate:[{start} TO {end}]',
        f'all:"post-training" AND submittedDate:[{start} TO {end}]',
        f'all:RLHF AND submittedDate:[{start} TO {end}]',
        f'all:DPO AND submittedDate:[{start} TO {end}]',
        f'all:GRPO AND submittedDate:[{start} TO {end}]',
        f'all:"fine-tuning" AND all:llm AND submittedDate:[{start} TO {end}]',
        f'all:"vision language model" AND submittedDate:[{start} TO {end}]',
        f'all:VLM AND submittedDate:[{start} TO {end}]',
        f'all:"chain of thought" AND submittedDate:[{start} TO {end}]',
        f'all:"reasoning" AND all:"language model" AND submittedDate:[{start} TO {end}]',
        f'all:"world model" AND all:agent AND submittedDate:[{start} TO {end}]',
        f'all:"code agent" AND submittedDate:[{start} TO {end}]',
        f'all:"web agent" AND submittedDate:[{start} TO {end}]',
        f'all:"computer use" AND submittedDate:[{start} TO {end}]',
        f'all:"agent benchmark" AND submittedDate:[{start} TO {end}]',
        f'all:interpretability AND all:llm AND submittedDate:[{start} TO {end}]',
    ]
    out = []
    seen = set()
    for q in queries:
        url = (f'http://export.arxiv.org/api/query?search_query={urllib.parse.quote(q)}'
               f'&start=0&max_results={per_query}&sortBy=submittedDate&sortOrder=descending')
        try:
            raw = fetch_page(url)
            for p in parse_arxiv_xml(raw):
                d = p['date']
                try:
                    dt = datetime.fromisoformat(d).date()
                    if not (dt.year == year and dt.month == month): continue
                except: continue
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
        except Exception as e:
            log(f'  query error: {e}')
        time.sleep(3.5)
    return out

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--years', type=int, default=5)
    ap.add_argument('--max-per-month', type=int, default=150)
    ap.add_argument('--page-size', type=int, default=100)
    args = ap.parse_args()

    hist = load_history()
    start_year = datetime.now(timezone.utc).year - args.years + 1
    end_year = datetime.now(timezone.utc).year
    total_added = 0
    DATA_DIR.mkdir(exist_ok=True)
    for year in range(start_year, end_year+1):
        for month in range(1, 13):
            if year == end_year and month >= datetime.now(timezone.utc).month: break
            log(f'Backfilling {year}-{month:02d}...')
            papers = fetch_arxiv_month(year, month, per_query=args.page_size)
            log(f'  fetched {len(papers)} relevant papers')
            added = merge_into_history(hist, papers)
            total_added += added
            if added:
                log(f'  added {added} new, total history now {len(hist["papers"])}')
                HIST_PATH.write_text(__import__('json').dumps(hist, ensure_ascii=False), encoding='utf-8')
            time.sleep(2)
    log(f'Backfill complete. Total added: {total_added}. Final history size: {len(hist["papers"])}')

if __name__ == '__main__':
    main()
