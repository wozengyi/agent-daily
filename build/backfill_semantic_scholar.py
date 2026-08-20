#!/usr/bin/env python3
"""Seed Agent Daily history from Semantic Scholar bulk search.

This is faster than arXiv month-by-month backfill and also preserves venue /
publication type metadata so the frontend can filter conference, journal, and
preprint papers.
"""
import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'build'))
import build_daily as bd

S2_URL = 'https://api.semanticscholar.org/graph/v1/paper/search/bulk'
FIELDS = ','.join([
    'paperId', 'title', 'abstract', 'authors', 'year', 'publicationDate',
    'url', 'openAccessPdf', 'venue', 'publicationVenue', 'publicationTypes',
    'externalIds', 'citationCount',
])

QUERIES = [
    '"llm agent"',
    '"language model agent"',
    '"multi-agent" "large language model"',
    '"tool use" "large language model"',
    '"function calling" "large language model"',
    '"web agent" "large language model"',
    '"computer use" "large language model"',
    '"code agent" "large language model"',
    '"agent safety" "large language model"',
    '"prompt injection" "large language model"',
    '"jailbreak" "large language model"',
    '"post training" "large language model"',
    '"instruction tuning" "large language model"',
    '"RLHF" "large language model"',
    '"DPO" "large language model"',
    '"vision language model"',
    '"VLM" "instruction tuning"',
    '"reasoning" "large language model"',
    '"planning" "language agent"',
    '"memory" "language agent"',
    '"agent benchmark" "large language model"',
    '"alignment" "large language model"',
    '"hallucination" "large language model"',
    '"interpretability" "large language model"',
]

CONFERENCE_HINTS = re.compile(
    r'\b('
    r'neurips|nips|iclr|icml|acl|emnlp|naacl|eacl|coling|cvpr|iccv|eccv|aaai|ijcai|kdd|www|webconf|'
    r'sigir|chi|uist|icse|fse|ase|issta|osdi|sosp|nsdi|usenix|icra|iros|rss|corl|aistats|colm'
    r')\b|conference|proceedings|symposium|workshop',
    re.I,
)
JOURNAL_HINTS = re.compile(
    r'journal|transactions|magazine|review|survey|computing surveys|nature|science|cell|pnas',
    re.I,
)


def fetch_json(params, timeout=60, retries=0):
    url = S2_URL + '?' + urllib.parse.urlencode(params)
    attempt = 0
    while retries <= 0 or attempt < retries:
        attempt += 1
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'AgentDaily/1.0'})
            with urllib.request.urlopen(req, timeout=timeout, context=bd.CTX) as r:
                return json.loads(r.read().decode('utf-8'))
        except Exception as e:
            wait = min(180, 8 * attempt)
            budget = '∞' if retries <= 0 else str(retries)
            print(f'  retry {attempt}/{budget} in {wait}s: {e}', file=sys.stderr, flush=True)
            time.sleep(wait)
    raise RuntimeError(f'failed Semantic Scholar request: {url[:140]}...')


def clean_text(value):
    return ' '.join(str(value or '').split())


def arxiv_url(arxiv_id):
    if not arxiv_id:
        return None
    return 'https://arxiv.org/abs/' + clean_arxiv_id(arxiv_id)


def clean_arxiv_id(arxiv_id):
    return re.sub(r'v\d+$', '', str(arxiv_id or ''))


def infer_kind(paper):
    types = ' '.join(paper.get('publicationTypes') or [])
    venue = clean_text(paper.get('venue'))
    venue_obj = paper.get('publicationVenue') or {}
    venue_name = clean_text(venue_obj.get('name'))
    venue_type = clean_text(venue_obj.get('type')).lower()
    hay = ' '.join([types, venue, venue_name, venue_type])
    if 'conference' in venue_type or CONFERENCE_HINTS.search(hay):
        return 'conference'
    if 'journal' in venue_type or JOURNAL_HINTS.search(hay):
        return 'journal'
    if paper.get('externalIds', {}).get('ArXiv') and not (venue or venue_name):
        return 'preprint'
    if re.search(r'arxiv|preprint', hay, re.I):
        return 'preprint'
    return 'other'


def normalize(paper):
    title = clean_text(paper.get('title'))
    abstract = clean_text(paper.get('abstract'))
    if not title or not bd.is_relevant(f'{title} {abstract}'):
        return None
    topics = bd.classify_topics(title, abstract)
    if not topics:
        return None

    external = paper.get('externalIds') or {}
    arxiv_id = external.get('ArXiv')
    arxiv = arxiv_url(arxiv_id)
    paper_id = paper.get('paperId')
    if arxiv_id:
        item_id = 'arxiv:' + clean_arxiv_id(arxiv_id)
    elif paper_id:
        item_id = 's2:' + paper_id
    else:
        return None

    venue_obj = paper.get('publicationVenue') or {}
    venue = clean_text(paper.get('venue')) or clean_text(venue_obj.get('name'))
    year = paper.get('year')
    pub_date = paper.get('publicationDate') or (f'{year}-01-01' if year else '')
    authors = ', '.join(clean_text(a.get('name')) for a in (paper.get('authors') or []) if a.get('name'))
    pdf = (paper.get('openAccessPdf') or {}).get('url')
    kind = infer_kind(paper)

    return {
        'id': item_id,
        'title': title,
        'abstract': abstract,
        'authors': authors,
        'date': pub_date,
        'published': pub_date,
        'year': year,
        'venue': venue or ('arXiv' if arxiv else 'Semantic Scholar'),
        'publicationKind': kind,
        'publicationTypes': paper.get('publicationTypes') or [],
        'citationCount': int(paper.get('citationCount') or 0),
        'source': 'semantic-scholar',
        'url': paper.get('url') or arxiv,
        'arxiv': arxiv,
        'pdf': pdf or (f'https://arxiv.org/pdf/{clean_arxiv_id(arxiv_id)}.pdf' if arxiv_id else None),
        'upvotes': 0,
        'topics': topics,
        'tags': topics[:5],
    }


def merge_preserving_existing(hist, papers):
    existing = hist.setdefault('papers', {})
    added = updated = 0
    for paper in papers:
        cur = existing.get(paper['id'])
        if not cur:
            existing[paper['id']] = paper
            added += 1
            continue
        for key in ['venue', 'publicationKind', 'publicationTypes', 'citationCount', 'url', 'pdf', 'published', 'year']:
            if paper.get(key) and not cur.get(key):
                cur[key] = paper[key]
        if paper.get('citationCount') and paper.get('citationCount', 0) > int(cur.get('citationCount') or 0):
            cur['citationCount'] = paper['citationCount']
        cur['topics'] = list(dict.fromkeys(list(cur.get('topics') or []) + list(paper.get('topics') or [])))[:8]
        cur['tags'] = cur['topics'][:5]
        updated += 1
    hist['generatedAt'] = datetime.now(timezone.utc).isoformat()
    return added, updated


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--years', type=int, default=5)
    ap.add_argument('--pages-per-query', type=int, default=0, help='0 means follow every Semantic Scholar page')
    ap.add_argument('--sleep', type=float, default=3.0)
    ap.add_argument('--max-total', type=int, default=0, help='0 means no global cap')
    ap.add_argument('--max-per-year', type=int, default=0, help='0 means no yearly cap')
    ap.add_argument('--max-retries', type=int, default=0, help='0 means retry Semantic Scholar requests until the workflow timeout')
    ap.add_argument('--oldest-first', action='store_true')
    ap.add_argument('--recent', type=int, default=7)
    ap.add_argument('--limit', type=int, default=240)
    args = ap.parse_args()

    year_end = date.today().year
    year_start = year_end - args.years
    hist = bd.load_history()
    before = len(hist.get('papers', {}))
    existing_ids = set(hist.get('papers', {}).keys())
    collected = []
    seen = set()

    print(f'Semantic Scholar backfill: {year_start}-{year_end}, {len(QUERIES)} queries')
    year_order = range(year_start, year_end + 1) if args.oldest_first else range(year_end, year_start - 1, -1)
    def hit_total():
        return args.max_total > 0 and len(collected) >= args.max_total
    for year in year_order:
        kept_for_year = 0
        def hit_year():
            return args.max_per_year > 0 and kept_for_year >= args.max_per_year
        for idx, query in enumerate(QUERIES, 1):
            if hit_year() or hit_total():
                break
            token = None
            kept_for_query = 0
            page = 0
            while True:
                if args.pages_per_query > 0 and page >= args.pages_per_query:
                    break
                params = {
                    'query': query,
                    'fields': FIELDS,
                    'year': str(year),
                    'fieldsOfStudy': 'Computer Science',
                }
                if token:
                    params['token'] = token
                try:
                    data = fetch_json(params, retries=args.max_retries)
                except Exception as e:
                    print(f'[{year} {idx}/{len(QUERIES)}] {query}: skipped after retries: {e}', file=sys.stderr, flush=True)
                    break
                token = data.get('token')
                for raw in data.get('data') or []:
                    paper = normalize(raw)
                    if not paper or paper['id'] in existing_ids or paper['id'] in seen:
                        continue
                    seen.add(paper['id'])
                    collected.append(paper)
                    kept_for_query += 1
                    kept_for_year += 1
                    if hit_year() or hit_total():
                        break
                print(f'[{year} {idx}/{len(QUERIES)}] {query}: +{kept_for_query}, year={kept_for_year}, total={len(collected)}', flush=True)
                page += 1
                if hit_year() or hit_total() or not token:
                    break
                time.sleep(args.sleep)
            time.sleep(args.sleep)
        if hit_total():
            break

    added, updated = merge_preserving_existing(hist, collected)
    bd.save_history(hist)
    bundle = bd.build_bundle(hist, recent_days=args.recent, archive_days=args.years * 365, limit=args.limit, archive_limit=0)
    bd.save(hist, bundle)
    after = len(hist.get('papers', {}))
    print(f'Done. history {before} -> {after} (+{added}, updated={updated}); '
          f'recent={bundle["count"]}, archiveTotal={bundle["archiveTotal"]}')


if __name__ == '__main__':
    main()
