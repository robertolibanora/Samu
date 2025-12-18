/**
 * Service Worker per SAMU PWA
 * Strategia: Cache-First per static assets, Network-First per HTML/API
 * Versione: 1.0.0
 */

const CACHE_NAME = 'samu-pwa-v1.0.0';
const STATIC_CACHE = 'samu-static-v1.0.0';
const DYNAMIC_CACHE = 'samu-dynamic-v1.0.0';

// Risorse statiche da cachare immediatamente (cache-first)
const STATIC_ASSETS = [
  '/static/style.css',
  '/static/admin.css',
  '/static/ux-enhancements.css',
  '/static/pwa-enhancements.css',
  '/static/sfondo.png',
  '/manifest.json',
  '/offline.html',
  // Icone PWA - precache per installazione rapida
  '/static/icons/icon-72x72.png',
  '/static/icons/icon-96x96.png',
  '/static/icons/icon-128x128.png',
  '/static/icons/icon-144x144.png',
  '/static/icons/icon-152x152.png',
  '/static/icons/icon-192x192.png',
  '/static/icons/icon-384x384.png',
  '/static/icons/icon-512x512.png'
];

// Risorse dinamiche (network-first con fallback)
const DYNAMIC_PATTERNS = [
  /^\/$/,
  /^\/register/,
  /^\/admin/,
  /^\/static\/icons\//
];

/**
 * Installazione Service Worker
 * Precaching delle risorse statiche critiche
 */
self.addEventListener('install', (event) => {
  console.log('[SW] Installazione in corso...');
  
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then((cache) => {
        console.log('[SW] Caching risorse statiche');
        return cache.addAll(STATIC_ASSETS);
      })
      .then(() => {
        console.log('[SW] Installazione completata');
        // Forza attivazione immediata (skip waiting)
        return self.skipWaiting();
      })
      .catch((error) => {
        console.error('[SW] Errore durante installazione:', error);
      })
  );
});

/**
 * Attivazione Service Worker
 * Pulizia cache vecchie
 */
self.addEventListener('activate', (event) => {
  console.log('[SW] Attivazione in corso...');
  
  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames
            .filter((cacheName) => {
              // Rimuovi cache vecchie
              return cacheName !== STATIC_CACHE && 
                     cacheName !== DYNAMIC_CACHE &&
                     cacheName.startsWith('samu-');
            })
            .map((cacheName) => {
              console.log('[SW] Rimozione cache vecchia:', cacheName);
              return caches.delete(cacheName);
            })
        );
      })
      .then(() => {
        console.log('[SW] Attivazione completata');
        // Prendi controllo immediato di tutte le pagine
        return self.clients.claim();
      })
  );
});

/**
 * Fetch Handler
 * Strategia di caching intelligente
 */
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Ignora richieste non-GET e chrome-extension
  if (request.method !== 'GET' || url.protocol === 'chrome-extension:') {
    return;
  }

  // Strategia Cache-First per risorse statiche
  if (isStaticAsset(request.url)) {
    event.respondWith(cacheFirst(request));
    return;
  }

  // Strategia Network-First per HTML e API
  if (request.headers.get('accept')?.includes('text/html') || 
      url.pathname.startsWith('/admin') ||
      url.pathname === '/' ||
      url.pathname === '/register') {
    event.respondWith(networkFirst(request));
    return;
  }

  // Default: Network-First con fallback
  event.respondWith(networkFirst(request));
});

/**
 * Cache-First Strategy
 * Per CSS, JS, immagini statiche, manifest
 */
async function cacheFirst(request) {
  try {
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }

    const networkResponse = await fetch(request);
    
    // Cache solo risposte valide
    if (networkResponse && networkResponse.status === 200) {
      const cache = await caches.open(STATIC_CACHE);
      cache.put(request, networkResponse.clone());
    }
    
    return networkResponse;
  } catch (error) {
    console.error('[SW] Errore cache-first:', error);
    // Fallback: prova a servire dalla cache anche se non match esatto
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }
    throw error;
  }
}

/**
 * Network-First Strategy
 * Per HTML e contenuti dinamici
 */
async function networkFirst(request) {
  try {
    const networkResponse = await fetch(request);
    
    // Cache risposte valide
    if (networkResponse && networkResponse.status === 200) {
      const cache = await caches.open(DYNAMIC_CACHE);
      cache.put(request, networkResponse.clone());
    }
    
    return networkResponse;
  } catch (error) {
    console.log('[SW] Network fallito, uso cache:', request.url);
    
    // Fallback: cerca nella cache
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }

    // Se è una richiesta HTML e non c'è cache, mostra offline page
    if (request.headers.get('accept')?.includes('text/html')) {
      const offlinePage = await caches.match('/offline.html');
      if (offlinePage) {
        return offlinePage;
      }
    }

    // Ultimo fallback: risposta generica
    return new Response('Connessione non disponibile', {
      status: 503,
      statusText: 'Service Unavailable',
      headers: new Headers({
        'Content-Type': 'text/plain'
      })
    });
  }
}

/**
 * Verifica se è una risorsa statica
 */
function isStaticAsset(url) {
  return url.includes('/static/') && 
         (url.endsWith('.css') || 
          url.endsWith('.js') || 
          url.endsWith('.png') || 
          url.endsWith('.jpg') || 
          url.endsWith('.jpeg') || 
          url.endsWith('.svg') ||
          url.endsWith('.woff') ||
          url.endsWith('.woff2') ||
          url.includes('/manifest.json') ||
          url.includes('/static/icons/'));
}

/**
 * Message Handler
 * Per comunicazione con la pagina principale
 */
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
  
  if (event.data && event.data.type === 'CACHE_URLS') {
    event.waitUntil(
      caches.open(DYNAMIC_CACHE)
        .then((cache) => {
          return cache.addAll(event.data.urls);
        })
    );
  }
});

