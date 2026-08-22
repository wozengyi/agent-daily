#!/usr/bin/env python3
"""Validate generated Agent Daily data before committing or deploying."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    return json.loads((ROOT / name).read_text(encoding='utf-8'))


def fail(message):
    print(f'[validate] {message}', file=sys.stderr)
    raise SystemExit(1)


def main():
    daily = load('data/daily.json')
    latest = load('data/latest.json')
    if not isinstance(daily.get('papers'), list) or not isinstance(latest.get('papers'), list):
        fail('daily/latest papers must be arrays')
    recent_total = latest.get('recentTotal') or len(latest['papers'])
    sources = latest.get('sources') or {}
    fetch_stats = latest.get('fetchStats') or daily.get('fetchStats') or {}
    if recent_total <= 0:
        fail(f'recentTotal too low: {recent_total}')
    if (sources.get('arxiv') or 0) <= 0:
        fail(f'latest arXiv source count is empty: {sources.get("arxiv")}')
    if fetch_stats and (fetch_stats.get('arxiv') or 0) <= 0:
        fail(f'current arXiv fetch count is empty: {fetch_stats.get("arxiv")}')
    fatal_warnings = {'zero_papers', 'empty_arxiv_fetch', 'empty_current_fetch'}
    warnings = set(latest.get('warnings') or [])
    if warnings & fatal_warnings:
        fail(f'fatal warnings present: {sorted(warnings & fatal_warnings)}')
    print(f'[validate] ok: recentTotal={recent_total}, sources={sources}, fetchStats={fetch_stats}')


if __name__ == '__main__':
    main()
