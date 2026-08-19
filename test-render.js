const { JSDOM } = require('jsdom');
const fs = require('fs');
const path = require('path');

// Read all files
const html = fs.readFileSync('index.html', 'utf8');
const appJs = fs.readFileSync('app.js', 'utf8');
const papersJs = fs.readFileSync('papers.js', 'utf8');
const data = JSON.parse(fs.readFileSync('data/daily.json', 'utf8'));

// Create DOM with proper base URL for subpath
const dom = new JSDOM(html, {
  url: 'http://localhost:8766/',
  runScripts: 'dangerously',
  resources: 'usable',
  pretendToBeVisual: true,
});

// Mock fetch to return local data
dom.window.fetch = async (url) => {
  if (url.includes('daily.json')) {
    return {
      ok: true,
      json: async () => data,
    };
  }
  if (url.includes('/api/daily')) {
    return { ok: false, status: 404 };
  }
  throw new Error('Not found');
};

// Capture console errors
const errors = [];
dom.window.console.error = (...args) => {
  errors.push(args.map(String).join(' '));
  console.log('❌ CONSOLE ERROR:', ...args);
};
dom.window.addEventListener('error', (e) => {
  errors.push(e.message);
  console.log('❌ WINDOW ERROR:', e.message, e.error?.stack);
});

// Load papers.js first
dom.window.eval(papersJs);
console.log('✅ papers.js loaded, PAPERS count:', dom.window.PAPERS?.length);

// Load app.js
try {
  dom.window.eval(appJs);
  console.log('✅ app.js evaluated');
} catch(e) {
  console.log('❌ app.js load error:', e.message);
  console.log(e.stack);
}

// Wait for async loadBundle
setTimeout(() => {
  console.log('\n=== After 2 seconds ===');
  const document = dom.window.document;
  
  // Check counts
  console.log('latestCount badge:', document.getElementById('latestCount')?.textContent);
  console.log('archiveCountBadge:', document.getElementById('archiveCountBadge')?.textContent);
  console.log('classicsCount:', document.getElementById('classicsCount')?.textContent);
  console.log('todaySub:', document.getElementById('todaySub')?.textContent);
  
  // Check if papers are rendered
  const latestGrid = document.getElementById('latestGrid');
  const archiveGrid = document.getElementById('archiveGrid');
  const hfGrid = document.getElementById('hfGrid');
  console.log('\nRendered cards:');
  console.log('today hero:', document.getElementById('heroCard')?.children?.length || 0);
  console.log('hfGrid/today more:', hfGrid?.children?.length || 0);
  console.log('latestGrid:', latestGrid?.children?.length || 0);
  console.log('archiveGrid children:', archiveGrid?.children?.length || 0);
  
  // Check for any error messages
  if (errors.length) {
    console.log('\n=== ALL ERRORS ===');
    errors.forEach(e => console.log(' -', e));
  } else {
    console.log('\n✅ NO ERRORS');
  }
  
  // Check if pages show empty text
  console.log('\narchiveGrid HTML start:', archiveGrid?.innerHTML?.slice(0, 200));
  
  process.exit(0);
}, 2000);
