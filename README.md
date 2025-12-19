# SAMU - Sistema di Registrazione Eventi

Sistema web elegante e mobile-first per la registrazione di utenti a eventi, con dashboard admin completa per la gestione, visualizzazione dello storico e statistiche dettagliate.

## Caratteristiche

- **Registrazione Eventi**: Interfaccia intuitiva per la registrazione a eventi specifici
- **Dashboard Admin**: Creazione eventi, visualizzazione registrazioni e storico completo
- **Statistiche Avanzate**: Grafici interattivi per analisi registrazioni per evento, fascia d'età, orari e andamento giornaliero
- **PWA (Progressive Web App)**: Installabile come app nativa su mobile con manifest separati per registrazione e admin
- **Design Luxury/Dark**: Interfaccia elegante con tema dark e accenti gold/yellow
- **Mobile-First**: Design responsive ottimizzato per dispositivi mobili
- **Pagina Presentazione**: Link alla pagina di presentazione dello sviluppatore

## Requisiti

- Python 3.8+
- pip

## Installazione

1. Clona il repository:
```bash
git clone https://github.com/robertolibanora/Samu.git
cd Samu
```

2. Crea un virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # Su Windows: venv\Scripts\activate
```

3. Installa le dipendenze:
```bash
pip install -r requirements.txt
```

4. Configura le variabili d'ambiente:
```bash
cp .env.example .env  # Se esiste, altrimenti crea .env manualmente
```

Modifica `.env` con le tue credenziali:
```
ADMIN_USERNAME=admin
ADMIN_PASSWORD=tuapassword
DB_DIR=/data
PORT=5002
```

5. Avvia l'applicazione:
```bash
python app.py
```

L'applicazione sarà disponibile su `http://localhost:5002`

## Struttura Progetto

```
SAMU/
├── templates/                    # Template HTML
│   ├── admin_dashboard.html     # Dashboard principale admin
│   ├── admin_login.html         # Login admin
│   ├── admin_statistiche.html  # Pagina statistiche con grafici
│   ├── admin_eventi.html        # Lista eventi
│   ├── admin_evento_dettaglio.html  # Dettaglio evento con registrati
│   ├── crea_evento.html         # Creazione nuovo evento
│   ├── register.html            # Pagina registrazione utenti
│   ├── landing.html             # Landing page
│   ├── offline.html             # Pagina offline PWA
│   └── presentazione_roberto.html  # Pagina presentazione sviluppatore
├── static/                      # File statici
│   ├── style.css                # Stili principali
│   ├── admin.css                # Stili admin
│   ├── ux-enhancements.css      # Miglioramenti UX
│   ├── pwa-enhancements.css     # Stili PWA
│   ├── logo.png                 # Logo principale
│   ├── logoadmin.png            # Logo admin
│   ├── profile.png              # Foto profilo sviluppatore
│   ├── sfondo.png               # Immagine di sfondo
│   ├── icons/                   # Icone PWA (vari formati)
│   ├── manifest.json            # Manifest PWA principale
│   ├── manifest-register.json   # Manifest PWA registrazione
│   ├── manifest-admin.json      # Manifest PWA admin
│   ├── service-worker.js        # Service worker PWA
│   └── pwa-init.js              # Inizializzazione PWA
├── data/                        # Directory database (creata automaticamente)
│   └── registrazioni.db         # Database SQLite
├── app.py                       # Applicazione Flask principale
├── requirements.txt             # Dipendenze Python
├── deploy.sh                    # Script di deploy
├── .env                         # Variabili d'ambiente (non committato)
└── README.md
```

## Credenziali Default

- **Username**: admin
- **Password**: admin123 (cambiala subito in produzione!)

## Utilizzo

### Per gli Utenti
1. Vai alla homepage
2. Seleziona un evento disponibile
3. Compila il form di registrazione
4. Conferma la registrazione

### Per l'Admin
1. Accedi a `/admin/login`
2. Crea nuovi eventi da `/admin/evento/crea`
3. Visualizza le registrazioni nella dashboard principale
4. Consulta le statistiche dettagliate in `/admin/statistiche`:
   - Grafico distribuzione per fascia d'età
   - Grafico distribuzione orari di arrivo
   - Grafico registrazioni per evento (con date)
   - Grafico andamento ultimi 7 giorni
5. Naviga tra gli eventi passati per vedere lo storico
6. Visualizza i dettagli di ogni evento con lista completa registrati

### Pagine Disponibili

- `/` - Landing page
- `/register` - Registrazione utenti
- `/admin/login` - Login admin
- `/admin/dashboard` - Dashboard principale
- `/admin/statistiche` - Statistiche e grafici
- `/admin/eventi` - Lista tutti gli eventi
- `/admin/evento/<id>` - Dettaglio evento specifico
- `/admin/evento/crea` - Crea nuovo evento
- `/presentazione` - Pagina presentazione sviluppatore

## Funzionalità Avanzate

### Statistiche e Grafici
- **Grafici interattivi** con Chart.js
- Visualizzazione registrazioni per evento con date formattate
- Analisi distribuzione per fascia d'età
- Analisi orari di arrivo
- Andamento registrazioni ultimi 7 giorni
- Tooltip informativi e design mobile-optimized

### PWA (Progressive Web App)
- **Installabile come app nativa** su iOS e Android
- Due entrypoint separati con stesso nome "SAMU":
  - Registrazione: `/` (manifest-register.json)
  - Admin: `/admin/login` (manifest-admin.json)
- Service worker per funzionalità offline
- Icone ottimizzate per tutti i dispositivi

### Design
- **Tema dark/luxury** con accenti gold (#FFD700) e orange (#FFA500)
- Glassmorphism e effetti blur
- Animazioni fluide e transizioni eleganti
- Logo responsive che si adatta a tutte le dimensioni
- Footer con link alla pagina sviluppatore

## Sicurezza

- Rate limiting sui tentativi di login (max 5 tentativi, lockout 5 minuti)
- Validazione input lato server completa
- Sessioni sicure con scadenza 24 ore
- Password admin configurabile via variabili d'ambiente
- Controllo duplicati per telefono per evento
- Normalizzazione telefoni per evitare falsi positivi

## Licenza

Questo progetto è open source e disponibile sotto licenza MIT.

## Tecnologie Utilizzate

- **Backend**: Flask (Python)
- **Database**: SQLite con WAL mode
- **Frontend**: HTML5, CSS3, JavaScript vanilla
- **Grafici**: Chart.js 4.4.0
- **PWA**: Service Worker, Web App Manifest
- **Styling**: CSS custom con design system dark/luxury

## Note di Sviluppo

- Il database viene creato automaticamente alla prima esecuzione
- Gli eventi possono essere attivi o passati (solo uno attivo alla volta)
- Le registrazioni sono legate a un evento specifico
- Il sistema supporta timezone italiano (Europe/Rome)
- Tutti i telefoni vengono normalizzati (rimozione spazi, trattini, etc.)

## Autore

**Roberto Libanora** - Sviluppatore & Consulente Digitale

- Email: roberto.libanora@sartosrl.com
- LinkedIn: [roberto-libanora-71a3a02b8](https://www.linkedin.com/in/roberto-libanora-71a3a02b8)
- Pagina presentazione: `/presentazione`

## Repository

https://github.com/robertolibanora/Samu

## Licenza

Questo progetto è open source e disponibile sotto licenza MIT.

