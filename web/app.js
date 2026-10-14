const grid = document.querySelector('#resource-grid');
const search = document.querySelector('#search');
const dialog = document.querySelector('#detail');
const content = document.querySelector('#dialog-content');
let sources = [], category = 'all';
const groups = { 'manufacturer-portal': 'devices', 'credentialing-body': 'learning' };
const labels = { devices: 'DEVICES & LABELING', learning: 'CERTIFICATION', safety: 'SAFETY & GUIDANCE' };
const publisher = { 'American College of Radiology': 'ACR', 'US Food and Drug Administration': 'FDA', 'The Joint Commission': 'Joint Commission', 'RadiologyInfo.org (ACR and RSNA)': 'RadiologyInfo', 'International Board of Magnetic Resonance Safety': 'IBMRS', 'Medtronic': 'Medtronic', 'Abbott Neuromodulation': 'Abbott', 'Boston Scientific': 'Boston Scientific', 'Cochlear': 'Cochlear', 'US National Library of Medicine and FDA': 'AccessGUDID' };
function node(tag, text, className) { const el=document.createElement(tag); el.textContent=text; if(className)el.className=className; return el; }
function openDialog(title, label='RESOURCE DETAILS') { content.replaceChildren(node('h2',title));document.querySelector('#dialog-label').textContent=label;dialog.showModal(); }
let guides=[];
function guideCard(g){const a=node('a','','guide-card');a.href=g.url;a.dataset.group=g.category;const mark=node('span',g.initials,'maker-mark');mark.setAttribute('aria-hidden','true');const text=node('span','','guide-text');text.append(node('h3',g.manufacturer),node('p',g.devices));a.append(mark,text,node('span','→','guide-arrow'));a.setAttribute('aria-label',`${g.manufacturer}: ${g.title}`);return a;}
function renderTools(tools){const grid=document.querySelector('#tool-grid');grid.replaceChildren();for(const t of tools){const a=node('a','','tool-card');a.href=t.url;a.target='_blank';a.rel='noopener noreferrer';const text=node('span','','guide-text');text.append(node('h3',`${t.title} ↗`),node('p',t.scope));a.append(node('span',publisher[t.publisher]||t.publisher,'tool-tag'),text);grid.append(a);}}
function categoryOf(s){return (s.topics.includes('udi')||s.topics.includes('recalls'))?'devices':(groups[s.kind] || 'safety');}
function render(){
 const query=search.value.trim().toLowerCase();
 const visible=sources.filter(s=>(category==='all'||categoryOf(s)===category)&&(!query||[s.title,s.publisher,s.scope,...s.topics].join(' ').toLowerCase().includes(query)));
 grid.replaceChildren();
 for(const s of visible){
  const card=node('article','','resource-card'), top=node('div','','card-top');top.append(node('span',publisher[s.publisher]||s.publisher,'publisher-logo'),node('span',labels[categoryOf(s)],'category-label'));
  const bottom=node('div','','card-bottom'), link=node('a','Visit Source ↗');link.href=s.url;link.target='_blank';link.rel='noopener noreferrer';
  const more=node('button','Details');more.type='button';more.setAttribute('aria-label',`Source details: ${s.publisher}, ${s.title}`);more.addEventListener('click',()=>showSource(s));bottom.append(link,more);
  card.append(top,node('h3',s.title),node('p',s.scope),bottom);grid.append(card);
 }
 const matches=query?guides.filter(g=>[g.manufacturer,g.devices,g.title,g.covers,g.category].join(' ').toLowerCase().includes(query)):[];const gm=document.querySelector('#guide-matches');gm.hidden=!matches.length;gm.replaceChildren();if(matches.length){gm.append(node('p','Guides','matches-label'));const grid=node('div','','guide-grid');matches.forEach(g=>grid.append(guideCard(g)));gm.append(grid);}
 document.querySelector('#empty').hidden=visible.length!==0||matches.length!==0;
 const active=document.querySelector('#active-query');active.hidden=!query;active.textContent=`Search results for “${search.value.trim()}”`;
 document.querySelectorAll('[data-filter]').forEach(b=>{const selected=b.dataset.filter===category;b.classList.toggle('active',selected);b.setAttribute('aria-pressed',selected);});
}
function showSource(s){openDialog(s.title);content.append(node('p',s.scope));const dl=node('dl','');for(const [k,v] of [['Publisher',s.publisher],['Region',s.jurisdiction==='US'?'United States':'US & international — select the US pathway']])dl.append(node('dt',k),node('dd',v));content.append(dl,node('p','This record identifies a starting point. It does not confirm an exact device manual, its current revision, or individual scan eligibility.'));const a=node('a','Open Source Page ↗','button outline');a.href=s.url;a.target='_blank';a.rel='noopener noreferrer';content.append(a);}
function selectCategory(value){category=value;search.value='';render();document.querySelector('#resources').scrollIntoView();}
document.querySelectorAll('[data-filter]').forEach(b=>b.addEventListener('click',()=>{category=b.dataset.filter;render();}));
document.querySelectorAll('[data-category]').forEach(b=>b.addEventListener('click',()=>selectCategory(b.dataset.category)));
document.querySelectorAll('[data-query]').forEach(b=>b.addEventListener('click',()=>{category='all';search.value=b.dataset.query;render();document.querySelector('#resources').scrollIntoView();}));
search.addEventListener('input',render);
document.querySelector('form').addEventListener('submit',e=>{e.preventDefault();render();document.querySelector('#resources').scrollIntoView();});
document.querySelector('#reset').addEventListener('click',()=>selectCategory('all'));
document.querySelector('#close-dialog').addEventListener('click',()=>dialog.close());
dialog.addEventListener('click',e=>{if(e.target===dialog){const r=dialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)dialog.close();}});
document.querySelector('#copy-prompt').addEventListener('click',async()=>{const text=document.querySelector('#prompt-text').textContent;try{await navigator.clipboard.writeText(text);document.querySelector('#copy-status').textContent='Copied';}catch{document.querySelector('#copy-status').textContent='Select the prompt text to copy.';}});
function showInstall(){openDialog('Add MR Safety Agent to Your AI Tool','INSTALL');
 const block=(title,parts)=>{const box=node('div','','install-option');box.append(node('h3',title));for(const p of parts){if(p.code){const pre=node('pre','');pre.append(node('code',p.code));const copy=node('button','Copy','copy-code');copy.type='button';copy.addEventListener('click',async()=>{try{await navigator.clipboard.writeText(p.code);copy.textContent='Copied';}catch{copy.textContent='Select and copy';}setTimeout(()=>{copy.textContent='Copy';},1800);});box.append(pre,copy);}else box.append(node('p',p));}return box;};
 const repo='mri-commons/mr-safety-agent';
 const appBlock=block('Claude, ChatGPT, or Gemini App',['Download the skill, then upload the zip in your app.','Claude: turn on Settings → Capabilities → Code execution and file creation, then open Customize → Skills.','ChatGPT: on paid plans, open Plugins → Skills → Create → Upload from your computer. Uploaded skills work only in Work, not in regular chat.','Gemini: when Skills appears in your account, upload the zip there.']);
 const dl=node('a','Download the Skill ↓','button outline install-download');dl.href='assets/mr-safety-agent.zip';dl.download='';appBlock.append(dl);
 content.append(node('p','1. Choose how to install','install-step'),
  block('Claude Code, Codex, or Gemini CLI',['Run one command. It requires Node.js.',{code:document.querySelector('#install-command').textContent}]),
  block('As a Plugin',['Claude Code:',{code:`claude plugin marketplace add ${repo}\nclaude plugin install mr-safety-agent@mr-safety-agent`},'Codex: add the marketplace, then install MR Safety Agent from the plugin browser.',{code:`codex plugin marketplace add ${repo}`}]),
  appBlock,
  node('p','2. Ask a question','install-step'),
  node('p','Ask normally or name the skill. Give exact model numbers for device questions. For example: “Find the current US MRI manual for a Medtronic Azure XT DR MRI SureScan pacemaker with two 5076 leads.”'),
  node('p','Live research needs web search and PDF reading in your AI tool. Testing so far has been in Claude Code, with limited testing in ChatGPT Work.','install-fine'));
}
document.querySelector('#how-use').addEventListener('click',showInstall);
document.querySelectorAll('[data-install-help]').forEach(b=>b.addEventListener('click',showInstall));
document.querySelector('#copy-install').addEventListener('click',async()=>{const status=document.querySelector('#install-status');try{await navigator.clipboard.writeText(document.querySelector('#install-command').textContent);status.textContent='Copied';}catch{status.textContent='Select the command to copy.';}});
const guideGrid=document.querySelector('#guide-grid');
fetch('data/guides.json').then(r=>{if(!r.ok)throw Error();return r.json();}).then(data=>{guides=data.guides;guideGrid.replaceChildren();const groups=new Map();for(const g of data.guides){if(!groups.has(g.category)){const box=node('div','','guide-group'),grid=node('div','','guide-grid');box.append(node('h3',g.category,'group-title'),grid);guideGrid.append(box);groups.set(g.category,grid);}const a=guideCard(g);groups.get(g.category).append(a);}}).catch(()=>{guideGrid.replaceChildren(node('p','Guides could not be loaded. Please refresh the page.'));});
document.querySelectorAll('[data-contribute]').forEach(b=>b.addEventListener('click',()=>{openDialog('Build This Resource With Us','CONTRIBUTE');content.append(node('p','Useful contributions include corrected links, clearer resource descriptions, research cases, and professional review. Include a link to the publisher’s own page, the applicable region, and the date you checked it.'),node('p','Open an issue on GitHub to report a problem or suggest a source, or read the contribution guide to propose a change.'));const issue=node('a','Open an Issue ↗','button outline');issue.href='https://github.com/mri-commons/mr-safety-agent/issues/new';issue.target='_blank';issue.rel='noopener';const a=node('a','Read the Contribution Guide ↗','button outline');a.href='https://github.com/mri-commons/mr-safety-agent/blob/main/CONTRIBUTING.md';a.target='_blank';a.rel='noopener';const row=node('div','','dialog-actions');row.append(issue,a);content.append(row);}));
fetch('data/sources.json').then(r=>{if(!r.ok)throw Error('Source data unavailable');return r.json();}).then(data=>{const isTool=s=>s.topics.includes('udi')||s.topics.includes('recalls');sources=data.sources.filter(s=>s.kind!=='manufacturer-portal'&&!isTool(s));renderTools(data.sources.filter(isTool));render();}).catch(()=>{grid.append(node('p','The resource directory could not be loaded. Please refresh the page.'));});

const topicGrid=document.querySelector('#topic-grid');
fetch('data/topics.json').then(r=>{if(!r.ok)throw Error();return r.json();}).then(data=>{topicGrid.replaceChildren();for(const t of data.topics){const a=node('a','','topic-card');a.href=t.url;const foot=node('span','','card-foot');foot.append(node('b','Read →'));a.append(node('span',t.audience,'audience-tag'),node('h3',t.title.split(':')[0]),node('p',t.summary),foot);topicGrid.append(a);}}).catch(()=>{topicGrid.replaceChildren(node('p','Topics could not be loaded. Please refresh the page.'));});
const examples=[
 ['Device Manual','Find the current US MRI technical guide for a Boston Scientific ACCOLADE MRI L311 pacemaker with INGEVITY MRI 7741 and 7742 leads. Confirm the edition, check for safety notices, and list what is still unverified.'],
 ['Hearing Implant','Our patient has a Cochlear Nucleus CI612 cochlear implant with the magnet in place and is scheduled for a 3T brain MRI. Which current US Cochlear document applies, and what does it require?'],
 ['Patient','My dad has a pacemaker and an MRI next week. What should we bring, and what should we ask the imaging team?'],
 ['ACR Guidance','According to the current ACR Manual on MR Safety, what is Zone III, and who controls access to it?'],
 ['Certification','I am a US MRI technologist. Compare the MRSO and MRSE credentials, then suggest a six-week study plan based on the current exam syllabus.'],
];
const tabs=document.querySelector('#prompt-tabs'),promptText=document.querySelector('#prompt-text');
examples.forEach(([label,text],i)=>{const b=node('button',label,'prompt-tab');b.type='button';b.setAttribute('role','tab');b.setAttribute('aria-selected',i===0);b.addEventListener('click',()=>{promptText.textContent=text;document.querySelector('#copy-status').textContent='';tabs.querySelectorAll('button').forEach(x=>x.setAttribute('aria-selected',x===b));});tabs.append(b);});
