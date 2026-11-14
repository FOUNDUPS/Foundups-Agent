'use strict';
// Catalog links are not permission grants. Only verified Google Docs and local sources are linked.
(function(){
 const local=p=>typeof p==='string'&&!p.includes('..')&&/^[A-Za-z0-9_./-]+\.(html|md)$/.test(p)&&!p.startsWith('/');
 const google=u=>typeof u==='string'&&/^https:\/\/docs\.google\.com\/document\/d\/[A-Za-z0-9_-]+\/edit(?:\?usp=drivesdk)?$/.test(u);
 const api={items:[],status:'loading',hydrate(){
  document.querySelectorAll('[data-document]').forEach(box=>{
   const path=box.dataset.document,doc=api.items.find(x=>x.path===path);box.replaceChildren();
   const link=(label,url,isGoogle=false,download=false)=>{const a=document.createElement('a');a.textContent=label;a.href=url;if(isGoogle){a.target='_blank';a.rel='noopener noreferrer';}if(download)a.download='';box.append(a);};
   const read=doc?.read_url||(path.startsWith('docs/')?path.slice(5):path).replace(/\.md$/,'.html');
   if(local(read))link('Read draft →',read);
   if(doc&&google(doc.google_url))link('Google Docs ↗',doc.google_url,true);
   if(local(path))link('Download source ↓',path,false,true);
  });
 }};
 window.oversightDocs=api;
 fetch('documents.json').then(r=>{if(!r.ok)throw Error('catalog');return r.json();}).then(rows=>{if(!Array.isArray(rows))throw Error('catalog shape');api.items=rows.filter(d=>local(d.path)&&local(d.read_url)&&google(d.google_url));api.status='ready';api.hydrate();window.dispatchEvent(new Event('documents-ready'));}).catch(()=>{api.status='error';api.hydrate();window.dispatchEvent(new Event('documents-ready'));});
})();
