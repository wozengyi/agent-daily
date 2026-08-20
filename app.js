const STORAGE_KEY = 'agent-daily-bookmarks-v2';
const state = {
  tab: 'today',
  search: '',
  activeTags: new Set(),
  activeYears: new Set(),
  activeKinds: new Set(),
  bookmarks: new Set(JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]')),
  seedOffset: 0,
  bundle: null,
  loading: false,
  bundleError: null,
  archiveIndex: null,
  archiveIndexLoading: false,
  archiveIndexError: null,
  archiveYears: {},
  archiveLoadingYears: new Set(),
  archiveYearErrors: {},
  archiveExpandedYears: new Set(),
  archiveExpandedMonths: new Set(),
  archiveMonthLimits: {},
  searchIndex: null,
  searchIndexLoading: false,
  searchIndexError: null,
  searchResultLimit: 120,
};

function byId(id){ return document.getElementById(id); }
function saveBookmarks(){
  localStorage.setItem(STORAGE_KEY, JSON.stringify(Array.from(state.bookmarks)));
  const el = byId('bmCount'); if(el) el.textContent = state.bookmarks.size;
}
function todayKey(){ const d=new Date(); return d.getFullYear()*10000 + (d.getMonth()+1)*100 + d.getDate(); }
function seededRandom(seed){
  return function(){
    seed |= 0; seed = seed + 0x6D2B79F5 | 0;
    let t = Math.imul(seed ^ seed >>> 15, 1 | seed);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}
function uniq(arr){ return Array.from(new Set(arr)); }
function countBy(arr, pick){
  const counts = new Map();
  arr.forEach(item=>{
    (pick(item) || []).forEach(v=>counts.set(v, (counts.get(v) || 0) + 1));
  });
  return counts;
}
const KIND_LABELS = {
  conference: '会议',
  journal: '期刊',
  preprint: '预印',
  workshop: 'Workshop',
  other: '其他'
};
function inferKindFromVenue(venue, source){
  const v = (venue||'').toLowerCase();
  if(!v && (source === 'arxiv' || source === 'hf')) return 'preprint';
  if(/\barxiv\b|preprint/.test(v)) return 'preprint';
  if(/journal|transactions|proceedings of the national academy|nature|science|cell|survey|computing surveys/.test(v)) return 'journal';
  if(/conference|proceedings|symposium|workshop|\biclr\b|\bicml\b|\bneurips\b|\bnips\b|\bacl\b|\bemnlp\b|\bnaacl\b|\bcvpr\b|\biccv\b|\beccv\b|\baaai\b|\bijcai\b|\bkdd\b|\bwww\b|\bsigir\b|\bchi\b|\buist\b|\bfse\b|\bicse\b/.test(v)) return 'conference';
  return 'other';
}
function kindLabel(kind){ return KIND_LABELS[kind] || KIND_LABELS.other; }
function escapeHtml(s){
  return (s||'').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
function formatAuthors(a){
  const raw = Array.isArray(a) ? a.join(', ') : (a || '');
  const parts = String(raw).split(',').map(s=>s.trim()).filter(Boolean);
  if(parts.length <= 3) return parts.join(', ');
  return parts.slice(0,3).join(', ') + ', 等';
}
function daysAgoStr(ds){
  if(!ds) return '';
  const today = new Date(); today.setHours(0,0,0,0);
  const d = new Date(ds+'T00:00:00');
  if(isNaN(d)) return ds;
  const diff = Math.round((today - d)/(1000*60*60*24));
  if(diff===0) return '今天';
  if(diff===1) return '昨天';
  if(diff<0) return `${-diff} 天后`;
  return `${diff} 天前`;
}
function zhUrl(arxivIdOrUrl){
  const m = (arxivIdOrUrl||'').match(/(\d{4}\.\d{4,5})/);
  if(!m) return null;
  return `https://hjfy.top/arxiv/${m[1]}`;
}
function zhLink(arxivIdOrUrl, cls='btn btn-zh', label='中文'){
  const u = zhUrl(arxivIdOrUrl);
  if(!u) return '';
  return `<a class="${cls}" href="${u}" target="_blank" rel="noopener">🇨🇳 ${label}</a>`;
}

// ---------- Papers normalization ----------
function curatedAsGeneric(p){
  return {
    id: 'c:'+p.id,
    arxiv: p.arxiv,
    pdf: p.arxiv ? p.arxiv.replace('/abs/','/pdf/') : null,
    project: p.project,
    title: p.title, authors: p.authors, abstract: p.abstract||'',
    date: String(p.year), // year as pseudo-date for sorting
    year: p.year, venue: p.venue,
    upvotes: 0, source: 'classic',
    publicationKind: inferKindFromVenue(p.venue, 'classic'),
    tags: p.tags || [], topics: p.tags || [],
    why: p.why || ''
  };
}
function newAsGeneric(p){
  return {
    id: 'n:'+p.id,
    arxiv: p.arxiv, pdf: p.pdf, hfUrl: p.hfUrl, url: p.url,
    title: p.title, authors: p.authors, abstract: p.abstract||'',
    date: p.date, year: (p.date||'').slice(0,4),
    upvotes: p.upvotes||0, source: p.source,
    venue: p.venue || (p.source==='hf'?'Hugging Face Daily':(p.source==='arxiv'?'arXiv':'')),
    publicationKind: p.publicationKind || inferKindFromVenue(p.venue, p.source),
    publicationTypes: p.publicationTypes || [],
    citationCount: p.citationCount || 0,
    tags: uniq([...(p.tags||[]), ...(p.topics||[])]),
    topics: p.topics || p.tags || []
  };
}

function allNewPapers(){ return (state.bundle && state.bundle.papers || []).map(newAsGeneric); }
function allClassics(){ return PAPERS.map(curatedAsGeneric); }

// ---------- Filtering ----------
function matches(p){
  const q = state.search.trim().toLowerCase();
  if(q){
    const hay = (p.title+' '+(p.authors||'')+' '+(p.abstract||'')+' '+(p.tags||[]).join(' ')).toLowerCase();
    if(!hay.includes(q)) return false;
  }
  if(state.activeTags.size){
    const tagset = new Set(p.tags||[]);
    let ok = false;
    for(const t of state.activeTags){ if(tagset.has(t)){ ok=true; break; } }
    if(!ok) return false;
  }
  if(state.activeYears.size){
    if(!state.activeYears.has(String(p.year||(p.date||'').slice(0,4)))) return false;
  }
  if(state.activeKinds.size){
    if(!state.activeKinds.has(p.publicationKind || 'other')) return false;
  }
  return true;
}

function filtered(list){ return list.filter(matches); }

// ---------- Render helpers ----------
function sourceBadge(p){
  const kind = p.publicationKind || inferKindFromVenue(p.venue, p.source);
  if(kind === 'conference') return '<span class="src src-hf">会议</span>';
  if(kind === 'journal') return '<span class="src src-arxiv">期刊</span>';
  if(kind === 'preprint') return '<span class="src src-arxiv">预印</span>';
  if(p.source === 'hf') return '<span class="src src-hf">HF</span>';
  if(!isClassic(p)) return '<span class="src src-classic">其他</span>';
  return '<span class="src src-classic">★ 经典</span>';
}
function bookmarkBtn(id){
  const on = state.bookmarks.has(id);
  return `<button class="icon-btn bookmark ${on?'active':''}" data-bm="${id}" aria-label="收藏">${on?'★':'☆'}</button>`;
}
function newCard(p, opts={}){
  const actionLinks = [];
  if(p.hfUrl) actionLinks.push(`<a class="btn" href="${p.hfUrl}" target="_blank" rel="noopener">HF</a>`);
  if(p.arxiv) actionLinks.push(`<a class="btn" href="${p.arxiv}" target="_blank" rel="noopener">arXiv</a>`);
  if(p.pdf) actionLinks.push(`<a class="btn" href="${p.pdf}" target="_blank" rel="noopener">PDF</a>`);
  actionLinks.push(zhLink(p.arxiv||p.id.replace(/^n:/,'')));
  const topics = (p.topics||[]).slice(0,4);
  return `
  <div class="card">
    ${bookmarkBtn(p.id)}
    <div class="venue">
      ${sourceBadge(p)}
      <span style="margin-left:6px">${escapeHtml(p.date||'')} · ${escapeHtml(p.venue || daysAgoStr(p.date))}${p.citationCount?(' · 引用 '+p.citationCount):''}${p.upvotes?(' · 👍 '+p.upvotes):''}</span>
    </div>
    <h3>${isClassic(p)?escapeHtml(p.title):`<a href="${p.hfUrl||p.url||p.arxiv}" target="_blank" rel="noopener" style="color:var(--text)">${escapeHtml(p.title)}</a>`}</h3>
    <div class="authors">${escapeHtml(formatAuthors(p.authors))}</div>
    <div class="abstract">${escapeHtml((p.abstract||'').slice(0,460))}</div>
    ${opts.why?`<div class="why">${escapeHtml(opts.why)}</div>`:''}
    <div class="row">
      <div class="tags">${topics.map(t=>`<span class="tag-pill">${escapeHtml(t)}</span>`).join('')}</div>
      <div style="display:flex;gap:6px;flex-wrap:wrap">${actionLinks.join('')}</div>
    </div>
  </div>`;
}
function classicCard(p, opts={}){
  return `
  <div class="card">
    ${bookmarkBtn(p.id)}
    <div class="venue">${escapeHtml(p.venue)} · ${p.year}</div>
    <h3>${escapeHtml(p.title)}</h3>
    <div class="authors">${escapeHtml(formatAuthors(p.authors))}</div>
    <div class="abstract">${escapeHtml(p.abstract||'')}</div>
    ${opts.why?`<div class="why">${escapeHtml(opts.why)}</div>`:''}
    <div class="row">
      <div class="tags">${(p.topics||[]).slice(0,4).map(t=>`<span class="tag-pill">${escapeHtml(t)}</span>`).join('')}</div>
      <div style="display:flex;gap:6px;flex-wrap:wrap">
        ${p.arxiv?`<a class="btn" href="${p.arxiv}" target="_blank" rel="noopener">论文</a>${zhLink(p.arxiv)}`:''}
        ${p.project?`<a class="btn" href="${p.project}" target="_blank" rel="noopener">项目页</a>`:''}
      </div>
    </div>
  </div>`;
}
function isClassic(p){ return p.source === 'classic'; }

function heroNew(p){
  const kind = p.publicationKind || inferKindFromVenue(p.venue, p.source);
  const srcClass = kind==='conference'?'src-hf':(kind==='journal' || kind==='preprint'?'src-arxiv':'src-classic');
  const srcLabel = kindLabel(kind);
  return `
    <div>
      <span class="badge hf-badge">🔥 今日最新 · <span class="src ${srcClass}" style="margin-left:6px">${srcLabel}</span> · ${escapeHtml(p.date||'')}${p.venue?(' · '+escapeHtml(p.venue)):''}${p.upvotes?(' · 👍 '+p.upvotes):''}</span>
      <h1><a href="${p.hfUrl||p.url||p.arxiv}" target="_blank" rel="noopener" style="color:var(--text);text-decoration:none">${escapeHtml(p.title)}</a></h1>
      <div class="meta">${escapeHtml(formatAuthors(p.authors))}</div>
      <div class="abstract">${escapeHtml(p.abstract||'')}</div>
      <div class="actions">
        ${p.hfUrl?`<a class="btn" href="${p.hfUrl}" target="_blank" rel="noopener">🧡 HF 页面</a>`:''}
        ${p.arxiv?`<a class="btn primary" href="${p.arxiv}" target="_blank" rel="noopener">📄 arXiv</a>${zhLink(p.arxiv)}`:''}
        ${p.pdf?`<a class="btn" href="${p.pdf}" target="_blank" rel="noopener">PDF</a>`:''}
      </div>
      <div class="hero-tags">${(p.topics||[]).map(t=>`<span class="tag-pill">${escapeHtml(t)}</span>`).join('')}</div>
    </div>
    <div class="hero-art"><div><div class="emoji">🤖</div><div class="tag">来自 HF Daily Papers + arXiv 最新提交，每天自动更新。</div></div></div>
  `;
}
function heroCurated(sel){
  const p = sel.hero;
  return `
    <div>
      <span class="badge">今日主题 · ${escapeHtml(sel.theme.title)} · 经典重温</span>
      <h1>${escapeHtml(p.title)}</h1>
      <div class="meta">${escapeHtml(p.venue)} · ${p.year}</div>
      <div class="authors">${escapeHtml(p.authors)}</div>
      <div class="abstract">${escapeHtml(p.abstract||'')}</div>
      <div class="actions">
        ${p.arxiv?`<a class="btn primary" href="${p.arxiv}" target="_blank" rel="noopener">📄 阅读论文</a>${zhLink(p.arxiv)}`:''}
        ${p.project?`<a class="btn" href="${p.project}" target="_blank" rel="noopener">🔗 项目页</a>`:''}
        ${bookmarkBtn('c:'+p.id)}
      </div>
      <div class="hero-tags">${p.tags.map(t=>`<span class="tag-pill">${escapeHtml(t)}</span>`).join('')}</div>
    </div>
    <div class="hero-art"><div><div class="emoji">${p.emoji||'🤖'}</div><div class="tag">${escapeHtml(sel.theme.hook)}</div></div></div>
  `;
}

// ---------- Sidebar chips ----------
function renderChips(){
  const newPs = allNewPapers();
  const classics = allClassics();
  const archivePs = allArchivePapers();
  const tagCounts = countBy([...newPs, ...classics, ...archivePs], p=>p.topics||[]);
  const kindCounts = countBy([...newPs, ...classics, ...archivePs], p=>[p.publicationKind || 'other']);
  Object.entries(state.bundle?.topicCounts || state.archiveIndex?.topicCounts || {}).forEach(([name, count])=>{
    tagCounts.set(name, Math.max(tagCounts.get(name) || 0, Number(count) || 0));
  });
  const tagSet = Array.from(tagCounts.entries()).sort((a,b)=>b[1]-a[1] || a[0].localeCompare(b[0])).map(([name])=>name);
  const indexYears = (state.archiveIndex?.years || []).map(y=>String(y.year));
  const yearSet = uniq([...newPs.map(p=>String((p.date||'').slice(0,4))), ...classics.map(p=>String(p.year)), ...archivePs.map(p=>String((p.date||'').slice(0,4))), ...indexYears]).sort((a,b)=>Number(b)-Number(a));

  const fill = (hostId, set, activeSet, counts=null)=>{
    const host = byId(hostId); host.innerHTML='';
    set.forEach(v=>{
      if(!v) return;
      const b = document.createElement('button');
      b.className = 'chip' + (activeSet.has(v)?' active':'');
      const label = hostId === 'kindChips' ? kindLabel(v) : v;
      b.innerHTML = counts ? `${escapeHtml(label)} <span class="chip-count">${counts.get(v) || 0}</span>` : escapeHtml(label);
      b.onclick = ()=>{
        if(activeSet.has(v)) activeSet.delete(v); else activeSet.add(v);
        // when a tag is picked and we're on "today", stay on today; if on feed/latest, stay.
        render();
      };
      host.appendChild(b);
    });
  };
  fill('tagChips', tagSet.slice(0, 28), state.activeTags, tagCounts);
  byId('yearChips').innerHTML='';
  fill('yearChips', yearSet, state.activeYears);
  fill('kindChips', ['conference','journal','preprint','other'].filter(k=>kindCounts.has(k)), state.activeKinds, kindCounts);
}

// ---------- Selections ----------
function getCuratedSelection(){
  const seed = todayKey() + state.seedOffset;
  const themeIdx = seed % DAILY_THEMES.length;
  const theme = DAILY_THEMES[themeIdx];
  const rng = seededRandom(seed);
  let pool = PAPERS;
  if(state.activeTags.size){
    pool = PAPERS.filter(p=>p.tags.some(t=>state.activeTags.has(t)));
    if(!pool.length) pool = PAPERS;
  }
  const heroIdx = Math.floor(rng()*pool.length);
  const hero = pool[heroIdx];
  let related = PAPERS.filter(p=>p.id!==hero.id && p.tags.some(t=>hero.tags.includes(t)))
                     .slice().sort(()=>rng()-0.5).slice(0,3);
  if(related.length<3){
    const rest = PAPERS.filter(p=>p.id!==hero.id && !related.find(r=>r.id===p.id)).slice().sort(()=>rng()-0.5);
    while(related.length<3 && rest.length) related.push(rest.shift());
  }
  return {theme, hero, related};
}
function pickNewHero(list){
  if(!list.length) return null;
  // If active tags, pick first (newest/hottest) matching in tags; else first.
  let pool = list;
  if(state.activeTags.size){
    const p = list.filter(x => (x.topics||[]).some(t=>state.activeTags.has(t)));
    if(p.length) pool = p;
  }
  return pool[0];
}

// ---------- Panels ----------
function allLatestPapers(){ return ((state.bundle && state.bundle.papers) || []).map(newAsGeneric); }
function allSearchPapers(){ return ((state.searchIndex && state.searchIndex.papers) || []).map(newAsGeneric); }
function allArchivePapers(){
  const base = ((state.bundle && state.bundle.archive) || []);
  const loaded = Object.values(state.archiveYears).flat();
  const seen = new Set();
  return [...base, ...loaded].filter(p=>{
    if(!p || seen.has(p.id)) return false;
    seen.add(p.id);
    return true;
  }).map(newAsGeneric);
}
function renderToday(){
  const curated = getCuratedSelection();
  const news = filtered(allLatestPapers()).sort((a,b)=>(b.date||'').localeCompare(a.date||'') || (b.upvotes||0)-(a.upvotes||0));
  const classicList = filtered(allClassics()); // "classics revisit" block below is always 3 related from curated selection (ignoring tag filter intentionally? We'll respect filter.)
  const moreClassics = classicList.filter(p=>p.id!=='c:'+curated.hero.id).sort(()=>seededRandom(todayKey()+state.seedOffset+1)()-0.5).slice(0,3);

  const top = pickNewHero(news);
  const heroHost = byId('heroCard');
  const sub = byId('todaySub');
  const newHost = byId('hfGrid');
  const moreHost = byId('todayMore');
  const hfSub = byId('hfSub');

  const d = new Date();
  const dateStr = `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
  const activeTagLabel = state.activeTags.size ? (' · 主题：'+Array.from(state.activeTags).join(' / ')) : '';
  byId('datePill').textContent = `${dateStr}${activeTagLabel}`;
  byId('todayTitle').textContent = top? '今日最新论文' : '今日精选';
  byId('todayMoreTitle').textContent = top? '更多最新' : '更多精选';

  if(state.loading && !state.bundle){
    byId('todaySub').textContent = '正在从 Hugging Face + arXiv 抓取最新具身论文…';
  } else if(state.bundleError && !top){
    byId('todaySub').textContent = '抓取新文失败，显示经典精选：'+state.bundleError;
  } else if(state.bundle){
    const hf = state.bundle.sources?.hf||0, arx = state.bundle.sources?.arxiv||0, s2 = state.bundle.sources?.semanticScholar||0;
    const total = state.bundle.recentTotal || state.bundle.count;
    byId('todaySub').textContent = `${dateStr} · 最近 ${state.bundle.recentDays||7} 天展示 ${state.bundle.count}/${total} 篇新文（HF ${hf} / arXiv ${arx}${s2 ? ' / S2 '+s2 : ''}）${activeTagLabel}`;
  }

  if(top){
    heroHost.innerHTML = heroNew(top);
    const rest = news.filter(p=>p.id!==top.id).slice(0,9);
    hfSub.textContent = `筛选后 ${rest.length+1} 篇，按日期+热度排序`;
    newHost.innerHTML = rest.length ? rest.map(p=>newCard(p)).join('') : '<div class="empty">今天匹配的新文只有这一篇。</div>';
  } else {
    heroHost.innerHTML = heroCurated(curated);
    hfSub.textContent = '暂无新文数据，先看经典精选。';
    newHost.innerHTML = `<div class="empty"><a class="btn primary" href="https://huggingface.co/papers" target="_blank" rel="noopener">🧡 HF Daily Papers</a> <a class="btn" href="https://arxiv.org/list/cs.RO/recent" target="_blank" rel="noopener">📄 arXiv cs.RO</a></div>`;
  }
  moreHost.innerHTML = moreClassics.map(p=>classicCard(p, {why:'推荐理由：'+(p.why||'领域代表性工作')})).join('');
}
function renderLatest(){
  const searching = state.search.trim().length >= 2;
  if(searching && !state.searchIndex && !state.searchIndexLoading && !state.searchIndexError){
    loadSearchIndex();
  }
  const sourceList = searching && state.searchIndex ? allSearchPapers() : allLatestPapers();
  const list = filtered(sourceList).sort((a,b)=>(b.date||'').localeCompare(a.date||'') || (b.upvotes||0)-(a.upvotes||0));
  const days = state.bundle?.recentDays || 7;
  const total = state.bundle?.recentTotal || state.bundle?.count || list.length;
  const meta = searching
    ? (state.searchIndex
        ? `全库搜索，共 ${list.length}/${state.searchIndex.count} 篇匹配`
        : state.searchIndexLoading ? '正在加载全库搜索索引…' : `全库搜索索引加载失败：${state.searchIndexError || '未知错误'}`)
    : `最近 ${days} 天，展示 ${list.length}/${total} 篇`;
  byId('latestCount2').textContent = meta;
  const visible = searching ? list.slice(0, state.searchResultLimit) : list;
  const more = searching && list.length > visible.length
    ? `<button class="btn small load-more" data-search-more>再显示 ${Math.min(120, list.length - visible.length)} 篇</button>`
    : '';
  const emptyText = searching && state.searchIndexLoading ? '正在加载全库搜索索引…' : '没有匹配的新论文，试试清除筛选或点「刷新最新」。';
  byId('latestGrid').innerHTML = visible.length ? visible.map(p=>newCard(p)).join('') + more : `<div class="empty">${emptyText}</div>`;
  byId('latestCount').textContent = allNewPapers().length;
}
function renderClassics(){
  const list = filtered(allClassics());
  byId('feedCount').textContent = `共 ${list.length} 篇`;
  byId('feedGrid').innerHTML = list.length ? list.map(p=>classicCard(p)).join('') : '<div class="empty">没有匹配的经典论文，换个关键词/标签。</div>';
  byId('classicsCount').textContent = allClassics().length;
}
function renderArchive(){
  const list = filtered(allArchivePapers()).sort((a,b)=>(b.date||'').localeCompare(a.date||'') || (b.upvotes||0)-(a.upvotes||0));
  const host = byId('archiveGrid');
  const archiveTotal = state.bundle?.archiveTotal || state.bundle?.historyTotal || list.length;
  const loadedTotal = allArchivePapers().length;
  byId('archiveCount').textContent = `已加载 ${loadedTotal}/${archiveTotal} 篇（最近 ${Math.round((state.bundle?.archiveDays||3650)/365)} 年，不含最近 ${state.bundle?.recentDays||7} 天）`;
  if(!state.archiveIndex && !state.archiveIndexLoading && !state.archiveIndexError){
    loadArchiveIndex();
  }
  if(state.archiveIndexLoading && !state.archiveIndex){
    host.innerHTML = '<div class="empty">正在加载往期索引…</div>';
    return;
  }
  if(state.archiveIndexError && !list.length){
    host.innerHTML = `<div class="empty">往期索引加载失败：${escapeHtml(state.archiveIndexError)}</div>`;
    return;
  }
  if (list.length === 0 && !state.archiveIndex) {
    host.innerHTML = '<div class="empty">往期暂无匹配论文。历史回填进行中，每日自动更新积累。</div>';
    return;
  }
  const years = new Map();
  list.forEach(p => {
    const y = (p.date||'').slice(0,4);
    const ym = (p.date||'').slice(0,7);
    if (!years.has(y)) years.set(y, new Map());
    const months = years.get(y);
    if (!months.has(ym)) months.set(ym, []);
    months.get(ym).push(p);
  });
  if(state.archiveIndex){
    state.archiveIndex.years.forEach(y=>{
      if(!years.has(y.year)) years.set(y.year, new Map());
    });
  }
  const yearOrder = Array.from(years.keys()).sort().reverse();
  if(!state.archiveExpandedYears.size && yearOrder.length){
    state.archiveExpandedYears.add(yearOrder[0]);
    if(state.archiveIndex && !state.archiveYears[yearOrder[0]] && !state.archiveLoadingYears.has(yearOrder[0])){
      loadArchiveYear(yearOrder[0]);
    }
  }
  const html = yearOrder.map(y => {
    const months = years.get(y);
    const monthOrder = Array.from(months.keys()).sort().reverse();
    const indexYear = state.archiveIndex?.years?.find(item=>item.year === y);
    const total = indexYear?.count || Array.from(months.values()).reduce((sum, arr)=>sum + arr.length, 0);
    const expanded = state.archiveExpandedYears.has(y);
    const yearLoaded = Boolean(state.archiveYears[y]) || !indexYear;
    const isLoading = state.archiveLoadingYears.has(y);
    const loadError = state.archiveYearErrors[y];
    const monthsHtml = expanded
      ? (isLoading
          ? '<div class="empty">正在加载这一年的论文…</div>'
          : loadError
            ? `<div class="empty">加载 ${y} 年失败：${escapeHtml(loadError)}</div>`
            : yearLoaded
              ? monthOrder.map((ym, idx) => {
                  if(!Array.from(state.archiveExpandedMonths).some(v=>v.startsWith(y+'-')) && idx === 0){
                    state.archiveExpandedMonths.add(ym);
                  }
                  const items = months.get(ym) || [];
                  const monthExpanded = state.archiveExpandedMonths.has(ym);
                  const limit = state.archiveMonthLimits[ym] || 60;
                  const cards = monthExpanded ? items.slice(0, limit).map(p => newCard(p)).join('') : '';
                  const more = monthExpanded && items.length > limit
                    ? `<button class="btn small load-more" data-more-month="${ym}">再显示 ${Math.min(60, items.length - limit)} 篇</button>`
                    : '';
                  return `<div class="month-group">
                    <h4 class="month-heading month-toggle" data-month="${ym}">
                      <span class="year-toggle">${monthExpanded ? '▼' : '▶'}</span>${ym} <span class="muted">(${items.length}篇)</span>
                    </h4>
                    ${monthExpanded ? `<div class="grid">${cards}</div>${more}` : `<div class="year-summary">${items.length} 篇，点击月份展开</div>`}
                  </div>`;
                }).join('')
              : `<div class="year-summary">${(indexYear?.months || []).slice(0,8).map(m=>`${m.month} (${m.count})`).join(' / ')}<br><button class="btn small" data-load-year="${y}">加载 ${y} 年全部 ${total} 篇</button></div>`)
      : `<div class="year-summary">${(indexYear?.months || monthOrder.map(m=>({month:m,count:(months.get(m)||[]).length}))).slice(0,6).map(m=>`${m.month} (${m.count})`).join(' / ')}${(indexYear?.months?.length || monthOrder.length) > 6 ? ' …' : ''}</div>`;
    return `<div class="year-group">
      <h3 class="year-heading" data-year="${y}">
        <span class="year-toggle">${expanded ? '▼' : '▶'}</span>
        ${y} 年 <span class="muted">(${months.size || indexYear?.months?.length || 0}个月, ${total}篇)</span>
      </h3>
      <div class="year-content" data-year-content="${y}">
        ${monthsHtml}
      </div>
    </div>`;
  }).join('');
  host.innerHTML = html;
  // Add toggle handlers
  host.querySelectorAll('.year-heading').forEach(h => {
    h.addEventListener('click', () => {
      const y = h.dataset.year;
      if(state.archiveExpandedYears.has(y)) state.archiveExpandedYears.delete(y);
      else {
        state.archiveExpandedYears.add(y);
        if(state.archiveIndex && !state.archiveYears[y] && !state.archiveLoadingYears.has(y)){
          loadArchiveYear(y);
        }
      }
      renderArchive();
    });
    h.style.cursor = 'pointer';
  });
  host.querySelectorAll('[data-load-year]').forEach(btn=>{
    btn.addEventListener('click', e=>{
      e.stopPropagation();
      loadArchiveYear(btn.dataset.loadYear);
    });
  });
  host.querySelectorAll('[data-month]').forEach(h=>{
    h.addEventListener('click', ()=>{
      const ym = h.dataset.month;
      if(state.archiveExpandedMonths.has(ym)) state.archiveExpandedMonths.delete(ym);
      else state.archiveExpandedMonths.add(ym);
      renderArchive();
    });
  });
  host.querySelectorAll('[data-more-month]').forEach(btn=>{
    btn.addEventListener('click', ()=>{
      const ym = btn.dataset.moreMonth;
      state.archiveMonthLimits[ym] = (state.archiveMonthLimits[ym] || 60) + 60;
      renderArchive();
    });
  });
}

function renderBookmarks(){
  const newPs = allNewPapers(), cls = allClassics(), arcPs = allArchivePapers();
  const all = [...newPs, ...cls, ...arcPs].filter(p=>state.bookmarks.has(p.id));
  byId('bmEmpty').hidden = all.length>0;
  byId('bmGrid').innerHTML = all.length ? all.map(p=> isClassic(p)?classicCard(p):newCard(p)).join('')
                                        : '<div class="empty">还没有收藏，点卡片右上角 ☆ 收藏论文。</div>';
}
function render(){
  renderChips();
  renderCounts();
  saveBookmarks();
  document.querySelectorAll('.tab').forEach(t=>{
    t.classList.toggle('active', t.dataset.tab===state.tab);
  });
  byId('todayPane').classList.toggle('hidden', state.tab!=='today');
  byId('latestPane').classList.toggle('hidden', state.tab!=='latest');
  byId('feedPane').classList.toggle('hidden', state.tab!=='feed');
  byId('archivePane').classList.toggle('hidden', state.tab!=='archive');
  byId('bookmarksPane').classList.toggle('hidden', state.tab!=='bookmarks');
  if(state.tab === 'today') renderToday();
  else if(state.tab === 'latest') renderLatest();
  else if(state.tab === 'feed') renderClassics();
  else if(state.tab === 'archive') renderArchive();
  else if(state.tab === 'bookmarks') renderBookmarks();
}
function renderCounts(){
  byId('latestCount').textContent = allNewPapers().length;
  byId('classicsCount').textContent = allClassics().length;
  byId('archiveCountBadge').textContent = state.archiveIndex?.archiveTotal || state.bundle?.archiveTotal || allArchivePapers().length;
}

// ---------- Interactions ----------
document.addEventListener('click', (e)=>{
  const t = e.target;
  if(t.dataset && t.dataset.bm){
    e.preventDefault();
    const id = t.dataset.bm;
    if(state.bookmarks.has(id)) state.bookmarks.delete(id); else state.bookmarks.add(id);
    saveBookmarks(); render();
  }
  if(t.dataset && t.dataset.close!==undefined) closeDetail();
  if(t.dataset && t.dataset.searchMore!==undefined){
    state.searchResultLimit += 120;
    renderLatest();
  }
});
document.addEventListener('keydown',(e)=>{ if(e.key==='Escape') closeDetail(); });
document.querySelectorAll('.tab').forEach(tab=>{
  tab.addEventListener('click', ()=>{ state.tab = tab.dataset.tab; render(); });
});
byId('searchInput').addEventListener('input', (e)=>{
  state.search = e.target.value;
  state.searchResultLimit = 120;
  // auto-switch to latest when typing new papers; classics tab still filters via state.
  if(state.search.trim() && state.tab === 'today') state.tab='latest';
  if(state.search.trim().length >= 2) loadSearchIndex();
  render();
});
byId('resetFilters').addEventListener('click', ()=>{
  state.activeTags.clear(); state.activeYears.clear(); state.activeKinds.clear();
  state.search=''; byId('searchInput').value='';
  state.tab='today';
  render();
});
byId('shuffleBtn').addEventListener('click', ()=>{ state.seedOffset += 1337; render(); });
byId('refreshBtn').addEventListener('click', ()=>{ loadBundle({refresh:true}); });

function mountSearchExtras(){
  const wrap = byId('searchInput').parentElement;
  const addBtn = (label, title, url)=>{
    const b = document.createElement('button');
    b.className='hf-btn'; b.textContent=label; b.title=title;
    b.onclick = ()=>{
      const q=(state.search||'agent llm safety training').trim();
      window.open(url+encodeURIComponent(q),'_blank','noopener');
    };
    wrap.appendChild(b);
  };
  addBtn('🔎 HF','在 Hugging Face Papers 搜索','https://huggingface.co/papers?q=');
  addBtn('📄 arXiv','在 arXiv 搜索','https://arxiv.org/search/?searchtype=all&query=');
  addBtn('HF Daily','打开 HF Daily Papers 首页',()=>(window.open('https://huggingface.co/papers','_blank','noopener'),null));
  // fix: third button doesn't take query; recreate:
  wrap.lastChild.remove();
  const daily = document.createElement('button');
  daily.className='hf-btn'; daily.textContent='HF Daily'; daily.title='HF Daily Papers 首页';
  daily.onclick = ()=>window.open('https://huggingface.co/papers','_blank','noopener');
  wrap.appendChild(daily);
}

// ---------- Data loading ----------
async function loadBundle(opts={}){
  state.loading = true; state.bundleError = null; render();
  try{
    const suffix = opts.refresh ? `?v=${Date.now()}` : '';
    const r = await fetch(`data/daily.json${suffix}`, {cache: opts.refresh ? 'no-store' : 'default'});
    if(r.ok){
      const d = await r.json();
      if(d && Array.isArray(d.papers)){ state.bundle = d; }
      else state.bundleError = 'daily.json 格式异常';
    } else {
      state.bundleError = '找不到 data/daily.json';
    }
  }catch(e){
    state.bundleError = String(e.message||e);
  }
  state.loading = false;
  render();
  if(!state.archiveIndex && !state.archiveIndexLoading && !state.archiveIndexError){
    loadArchiveIndex();
  }
}
async function loadArchiveIndex(){
  state.archiveIndexLoading = true;
  state.archiveIndexError = null;
  renderCounts();
  try{
    const r = await fetch('data/archive-index.json', {cache:'default'});
    if(!r.ok) throw new Error('HTTP '+r.status);
    const index = await r.json();
    if(!index || !Array.isArray(index.years)) throw new Error('archive-index.json 格式异常');
    state.archiveIndex = index;
    if(state.bundle) state.bundle.archiveTotal = index.archiveTotal || state.bundle.archiveTotal;
  }catch(e){
    state.archiveIndexError = String(e.message || e);
  }finally{
    state.archiveIndexLoading = false;
    if(state.tab === 'archive') renderArchive();
    else render();
  }
}
async function loadArchiveYear(year){
  if(!year || state.archiveYears[year] || state.archiveLoadingYears.has(year)) return;
  state.archiveLoadingYears.add(year);
  delete state.archiveYearErrors[year];
  if(state.tab === 'archive') renderArchive();
  try{
    const r = await fetch(`data/archive/${year}.json`, {cache:'default'});
    if(!r.ok) throw new Error('HTTP '+r.status);
    const data = await r.json();
    if(!data || !Array.isArray(data.papers)) throw new Error(`${year}.json 格式异常`);
    state.archiveYears[year] = data.papers;
  }catch(e){
    state.archiveYearErrors[year] = String(e.message || e);
  }finally{
    state.archiveLoadingYears.delete(year);
    if(state.tab === 'archive') renderArchive();
    else renderCounts();
  }
}
async function loadSearchIndex(){
  if(state.searchIndex || state.searchIndexLoading) return;
  state.searchIndexLoading = true;
  state.searchIndexError = null;
  if(state.tab === 'latest') renderLatest();
  try{
    const r = await fetch('data/search-index.json', {cache:'default'});
    if(!r.ok) throw new Error('HTTP '+r.status);
    const data = await r.json();
    if(!data || !Array.isArray(data.papers)) throw new Error('search-index.json 格式异常');
    state.searchIndex = data;
  }catch(e){
    state.searchIndexError = String(e.message || e);
  }finally{
    state.searchIndexLoading = false;
    if(state.tab === 'latest') renderLatest();
  }
}
function closeDetail(){ byId('detail').classList.add('hidden'); }
function openDetail(id){ /* details currently only for classics; keep simple for now */ }

saveBookmarks();
mountSearchExtras();
render();
loadBundle();
