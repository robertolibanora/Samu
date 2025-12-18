/**
 * PWA Initialization Script
 * Registra il service worker e gestisce installazione PWA
 * Nessun framework, vanilla JS puro
 */

(function() {
  'use strict';

  // Verifica supporto Service Worker
  if ('serviceWorker' in navigator) {
    // Registra Service Worker
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('/service-worker.js')
        .then((registration) => {
          console.log('[PWA] Service Worker registrato:', registration.scope);

          // Gestione aggiornamenti
          registration.addEventListener('updatefound', () => {
            const newWorker = registration.installing;
            console.log('[PWA] Nuovo Service Worker trovato');

            newWorker.addEventListener('statechange', () => {
              if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                // Nuovo SW disponibile, ricarica pagina
                console.log('[PWA] Nuova versione disponibile, ricarico...');
                window.location.reload();
              }
            });
          });
        })
        .catch((error) => {
          console.error('[PWA] Errore registrazione Service Worker:', error);
        });

      // Gestione messaggi dal Service Worker
      navigator.serviceWorker.addEventListener('message', (event) => {
        console.log('[PWA] Messaggio da SW:', event.data);
      });
    });
  }

  // Gestione installazione PWA
  let deferredPrompt;
  const installButton = document.getElementById('install-pwa-button');

  window.addEventListener('beforeinstallprompt', (e) => {
    // Previeni il prompt automatico
    e.preventDefault();
    deferredPrompt = e;
    
    // Mostra pulsante installazione personalizzato se presente
    if (installButton) {
      installButton.style.display = 'block';
      installButton.addEventListener('click', () => {
        // Mostra prompt installazione
        deferredPrompt.prompt();
        deferredPrompt.userChoice.then((choiceResult) => {
          if (choiceResult.outcome === 'accepted') {
            console.log('[PWA] Utente ha accettato installazione');
          } else {
            console.log('[PWA] Utente ha rifiutato installazione');
          }
          deferredPrompt = null;
          if (installButton) {
            installButton.style.display = 'none';
          }
        });
      });
    }
  });

  // Gestione stato offline/online
  window.addEventListener('online', () => {
    console.log('[PWA] Connessione ripristinata');
    // Rimuovi indicatore offline se presente
    const offlineIndicator = document.getElementById('offline-indicator');
    if (offlineIndicator) {
      offlineIndicator.classList.add('hidden');
    }
  });

  window.addEventListener('offline', () => {
    console.log('[PWA] Connessione persa');
    // Mostra indicatore offline se presente
    const offlineIndicator = document.getElementById('offline-indicator');
    if (offlineIndicator) {
      offlineIndicator.classList.remove('hidden');
    }
  });

  // Verifica stato iniziale
  if (!navigator.onLine) {
    window.dispatchEvent(new Event('offline'));
  }

  // Prevenzione zoom involontario (double-tap)
  let lastTouchEnd = 0;
  document.addEventListener('touchend', (event) => {
    const now = Date.now();
    if (now - lastTouchEnd <= 300) {
      event.preventDefault();
    }
    lastTouchEnd = now;
  }, false);

  // Prevenzione pull-to-refresh su iOS
  let touchStartY = 0;
  document.addEventListener('touchstart', (e) => {
    touchStartY = e.touches[0].clientY;
  }, { passive: true });

  document.addEventListener('touchmove', (e) => {
    const touchY = e.touches[0].clientY;
    const scrollTop = document.documentElement.scrollTop || document.body.scrollTop;
    
    // Se si scrolla verso l'alto dalla top, previeni default
    if (touchY > touchStartY && scrollTop === 0) {
      e.preventDefault();
    }
  }, { passive: false });

  console.log('[PWA] Inizializzazione completata');
})();

