# SAMU - Sistema di Registrazione Eventi

Sistema web semplice e mobile-first per la registrazione di utenti a eventi, con dashboard admin per la gestione e visualizzazione dello storico.

## 🚀 Caratteristiche

- **Registrazione Eventi**: Gli utenti possono registrarsi per eventi specifici
- **Dashboard Admin**: Creazione eventi, visualizzazione registrazioni e storico
- **Mobile-First**: Design responsive ottimizzato per dispositivi mobili
- **Semplice e Veloce**: Interfaccia minimalista e facile da usare

## 📋 Requisiti

- Python 3.8+
- pip

## 🛠️ Installazione

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

## 📁 Struttura Progetto

```
SAMU/
├── templates/          # Template HTML
│   ├── admin.html
│   ├── admin_login.html
│   ├── crea_evento.html
│   └── register.html
├── static/             # File statici (CSS, immagini)
│   └── style.css
├── app.py              # Applicazione Flask principale
├── requirements.txt    # Dipendenze Python
├── .env                # Variabili d'ambiente (non committato)
└── README.md
```

## 🔐 Credenziali Default

- **Username**: admin
- **Password**: admin123 (cambiala subito in produzione!)

## 📱 Utilizzo

### Per gli Utenti
1. Vai alla homepage
2. Seleziona un evento disponibile
3. Compila il form di registrazione
4. Conferma la registrazione

### Per l'Admin
1. Accedi a `/admin/login`
2. Crea nuovi eventi da `/admin/evento/crea`
3. Visualizza le registrazioni nella dashboard
4. Naviga tra gli eventi passati per vedere lo storico

## 🛡️ Sicurezza

- Rate limiting sui tentativi di login
- Validazione input lato server
- Sessioni sicure
- Password admin configurabile via variabili d'ambiente

## 📝 Licenza

Questo progetto è open source e disponibile sotto licenza MIT.

## 👤 Autore

Roberto Libanora

## 🔗 Repository

https://github.com/robertolibanora/Samu

