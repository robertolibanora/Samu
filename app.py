from flask import Flask, render_template, request, redirect, session, url_for, jsonify
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

# Database
DB_DIR = os.environ.get("DB_DIR", "/data")
try:
    os.makedirs(DB_DIR, exist_ok=True)
    test_file = os.path.join(DB_DIR, ".test_write")
    with open(test_file, 'w') as f:
        f.write('test')
    os.remove(test_file)
except (OSError, PermissionError):
    DB_DIR = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(DB_DIR, exist_ok=True)

DB_NAME = os.path.join(DB_DIR, "registrazioni.db")

def get_db_connection():
    """Crea una connessione al database"""
    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL")
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

print("🔐 Utenti configurati:")
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
            data_creazione TEXT DEFAULT CURRENT_TIMESTAMP,
            attivo INTEGER DEFAULT 1
        )
    """)
    
    # Tabella registrazioni con riferimento a evento
    c.execute("""
        CREATE TABLE IF NOT EXISTS registrazioni (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            evento_id INTEGER NOT NULL,
            nome TEXT NOT NULL,
            cognome TEXT NOT NULL,
            data_nascita TEXT NOT NULL,
            luogo_nascita TEXT NOT NULL,
            telefono TEXT NOT NULL,
            data_registrazione TEXT DEFAULT CURRENT_TIMESTAMP,
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
    
    # Aggiungi colonna evento_id se non esiste (migrazione)
    try:
        c.execute("PRAGMA table_info(registrazioni)")
        columns = [row[1] for row in c.fetchall()]
        if 'evento_id' not in columns:
            c.execute("ALTER TABLE registrazioni ADD COLUMN evento_id INTEGER DEFAULT 1")
            conn.commit()
    except sqlite3.OperationalError:
        pass
    
    conn.close()

init_db()

# ---------------------------
# ROUTE: HOME - REGISTRAZIONE
# ---------------------------
@app.route("/", methods=["GET", "POST"])
def register():
    # Carica eventi attivi per la selezione
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id, nome, descrizione, prezzo FROM eventi WHERE attivo = 1 ORDER BY data_creazione DESC")
    eventi = c.fetchall()
    conn.close()
    
    if request.method == "POST":
        # Validazione input
        evento_id = request.form.get("evento_id", "").strip()
        nome = request.form.get("nome", "").strip()
        cognome = request.form.get("cognome", "").strip()
        data_nascita = request.form.get("data_nascita", "").strip()
        luogo_nascita = request.form.get("luogo_nascita", "").strip()
        telefono = request.form.get("telefono", "").strip()
        
        # Validazione evento
        if not evento_id:
            return render_template("register.html", eventi=eventi, error="Seleziona un evento.")
        try:
            evento_id = int(evento_id)
        except ValueError:
            return render_template("register.html", eventi=eventi, error="Evento non valido.")
        
        # Validazione campi obbligatori
        if not nome or len(nome) > 100:
            return render_template("register.html", eventi=eventi, error="Nome non valido (max 100 caratteri).")
        if not cognome or len(cognome) > 100:
            return render_template("register.html", eventi=eventi, error="Cognome non valido (max 100 caratteri).")
        if not data_nascita:
            return render_template("register.html", eventi=eventi, error="Data di nascita obbligatoria.")
        if not luogo_nascita or len(luogo_nascita) > 100:
            return render_template("register.html", eventi=eventi, error="Luogo di nascita non valido (max 100 caratteri).")
        if not telefono:
            return render_template("register.html", eventi=eventi, error="Numero di telefono obbligatorio.")

        # Validazione età minima (12 anni)
        try:
            data_nascita_obj = datetime.strptime(data_nascita, "%Y-%m-%d")
            oggi = now_italia()
            eta = (oggi.date() - data_nascita_obj.date()).days // 365
            if eta < 12:
                return render_template("register.html", eventi=eventi,
                                     error=f"Devi avere almeno 12 anni per registrarti. Età attuale: {eta} anni.")
        except ValueError:
            return render_template("register.html", eventi=eventi,
                                 error="Data di nascita non valida.")

        # Validazione telefono: deve iniziare con 3
        telefono_pulito = ''.join(filter(str.isdigit, telefono))
        if not telefono_pulito.startswith('3'):
            return render_template("register.html", eventi=eventi,
                                 error="Il numero di telefono deve iniziare con 3.")
        if len(telefono_pulito) < 9 or len(telefono_pulito) > 15:
            return render_template("register.html", eventi=eventi,
                                 error="Il numero di telefono deve avere tra 9 e 15 cifre.")
        telefono = telefono_pulito

        conn = None
        try:
            conn = get_db_connection()
            c = conn.cursor()
            
            # Verifica che l'evento esista e sia attivo
            c.execute("SELECT id FROM eventi WHERE id = ? AND attivo = 1", (evento_id,))
            if not c.fetchone():
                return render_template("register.html", eventi=eventi,
                                     error="Evento non valido o non più disponibile.")
            
            # Controlla se il telefono è già registrato per questo evento
            c.execute("SELECT COUNT(*) FROM registrazioni WHERE telefono = ? AND evento_id = ?", (telefono, evento_id))
            if c.fetchone()[0] > 0:
                return render_template("register.html", eventi=eventi,
                                     error="Sei già registrato per questo evento.")
            
            # Inserisci la registrazione
            data_registrazione = now_italia().strftime("%Y-%m-%d %H:%M:%S")
            c.execute("""
                INSERT INTO registrazioni (evento_id, nome, cognome, data_nascita, luogo_nascita, telefono, data_registrazione)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (evento_id, nome, cognome, data_nascita, luogo_nascita, telefono, data_registrazione))
            conn.commit()
            
            return render_template("register.html", eventi=eventi,
                                 success="Registrazione completata con successo!")
        except sqlite3.IntegrityError:
            return render_template("register.html", eventi=eventi,
                                 error="Sei già registrato per questo evento.")
        except Exception as e:
            print(f"Errore durante la registrazione: {e}")
            return render_template("register.html", eventi=eventi,
                                 error="Si è verificato un errore durante la registrazione. Riprova.")
        finally:
            if conn:
                conn.close()

    return render_template("register.html", eventi=eventi)

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
            return redirect(url_for("admin"))
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
# ROUTE: ADMIN - LISTA EVENTI E REGISTRATI
# ---------------------------
@app.route("/admin")
def admin():
    if not session.get("user_logged_in"):
        return redirect(url_for("admin_login"))
    
    user_role = session.get("user_role")
    if user_role != "admin":
        return redirect(url_for("admin_login"))
    
    # Filtro evento dalla query string
    evento_id = request.args.get("evento_id", None)
    
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # Lista tutti gli eventi (storico)
        c.execute("""
            SELECT id, nome, descrizione, prezzo, data_creazione, attivo,
                   (SELECT COUNT(*) FROM registrazioni WHERE registrazioni.evento_id = eventi.id) as num_registrati
            FROM eventi 
            ORDER BY data_creazione DESC
        """)
        eventi = c.fetchall()
        
        # Seleziona evento attivo o quello specificato
        evento_corrente = None
        if evento_id:
            try:
                evento_id = int(evento_id)
                c.execute("SELECT id, nome, descrizione, prezzo FROM eventi WHERE id = ?", (evento_id,))
                evento_corrente = c.fetchone()
            except ValueError:
                pass
        
        if not evento_corrente:
            # Prendi l'evento attivo più recente
            c.execute("SELECT id, nome, descrizione, prezzo FROM eventi WHERE attivo = 1 ORDER BY data_creazione DESC LIMIT 1")
            evento_corrente = c.fetchone()
        
        registrati = []
        totale_iscritti = 0
        
        if evento_corrente:
            evento_id = evento_corrente[0]
            # Conta registrati per questo evento
            c.execute("SELECT COUNT(*) FROM registrazioni WHERE evento_id = ?", (evento_id,))
            totale_iscritti = c.fetchone()[0]
            
            # Lista registrati per questo evento
            c.execute("""
                SELECT r.id, r.nome, r.cognome, r.data_nascita, r.luogo_nascita, r.telefono, r.data_registrazione 
                FROM registrazioni r
                WHERE r.evento_id = ?
                ORDER BY r.cognome, r.nome
            """, (evento_id,))
        registrati = c.fetchall()
    except Exception as e:
        print(f"Errore durante il caricamento dati admin: {e}")
        eventi = []
        evento_corrente = None
        totale_iscritti = 0
        registrati = []
    finally:
        if conn:
            conn.close()

    user_name = session.get("user_name", "Admin")
    
    return render_template("admin.html", 
                         eventi=eventi,
                         evento_corrente=evento_corrente,
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
        
            
            
            data_creazione = now_italia().strftime("%Y-%m-%d %H:%M:%S")
            c.execute("""
                INSERT INTO eventi (nome, descrizione, prezzo, data_creazione, attivo)
                VALUES (?, ?, ?, ?, 1)
            """, (nome, descrizione, prezzo, data_creazione))
            conn.commit()
            
            return redirect(url_for("admin"))
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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5002))
    app.run(debug=False, port=port, host="0.0.0.0")
