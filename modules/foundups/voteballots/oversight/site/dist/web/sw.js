'use strict';
// Cache only the public-method application shell. Never cache APIs or external requests.
const CACHE='oversight-public-shell-v0.5.0';
const SHELL=['./','./index.html','./style.css','./app.js','./documents.js','./explore.js','./manifest.webmanifest','./icons/icon-192.png','./icons/icon-512.png','./icons/icon.svg'];
self.addEventListener('install',e=>e.waitUntil(caches.open(CACHE).then(c=>c.addAll(SHELL))));
self.addEventListener('activate',e=>e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith('oversight-public-shell-')&&k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim())));
self.addEventListener('fetch',e=>{const u=new URL(e.request.url),base=new URL(self.registration.scope);if(e.request.method!=='GET'||u.origin!==base.origin)return;const relative=u.pathname.slice(base.pathname.length);if(!['','index.html','style.css','app.js','documents.js','explore.js','manifest.webmanifest','icons/icon-192.png','icons/icon-512.png','icons/icon.svg'].includes(relative)||u.search)return;e.respondWith(fetch(e.request).catch(()=>caches.match(e.request).then(r=>r||new Response('The public playbook is offline. Reconnect to open the latest document.',{status:503,headers:{'Content-Type':'text/plain'}}))));});
