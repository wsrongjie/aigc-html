const VERSION='workfit-v4-offline-20261020';
const APP=['./index.html','./manifest.webmanifest'];
self.addEventListener('install', e => e.waitUntil(caches.open(VERSION).then(c=>c.addAll(APP)).then(()=>self.skipWaiting())));
self.addEventListener('activate', e => e.waitUntil(caches.keys().then(names=>Promise.all(names.filter(n=>n.startsWith('workfit-')&&n!==VERSION).map(n=>caches.delete(n)))).then(()=>self.clients.claim())));
self.addEventListener('fetch', e => { if(e.request.method!=='GET'||e.request.mode==='no-cors')return; const url=new URL(e.request.url); if(url.origin!==self.location.origin || !url.pathname.includes('/workfit-v4/'))return; e.respondWith(caches.match(e.request).then(hit=>hit||fetch(e.request).then(response=>{if(response.ok){const copy=response.clone();caches.open(VERSION).then(c=>c.put(e.request,copy))}return response}).catch(()=> {if(e.request.mode==='navigate')return caches.match('./index.html');return Response.error()}))); });
