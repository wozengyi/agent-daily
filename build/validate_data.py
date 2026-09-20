#!/usr/bin/env python3
"""Validate generated Agent Daily data before committing or deploying."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP_START = '/* AGENT_DAILY_BOOTSTRAP_START */'
BOOTSTRAP_END = '/* AGENT_DAILY_BOOTSTRAP_END */'
BOOTSTRAP_PREFIX = 'window.__BUNDLE__='


def load(name):
    return json.loads((ROOT / name).read_text(encoding='utf-8'))


def fail(message):
    print(f'[validate] {message}', file=sys.stderr)
    raise SystemExit(1)


def load_bootstrap():
    html = (ROOT / 'index.html').read_text(encoding='utf-8')
    start = html.find(BOOTSTRAP_START)
    end = html.find(BOOTSTRAP_END, start + len(BOOTSTRAP_START))
    payload_start = html.find(BOOTSTRAP_PREFIX, start + len(BOOTSTRAP_START))
    if start < 0 or end < 0 or payload_start < 0 or payload_start >= end:
        fail('index.html bootstrap markers or payload are missing')
    payload_start += len(BOOTSTRAP_PREFIX)
    payload_end = html.rfind(';', payload_start, end)
    if payload_end < payload_start:
        fail('index.html bootstrap payload terminator is missing')
    try:
        return json.loads(html[payload_start:payload_end])
    except json.JSONDecodeError as exc:
        fail(f'index.html bootstrap payload is invalid JSON: {exc}')


def main():
    daily = load('data/daily.json')
    latest = load('data/latest.json')
    bootstrap = load_bootstrap()
    if not isinstance(daily.get('papers'), list) or not isinstance(latest.get('papers'), list):
        fail('daily/latest papers must be arrays')
    if bootstrap.get('generatedAt') != daily.get('generatedAt'):
        fail(
            'index.html bootstrap is stale: '
            f'{bootstrap.get("generatedAt")} != {daily.get("generatedAt")}'
        )
    if not isinstance(bootstrap.get('papers'), list):
        fail('index.html bootstrap papers must be an array')
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
    print(
        f'[validate] ok: generatedAt={daily.get("generatedAt")}, '
        f'recentTotal={recent_total}, sources={sources}, fetchStats={fetch_stats}'
    )


if __name__ == '__main__':
    main()
