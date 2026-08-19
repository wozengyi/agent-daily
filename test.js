const fs = require('fs');
global.document = {
  getElementById: () => ({ classList: {toggle:()=>{}, add:()=>{}, remove:()=>{}}, textContent: '', innerHTML: '', appendChild:()=>{}, style:{}, onclick: null, addEventListener:()=>{} }),
  querySelectorAll:()=>[],
  addEventListener:()=>{},
  createElement: ()=>({classList:{add:()=>{},toggle:()=>{}},appendChild:()=>{},onclick:null})
};
global.window = { location: { hostname: 'github.io', search: '' }, localStorage: { getItem:()=>null, setItem:()=>{} } };
global.fetch = async () => ({ ok: true, json: async () => JSON.parse(fs.readFileSync('data/daily.json','utf8')) });
global.Math = Math;

const papersCode = fs.readFileSync('papers.js','utf8');
eval(papersCode);
console.log('papers:', PAPERS.length);

const appCode = fs.readFileSync('app.js','utf8').replace('loadBundle();','//');
eval(appCode);
console.log('app loaded');

state.bundle = JSON.parse(fs.readFileSync('data/daily.json','utf8'));
console.log('bundle papers:', state.bundle.papers.length, 'archive:', state.bundle.archive.length);

try {
  renderChips();
  console.log('renderChips OK');
  renderToday();
  console.log('renderToday OK');
  renderLatest();
  console.log('renderLatest OK, count:', byId('latestCount').textContent);
  renderClassics();
  console.log('renderClassics OK, count:', byId('classicsCount').textContent);
  renderArchive();
  console.log('renderArchive OK, count:', byId('archiveCount').textContent);
  renderBookmarks();
  console.log('renderBookmarks OK');
  render();
  console.log('✅ ALL RENDERED');
} catch(e) {
  console.log('❌', e.message, e.stack.split('\\n')[1]);
}
