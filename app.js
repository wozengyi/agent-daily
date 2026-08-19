const STORAGE_KEY = 'embodied-daily-bookmarks-v2';
const state = {
  tab: 'today',
  search: '',
  activeTags: new Set(),
  activeYears: new Set(),
  bookmarks: new Set(JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]')),
  seedOffset: 0,
  bundle: null,
  loading: false,
  bundleError: null,
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
function escapeHtml(s){
  return (s||'').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
function formatAuthors(a){
  const parts = (a||'').split(',').map(s=>s.trim()).filter(Boolean);
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
    tags: uniq([...(p.tags||[]), ...(p.topics||[])]),
    topics: p.topics || p.tags || [],
    venue: p.source==='hf'?'Hugging Face Daily':'arXiv'
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
  return true;
}

function filtered(list){ return list.filter(matches); }

// ---------- Render helpers ----------
function sourceBadge(p){
  if(p.source === 'hf') return '<span class="src src-hf">🧡 HF</span>';
  if(p.source === 'arxiv') return '<span class="src src-arxiv">📄 arXiv</span>';
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
      <span style="margin-left:6px">${escapeHtml(p.date||'')} · ${isClassic(p)?p.venue:daysAgoStr(p.date)}${p.upvotes?(' · 👍 '+p.upvotes):''}</span>
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
  const srcClass = p.source==='hf'?'src-hf':(p.source==='arxiv'?'src-arxiv':'src-classic');
  const srcLabel = p.source==='hf'?'HF Daily':(p.source==='arxiv'?'arXiv':'新文');
  return `
    <div>
      <span class="badge hf-badge">🔥 今日最新 · <span class="src ${srcClass}" style="margin-left:6px">${srcLabel}</span> · ${escapeHtml(p.date||'')}${p.upvotes?(' · 👍 '+p.upvotes):''}</span>
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
  const tagSet = uniq([...newPs.flatMap(p=>p.topics||[]), ...classics.flatMap(p=>p.topics||[]), ...archivePs.flatMap(p=>p.topics||[])]).sort();
  const yearSet = uniq([...newPs.map(p=>String((p.date||'').slice(0,4))), ...classics.map(p=>String(p.year)), ...archivePs.map(p=>String((p.date||'').slice(0,4)))]).sort((a,b)=>Number(b)-Number(a));

  const fill = (hostId, set, activeSet)=>{
    const host = byId(hostId); host.innerHTML='';
    set.forEach(v=>{
      if(!v) return;
      const b = document.createElement('button');
      b.className = 'chip' + (activeSet.has(v)?' active':'');
      b.textContent = v;
      b.onclick = ()=>{
        if(activeSet.has(v)) activeSet.delete(v); else activeSet.add(v);
        // when a tag is picked and we're on "today", stay on today; if on feed/latest, stay.
        render();
      };
      host.appendChild(b);
    });
  };
  fill('tagChips', tagSet, state.activeTags);
  byId('yearChips').innerHTML='';
  fill('yearChips', yearSet, state.activeYears);
  // (Venue filter is intentionally removed; sources are now clear via badges.)
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
function allArchivePapers(){ return ((state.bundle && state.bundle.archive) || []).map(newAsGeneric); }
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
    const hf = state.bundle.sources?.hf||0, arx = state.bundle.sources?.arxiv||0;
    byId('todaySub').textContent = `${dateStr} · 最近 ${state.bundle.recentDays||7} 天共 ${state.bundle.count} 篇新文（HF ${hf} / arXiv ${arx}）${activeTagLabel}`;
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
  const list = filtered(allLatestPapers()).sort((a,b)=>(b.date||'').localeCompare(a.date||'') || (b.upvotes||0)-(a.upvotes||0));
  const days = state.bundle?.recentDays || 7;
  byId('latestCount2').textContent = `最近 ${days} 天，共 ${list.length} 篇`;
  byId('latestGrid').innerHTML = list.length ? list.map(p=>newCard(p)).join('') : '<div class="empty">没有匹配的新论文，试试清除筛选或点「🔄 刷新最新」。</div>';
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
  byId('archiveCount').textContent = '共 ' + list.length + ' 篇（最近 ' + (state.bundle?.archiveDays||365) + ' 天，' +
    '不含最近 ' + (state.bundle?.recentDays||7) + ' 天）';
  if (list.length === 0) {
    host.innerHTML = '<div class="empty">往期暂无匹配论文。随着每日构建积累，这里会展示更早的具身论文。</div>';
    return;
  }
  // Group by month for readability.
  const groups = new Map();
  list.forEach(p => {
    const ym = (p.date||'').slice(0,7);
    if (!groups.has(ym)) groups.set(ym, []);
    groups.get(ym).push(p);
  });
  const ymOrder = Array.from(groups.keys()).sort().reverse();
  const html = ymOrder.map(ym => {
    const cards = groups.get(ym).map(p => newCard(p)).join('');
    return '<div class="month-group"><h3 class="month-heading">' + ym + '</h3><div class="grid">' + cards + '</div></div>';
  }).join('');
  host.innerHTML = html;
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
  renderToday();
  renderLatest();
  renderClassics();
  renderArchive();
  renderBookmarks();
  // Update counts
  const arc = allArchivePapers();
  byId('archiveCountBadge').textContent = arc.length;
  saveBookmarks();
  document.querySelectorAll('.tab').forEach(t=>{
    t.classList.toggle('active', t.dataset.tab===state.tab);
  });
  byId('todayPane').classList.toggle('hidden', state.tab!=='today');
  byId('latestPane').classList.toggle('hidden', state.tab!=='latest');
  byId('feedPane').classList.toggle('hidden', state.tab!=='feed');
  byId('latestPane').classList.toggle('hidden', state.tab!=='latest');
  byId('archivePane').classList.toggle('hidden', state.tab!=='archive');
  byId('bookmarksPane').classList.toggle('hidden', state.tab!=='bookmarks');
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
});
document.addEventListener('keydown',(e)=>{ if(e.key==='Escape') closeDetail(); });
document.querySelectorAll('.tab').forEach(tab=>{
  tab.addEventListener('click', ()=>{ state.tab = tab.dataset.tab; render(); });
});
byId('searchInput').addEventListener('input', (e)=>{
  state.search = e.target.value;
  // auto-switch to latest when typing new papers; classics tab still filters via state.
  if(state.search.trim() && state.tab === 'today') state.tab='latest';
  render();
});
byId('resetFilters').addEventListener('click', ()=>{
  state.activeTags.clear(); state.activeYears.clear();
  state.search=''; byId('searchInput').value='';
  state.tab='today';
  render();
});
byId('shuffleBtn').addEventListener('click', ()=>{ state.seedOffset += 1337; render(); });
byId('refreshBtn').addEventListener('click', ()=>{ loadBundle({live:true}); });

function mountSearchExtras(){
  const wrap = byId('searchInput').parentElement;
  const addBtn = (label, title, url)=>{
    const b = document.createElement('button');
    b.className='hf-btn'; b.textContent=label; b.title=title;
    b.onclick = ()=>{
      const q=(state.search||'embodied robot vla').trim();
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
  if(opts.live && location.protocol.startsWith('http')){
    try{
      const r = await fetch('/api/daily', {cache:'no-store'});
      if(r.ok){
        const d = await r.json();
        if(d && Array.isArray(d.papers)){ state.bundle = d; state.loading=false; render(); return; }
      }
      state.bundleError = '实时抓取失败（HTTP '+r.status+'）';
    }catch(e){ state.bundleError = String(e.message||e); }
  }
  try{
    const r = await fetch('data/daily.json',{cache:'no-cache'});
    if(r.ok){
      const d = await r.json();
      if(d && Array.isArray(d.papers)){ state.bundle = d; }
      else state.bundleError = state.bundleError || 'daily.json 格式异常';
    } else {
      state.bundleError = state.bundleError || '找不到 data/daily.json，请先运行 build/build_daily.py';
    }
  }catch(e){ state.bundleError = state.bundleError || String(e.message||e); }
  state.loading = false;
  render();
}
function closeDetail(){ byId('detail').classList.add('hidden'); }
function openDetail(id){ /* details currently only for classics; keep simple for now */ }

saveBookmarks();
mountSearchExtras();
render();
loadBundle();
