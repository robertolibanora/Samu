from flask import Flask, render_template, request, redirect, session, url_for, jsonify, send_from_directory
import sqlite3
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from collections import defaultdict
from threading import Lock

# Carica variabili d'ambiente da file .env se esiste
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = Flask(__name__)
app.secret_key = "nonservepasswords"
app.permanent_session_lifetime = timedelta(hours=24)

# Timezone italiano
TIMEZONE_ITALIA = ZoneInfo("Europe/Rome")

def now_italia():
    """Restituisce la data/ora corrente nel timezone italiano"""
    return datetime.now(TIMEZONE_ITALIA)

# ============================================================
# BASE PATHS (ROBUSTI, NO PATH RELATIVI)
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

DB_NAME = os.path.join(DATA_DIR, "registrazioni.db")

# ============================================================
# DATABASE HELPERS
# ============================================================

def get_db_connection():
    """Crea una connessione al database"""
    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn

# Rate limiting per login
failed_login_attempts = defaultdict(list)
failed_login_lock = Lock()
MAX_LOGIN_ATTEMPTS = 5
LOGIN_LOCKOUT_TIME = 300

def check_rate_limit(ip_address):
    """Verifica se l'IP ha superato il limite di tentativi di login"""
    with failed_login_lock:
        now = datetime.now().timestamp()
        failed_login_attempts[ip_address] = [
            ts for ts in failed_login_attempts[ip_address] 
            if now - ts < LOGIN_LOCKOUT_TIME
        ]
        if len(failed_login_attempts[ip_address]) >= MAX_LOGIN_ATTEMPTS:
            return False, LOGIN_LOCKOUT_TIME - int(now - failed_login_attempts[ip_address][0])
        return True, 0

def record_failed_login(ip_address):
    """Registra un tentativo di login fallito"""
    with failed_login_lock:
        failed_login_attempts[ip_address].append(datetime.now().timestamp())

def clear_failed_logins(ip_address):
    """Cancella i tentativi falliti dopo un login riuscito"""
    with failed_login_lock:
        if ip_address in failed_login_attempts:
            del failed_login_attempts[ip_address]

# Utenti - solo admin
def get_env(key, default):
    """Ottiene variabile d'ambiente, rimuove spazi e gestisce valori vuoti"""
    value = os.environ.get(key, default)
    if value:
        return value.strip()
    return default

ADMIN_USERNAME = get_env("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = get_env("ADMIN_PASSWORD", "admin123")

USERS = {
    ADMIN_USERNAME: {
        "password": ADMIN_PASSWORD,
        "role": "admin",
        "name": "Admin"
    }
}

print("Utenti configurati:")
for username, user_data in USERS.items():
    print(f"   - {username} ({user_data['role']})")

# Inizializzazione database
def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Tabella eventi
    c.execute("""
        CREATE TABLE IF NOT EXISTS eventi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            descrizione TEXT,
            prezzo REAL DEFAULT 0.0,
            data_evento DATE NOT NULL,
            data_creazione TEXT DEFAULT CURRENT_TIMESTAMP,
            attivo INTEGER DEFAULT 1
        )
    """)
    
    # Migrazione: aggiungi/modifica data_evento se necessario
    try:
        c.execute("PRAGMA table_info(eventi)")
        columns = [row[1] for row in c.fetchall()]
        if 'data_evento' not in columns:
            c.execute("ALTER TABLE eventi ADD COLUMN data_evento DATE")
            conn.commit()
        # Nota: SQLite non supporta ALTER COLUMN per cambiare tipo,
        # ma DATE è semanticamente corretto anche se internamente è TEXT
    except sqlite3.OperationalError:
        pass
    
    # Tabella registrazioni con riferimento a evento
    c.execute("""
        CREATE TABLE IF NOT EXISTS registrazioni (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            evento_id INTEGER NOT NULL,
            nome TEXT NOT NULL,
            cognome TEXT NOT NULL,
            telefono TEXT NOT NULL,
            eta_fascia TEXT NOT NULL CHECK(eta_fascia IN ('>18', '18-21', '21-25', '25-30', '30+')),
            orario_arrivo TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (evento_id) REFERENCES eventi(id)
        )
    """)
    
    # Indici per performance
    try:
        c.execute("CREATE INDEX IF NOT EXISTS idx_evento_id ON registrazioni(evento_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_telefono_evento ON registrazioni(telefono, evento_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_cognome_nome ON registrazioni(cognome, nome)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_evento_attivo ON eventi(attivo)")
        conn.commit()
    except sqlite3.OperationalError:
        pass
    
    # Migrazione: aggiorna struttura tabella registrazioni se necessario
    try:
        c.execute("PRAGMA table_info(registrazioni)")
        columns = [row[1] for row in c.fetchall()]
        
        # Se la tabella esiste con vecchia struttura, aggiungi/modifica colonne
        if 'data_nascita' in columns or 'luogo_nascita' in columns:
            # Tabella vecchia - aggiungi nuove colonne se non esistono
            if 'eta_fascia' not in columns:
                c.execute("ALTER TABLE registrazioni ADD COLUMN eta_fascia TEXT")
            if 'orario_arrivo' not in columns:
                c.execute("ALTER TABLE registrazioni ADD COLUMN orario_arrivo TEXT")
            if 'created_at' not in columns:
                c.execute("ALTER TABLE registrazioni ADD COLUMN created_at TEXT DEFAULT CURRENT_TIMESTAMP")
            conn.commit()
        
        # Aggiungi evento_id se non esiste
        if 'evento_id' not in columns:
            c.execute("ALTER TABLE registrazioni ADD COLUMN evento_id INTEGER DEFAULT 1")
            conn.commit()
        
        # Migrazione: normalizza tutti i telefoni esistenti (rimuovi spazi, trattini, etc.)
        # per evitare problemi con il controllo duplicati
        try:
            c.execute("SELECT id, telefono FROM registrazioni")
            registrazioni = c.fetchall()
            for reg_id, telefono in registrazioni:
                if telefono:
                    # Normalizza il telefono (rimuovi caratteri non numerici)
                    telefono_normalizzato = ''.join(filter(str.isdigit, telefono))
                    if telefono_normalizzato != telefono:
                        c.execute("UPDATE registrazioni SET telefono = ? WHERE id = ?", 
                                (telefono_normalizzato, reg_id))
            conn.commit()
        except Exception as e:
            print(f"Errore durante normalizzazione telefoni: {e}")
            pass
    except sqlite3.OperationalError as e:
        print(f"Errore migrazione: {e}")
        pass
    
    conn.close()

init_db()

# ---------------------------
# ROUTE: HOME - LANDING PAGE
# ---------------------------
@app.route("/")
def landing():
    """Pagina landing pre-registrazione"""
    return render_template("landing.html")

# ---------------------------
# ROUTE: PRESENTAZIONE ROBERTO
# ---------------------------
@app.route("/presentazione")
def presentazione_roberto():
    """Pagina di presentazione di Roberto Libanora"""
    return render_template("presentazione_roberto.html")

# ---------------------------
# ROUTE: PRIVACY
# ---------------------------
@app.route("/privacy")
def privacy():
    """Pagina informativa sulla privacy"""
    return render_template("privacy.html")

# ---------------------------
# ROUTE: REGISTRAZIONE
# ---------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    # Carica l'evento attivo (solo uno può essere attivo)
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id, nome, descrizione, prezzo FROM eventi WHERE attivo = 1 ORDER BY data_creazione DESC LIMIT 1")
    evento_attivo = c.fetchone()
    conn.close()
    
    if request.method == "POST":
        # Validazione input
        nome = request.form.get("nome", "").strip()
        cognome = request.form.get("cognome", "").strip()
        telefono = request.form.get("telefono", "").strip()
        eta_fascia = request.form.get("eta_fascia", "").strip()
        orario_arrivo = request.form.get("orario_arrivo", "").strip()
        
        # Verifica che ci sia un evento attivo
        if not evento_attivo:
            return render_template("register.html", evento=None, error="Nessun evento disponibile al momento.")
        
        evento_id = evento_attivo[0]
        
        # Validazione campi obbligatori
        if not nome or len(nome) > 100:
            return render_template("register.html", evento=evento_attivo, error="Nome obbligatorio (max 100 caratteri).")
        if not cognome or len(cognome) > 100:
            return render_template("register.html", evento=evento_attivo, error="Cognome obbligatorio (max 100 caratteri).")
        if not telefono:
            return render_template("register.html", evento=evento_attivo, error="Numero di telefono obbligatorio.")
        if not eta_fascia or eta_fascia not in ['>18', '18-21', '21-25', '25-30', '30+']:
            return render_template("register.html", evento=evento_attivo, error="Fascia d'età obbligatoria.")
        if not orario_arrivo:
            return render_template("register.html", evento=evento_attivo, error="Orario di arrivo obbligatorio.")
        
        # Validazione consenso privacy
        privacy_consent = request.form.get("privacy_consent")
        if not privacy_consent:
            return render_template("register.html", evento=evento_attivo, error="È necessario accettare l'informativa sulla privacy per completare la registrazione.")

        # Validazione telefono: deve iniziare con 3
        telefono_pulito = ''.join(filter(str.isdigit, telefono))
        if not telefono_pulito.startswith('3'):
            return render_template("register.html", evento=evento_attivo,
                                 error="Il numero di telefono deve iniziare con 3.")
        if len(telefono_pulito) < 9 or len(telefono_pulito) > 15:
            return render_template("register.html", evento=evento_attivo,
                                 error="Il numero di telefono deve avere tra 9 e 15 cifre.")
        telefono = telefono_pulito

        # Validazione orario
        try:
            # Verifica formato HH:MM
            parts = orario_arrivo.split(':')
            if len(parts) != 2:
                raise ValueError
            hour = int(parts[0])
            minute = int(parts[1])
            if hour < 0 or hour > 23 or minute < 0 or minute > 59:
                raise ValueError
        except (ValueError, IndexError):
            return render_template("register.html", evento=evento_attivo,
                                 error="Orario non valido. Usa il formato HH:MM (es. 14:30).")

        conn = None
        try:
            conn = get_db_connection()
            c = conn.cursor()
            
            # Verifica che l'evento esista e sia attivo
            c.execute("SELECT id FROM eventi WHERE id = ? AND attivo = 1", (evento_id,))
            if not c.fetchone():
                return render_template("register.html", evento=evento_attivo,
                                     error="Evento non valido o non più disponibile.")
            
            # Controlla se il telefono è già registrato per questo evento
            # Normalizza il telefono nel database per il confronto (rimuovi spazi, trattini, etc.)
            # Confronta solo telefoni normalizzati per evitare falsi positivi
            c.execute("""
                SELECT COUNT(*) FROM registrazioni 
                WHERE REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(telefono, ' ', ''), '-', ''), '.', ''), '(', ''), ')', '') = ?
                AND evento_id = ?
            """, (telefono_pulito, evento_id))
            count = c.fetchone()[0]
            if count > 0:
                return render_template("register.html", evento=evento_attivo,
                                     error="Sei già registrato per questo evento.")
            
            # Inserisci la registrazione (usa telefono_pulito normalizzato)
            created_at = now_italia().strftime("%Y-%m-%d %H:%M:%S")
            c.execute("""
                INSERT INTO registrazioni (evento_id, nome, cognome, telefono, eta_fascia, orario_arrivo, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (evento_id, nome, cognome, telefono_pulito, eta_fascia, orario_arrivo, created_at))
            conn.commit()
            
            return render_template("register.html", evento=evento_attivo,
                                 success="Registrazione completata con successo!")
        except sqlite3.IntegrityError as e:
            print(f"IntegrityError: {e}")
            return render_template("register.html", evento=evento_attivo,
                                 error="Sei già registrato per questo evento.")
        except Exception as e:
            print(f"Errore durante la registrazione: {e}")
            return render_template("register.html", evento=evento_attivo,
                                 error="Si è verificato un errore durante la registrazione. Riprova.")
        finally:
            if conn:
                conn.close()

    return render_template("register.html", evento=evento_attivo)

# ---------------------------
# ROUTE: LOGIN ADMIN
# ---------------------------
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        ip_address = request.remote_addr or request.environ.get('HTTP_X_FORWARDED_FOR', 'unknown').split(',')[0]
        
        allowed, wait_time = check_rate_limit(ip_address)
        if not allowed:
            minutes = wait_time // 60
            seconds = wait_time % 60
            return render_template("admin_login.html", 
                                 error=f"Troppi tentativi di login falliti. Riprova tra {minutes} minuti e {seconds} secondi.")
        
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        
        if not username or not password:
            record_failed_login(ip_address)
            return render_template("admin_login.html", error="Username e password sono obbligatori")
        
        username_found = None
        for stored_username in USERS.keys():
            if stored_username.lower() == username.lower():
                username_found = stored_username
                break
        
        if username_found and USERS[username_found]["password"] == password:
            clear_failed_logins(ip_address)
            session.permanent = True
            session["user_logged_in"] = True
            session["username"] = username_found
            session["user_role"] = USERS[username_found]["role"]
            session["user_name"] = USERS[username_found]["name"]
            return redirect(url_for("admin_dashboard"))
        else:
            record_failed_login(ip_address)
            return render_template("admin_login.html", error="Username o password errati")
    
    return render_template("admin_login.html")

# ---------------------------
# ROUTE: LOGOUT
# ---------------------------
@app.route("/admin/logout")
def admin_logout():
    session.pop("user_logged_in", None)
    session.pop("username", None)
    session.pop("user_role", None)
    session.pop("user_name", None)
    return redirect(url_for("admin_login"))

# ---------------------------
# ROUTE: ADMIN - DASHBOARD
# ---------------------------
@app.route("/admin")
@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get("user_logged_in"):
        return redirect(url_for("admin_login"))
    
    user_role = session.get("user_role")
    if user_role != "admin":
        return redirect(url_for("admin_login"))
    
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # Prossimo evento (attivo)
        c.execute("""
            SELECT id, nome, descrizione, prezzo, data_evento, data_creazione,
                   (SELECT COUNT(*) FROM registrazioni WHERE registrazioni.evento_id = eventi.id) as num_registrati
            FROM eventi 
            WHERE attivo = 1 
            ORDER BY data_evento ASC
            LIMIT 1
        """)
        prossimo_evento = c.fetchone()
        
        # Statistiche generali
        c.execute("SELECT COUNT(*) FROM eventi")
        totale_eventi = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM registrazioni")
        totale_registrazioni = c.fetchone()[0]
        
        # Ultimi 5 eventi per preview
        c.execute("""
            SELECT id, nome, data_evento, attivo,
                   (SELECT COUNT(*) FROM registrazioni WHERE registrazioni.evento_id = eventi.id) as num_registrati
            FROM eventi 
            ORDER BY data_evento DESC
            LIMIT 5
        """)
        ultimi_eventi = c.fetchall()
        
        # Registrati per l'evento attivo (se esiste)
        registrati_evento_attivo = []
        if prossimo_evento:
            c.execute("""
                SELECT id, nome, cognome, telefono, eta_fascia, orario_arrivo, created_at
                FROM registrazioni
                WHERE evento_id = ?
                ORDER BY created_at DESC
            """, (prossimo_evento[0],))
            registrati_evento_attivo = c.fetchall()
        
    except Exception as e:
        print(f"Errore durante il caricamento dashboard: {e}")
        prossimo_evento = None
        totale_eventi = 0
        totale_registrazioni = 0
        ultimi_eventi = []
        registrati_evento_attivo = []
    finally:
        if conn:
            conn.close()

    user_name = session.get("user_name", "Admin")
    
    return render_template("admin_dashboard.html", 
                         prossimo_evento=prossimo_evento,
                         totale_eventi=totale_eventi,
                         totale_registrazioni=totale_registrazioni,
                         ultimi_eventi=ultimi_eventi,
                         registrati_evento_attivo=registrati_evento_attivo,
                         user_name=user_name)

# ---------------------------
# ROUTE: ADMIN - STATISTICHE
# ---------------------------
@app.route("/admin/statistiche")
def admin_statistiche():
    if not session.get("user_logged_in"):
        return redirect(url_for("admin_login"))
    
    user_role = session.get("user_role")
    if user_role != "admin":
        return redirect(url_for("admin_login"))
    
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # Statistiche per fascia d'età
        c.execute("""
            SELECT eta_fascia, COUNT(*) as count
            FROM registrazioni
            GROUP BY eta_fascia
            ORDER BY 
                CASE eta_fascia
                    WHEN '>18' THEN 1
                    WHEN '18-21' THEN 2
                    WHEN '21-25' THEN 3
                    WHEN '25-30' THEN 4
                    WHEN '30+' THEN 5
                END
        """)
        eta_stats = c.fetchall()
        
        # Statistiche per orario di arrivo (raggruppate per ora)
        c.execute("""
            SELECT substr(orario_arrivo, 1, 2) as ora, COUNT(*) as count
            FROM registrazioni
            GROUP BY ora
            ORDER BY ora
        """)
        orario_stats = c.fetchall()
        
        # Registrazioni per evento (con data evento)
        c.execute("""
            SELECT e.data_evento, COUNT(r.id) as count
            FROM eventi e
            LEFT JOIN registrazioni r ON e.id = r.evento_id
            GROUP BY e.id, e.data_evento
            ORDER BY e.data_evento ASC
        """)
        evento_stats = c.fetchall()
        
        # Registrazioni per giorno (ultimi 7 giorni)
        c.execute("""
            SELECT date(created_at) as giorno, COUNT(*) as count
            FROM registrazioni
            WHERE date(created_at) >= date('now', '-7 days')
            GROUP BY giorno
            ORDER BY giorno
        """)
        giornaliere_stats = c.fetchall()
        
    except Exception as e:
        print(f"Errore durante il caricamento statistiche: {e}")
        eta_stats = []
        orario_stats = []
        evento_stats = []
        giornaliere_stats = []
    finally:
        if conn:
            conn.close()

    user_name = session.get("user_name", "Admin")
    
    return render_template("admin_statistiche.html",
                         eta_stats=eta_stats,
                         orario_stats=orario_stats,
                         evento_stats=evento_stats,
                         giornaliere_stats=giornaliere_stats,
                         user_name=user_name)

# ---------------------------
# ROUTE: ADMIN - LISTA EVENTI PASSATI
# ---------------------------
@app.route("/admin/eventi")
def admin_eventi():
    if not session.get("user_logged_in"):
        return redirect(url_for("admin_login"))
    
    user_role = session.get("user_role")
    if user_role != "admin":
        return redirect(url_for("admin_login"))
    
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # Lista tutti gli eventi ordinati per data evento
        c.execute("""
            SELECT id, nome, descrizione, prezzo, data_evento, data_creazione, attivo,
                   (SELECT COUNT(*) FROM registrazioni WHERE registrazioni.evento_id = eventi.id) as num_registrati
            FROM eventi 
            ORDER BY data_evento DESC, data_creazione DESC
        """)
        eventi = c.fetchall()
        
    except Exception as e:
        print(f"Errore durante il caricamento eventi: {e}")
        eventi = []
    finally:
        if conn:
            conn.close()

    user_name = session.get("user_name", "Admin")
    
    return render_template("admin_eventi.html",
                         eventi=eventi,
                         user_name=user_name)

# ---------------------------
# ROUTE: ADMIN - DETTAGLIO EVENTO
# ---------------------------
@app.route("/admin/evento/<int:evento_id>")
def admin_evento_dettaglio(evento_id):
    if not session.get("user_logged_in"):
        return redirect(url_for("admin_login"))
    
    user_role = session.get("user_role")
    if user_role != "admin":
        return redirect(url_for("admin_login"))
    
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # Dettagli evento
        c.execute("""
            SELECT id, nome, descrizione, prezzo, data_evento, data_creazione, attivo
            FROM eventi 
            WHERE id = ?
        """, (evento_id,))
        evento = c.fetchone()
        
        if not evento:
            return redirect(url_for("admin_eventi"))
        
        # Conta registrati
        c.execute("SELECT COUNT(*) FROM registrazioni WHERE evento_id = ?", (evento_id,))
        totale_iscritti = c.fetchone()[0]
        
        # Lista registrati per questo evento
        c.execute("""
            SELECT r.id, r.nome, r.cognome, r.telefono, r.eta_fascia, r.orario_arrivo, r.created_at 
            FROM registrazioni r
            WHERE r.evento_id = ?
            ORDER BY r.cognome, r.nome
        """, (evento_id,))
        registrati = c.fetchall()
        
    except Exception as e:
        print(f"Errore durante il caricamento dettaglio evento: {e}")
        evento = None
        totale_iscritti = 0
        registrati = []
    finally:
        if conn:
            conn.close()

    if not evento:
        return redirect(url_for("admin_eventi"))

    user_name = session.get("user_name", "Admin")
    
    return render_template("admin_evento_dettaglio.html",
                         evento=evento,
                         totale_iscritti=totale_iscritti,
                         registrati=registrati,
                         user_name=user_name)

# ---------------------------
# ROUTE: CREA EVENTO
# ---------------------------
@app.route("/admin/evento/crea", methods=["GET", "POST"])
def crea_evento():
    if not session.get("user_logged_in"):
        return redirect(url_for("admin_login"))
    
    user_role = session.get("user_role")
    if user_role != "admin":
        return redirect(url_for("admin_login"))
    
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        descrizione = request.form.get("descrizione", "").strip()
        prezzo_str = request.form.get("prezzo", "0").strip()
        
        if not nome or len(nome) > 200:
            return render_template("crea_evento.html", 
                                 error="Nome evento obbligatorio (max 200 caratteri).")
        
        try:
            prezzo = float(prezzo_str) if prezzo_str else 0.0
            if prezzo < 0:
                prezzo = 0.0
        except ValueError:
            prezzo = 0.0
        
        conn = None
        try:
            conn = get_db_connection()
            c = conn.cursor()
            
            # Validazione data evento
            data_evento = request.form.get("data_evento", "").strip()
            if not data_evento:
                return render_template("crea_evento.html", 
                                     error="Data evento obbligatoria.")
            
            try:
                # Verifica formato data
                datetime.strptime(data_evento, "%Y-%m-%d")
            except ValueError:
                return render_template("crea_evento.html", 
                                     error="Data evento non valida. Usa il formato YYYY-MM-DD.")
            
            # Disattiva tutti gli altri eventi (solo uno può essere attivo)
            c.execute("UPDATE eventi SET attivo = 0 WHERE attivo = 1")
            
            # Crea il nuovo evento come attivo
            data_creazione = now_italia().strftime("%Y-%m-%d %H:%M:%S")
            c.execute("""
                INSERT INTO eventi (nome, descrizione, prezzo, data_evento, data_creazione, attivo)
                VALUES (?, ?, ?, ?, ?, 1)
            """, (nome, descrizione, prezzo, data_evento, data_creazione))
            conn.commit()
            
            return redirect(url_for("admin_dashboard"))
        except Exception as e:
            print(f"Errore durante la creazione evento: {e}")
            return render_template("crea_evento.html", 
                                 error="Errore durante la creazione dell'evento.")
        finally:
            if conn:
                conn.close()

    return render_template("crea_evento.html")

# ---------------------------
# ROUTE: ELIMINA REGISTRAZIONE
# ---------------------------
@app.route("/admin/delete", methods=["POST"])
def delete_registrazione():
    if not session.get("user_logged_in"):
        return jsonify({"ok": False, "error": "Non autorizzato"}), 401
    
    user_role = session.get("user_role")
    if user_role != "admin":
        return jsonify({"ok": False, "error": "Solo admin può eliminare registrazioni"}), 403
    
    data = request.get_json()
    persona_id = data.get("persona_id")
    
    if not persona_id:
        return jsonify({"ok": False, "error": "ID persona mancante"}), 400
    
    try:
        persona_id = int(persona_id)
    except (ValueError, TypeError):
        return jsonify({"ok": False, "error": "ID persona non valido"}), 400
    
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        c.execute("SELECT nome, cognome FROM registrazioni WHERE id = ?", (persona_id,))
        persona = c.fetchone()
        if not persona:
            return jsonify({"ok": False, "error": "Persona non trovata"}), 404
        
        c.execute("DELETE FROM registrazioni WHERE id = ?", (persona_id,))
        conn.commit()
        
        return jsonify({"ok": True, "message": f"Registrazione di {persona[0]} {persona[1]} eliminata con successo"})
    except Exception as e:
        print(f"Errore durante l'eliminazione: {e}")
        return jsonify({"ok": False, "error": "Errore durante l'eliminazione"}), 500
    finally:
        if conn:
            conn.close()

# ---------------------------
# ROUTE: PWA - MANIFEST (per retrocompatibilità)
# ---------------------------
@app.route("/manifest.json")
def manifest():
    """Serve il manifest.json per PWA (retrocompatibilità - default registrazione)"""
    return send_from_directory('static', 'manifest-register.json', mimetype='application/manifest+json')

# ---------------------------
# ROUTE: PWA - MANIFEST REGISTRAZIONE
# ---------------------------
@app.route("/manifest-register.json")
def manifest_register():
    """Serve il manifest per la PWA di registrazione"""
    return send_from_directory('static', 'manifest-register.json', mimetype='application/manifest+json')

# ---------------------------
# ROUTE: PWA - MANIFEST ADMIN
# ---------------------------
@app.route("/manifest-admin.json")
def manifest_admin():
    """Serve il manifest per la PWA admin"""
    return send_from_directory('static', 'manifest-admin.json', mimetype='application/manifest+json')

# ---------------------------
# ROUTE: PWA - SERVICE WORKER
# ---------------------------
@app.route("/service-worker.js")
def service_worker():
    """Serve il service worker con content-type corretto"""
    return send_from_directory('static', 'service-worker.js', mimetype='application/javascript')

# ---------------------------
# ROUTE: PWA - OFFLINE PAGE
# ---------------------------
@app.route("/offline.html")
def offline_page():
    """Serve la pagina offline"""
    return render_template("offline.html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5005))
    app.run(debug=False, port=port, host="0.0.0.0")
