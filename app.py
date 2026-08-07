from flask import Flask, render_template, request, redirect, session
import os, json, re, base64, requests
from datetime import datetime

app = Flask(__name__)
app.secret_key = "supersegreto123"   # 🔥 NECESSARIO PER USARE session

# -------------------------------
# CONFIGURAZIONE GITHUB
# -------------------------------
GITHUB_REPO = "emiliomaj60-lang/emiliodati"
GITHUB_PATH = "FILE_PREORDINI"
GITHUB_COUNTER = "counter.json"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

# -------------------------------
# FUNZIONI GITHUB
# -------------------------------

def github_get_file(path):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    r = requests.get(url, headers=HEADERS)

    if r.status_code == 200:
        data = r.json()
        content = base64.b64decode(data["content"]).decode("utf-8")
        return content, data["sha"]

    return None, None


def github_write_file(path, content, message, sha=None):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"

    encoded = base64.b64encode(content.encode("utf-8")).decode("utf-8")

    payload = {
        "message": message,
        "content": encoded
    }

    if sha:
        payload["sha"] = sha

    r = requests.put(url, headers=HEADERS, json=payload)

    if r.status_code not in [200, 201]:
        print("ERRORE SCRITTURA GITHUB:", r.text)


# -------------------------------
# COUNTER SU GITHUB
# -------------------------------

def get_counter():
    content, sha = github_get_file(GITHUB_COUNTER)

    if content is None:
        github_write_file(GITHUB_COUNTER, '{"counter": 0}', "Create counter.json")
        return 0, None

    data = json.loads(content)
    return data["counter"], sha


def update_counter(new_value, sha):
    content = json.dumps({"counter": new_value})
    github_write_file(GITHUB_COUNTER, content, f"Update counter to {new_value}", sha)


# -------------------------------
# UPLOAD ORDINI SU GITHUB
# -------------------------------

def upload_to_github(filename, content):
    path = f"{GITHUB_PATH}/{filename}"
    github_write_file(path, content, f"Nuovo ordine: {filename}")


# -------------------------------
# FUNZIONI LOCALI
# -------------------------------

def get_menu():
    menu = []
    try:
        with open("menu_alpini.csv", "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
            for line in lines[1:]:
                nome, prezzo = line.split(",")
                menu.append({"nome": nome, "prezzo": float(prezzo)})
    except FileNotFoundError:
        menu = []
    return menu


def sanitize_filename(name):
    return re.sub(r"[^A-Za-z0-9]", "", name)


def save_order(cliente, tavolo, coperti, items, numero):
    cliente_clean = sanitize_filename(cliente)
    filename = f"{numero}_{cliente_clean}.csv"

    contenuto = "NOME,VALORE\n"
    contenuto += f"NOME_UTENTE,{cliente}\n"
    contenuto += f"TAVOLO,{tavolo}\n"
    contenuto += f"COPERTI,{coperti}\n"
    for nome, qta in items:
        contenuto += f"{nome},{qta}\n"

    upload_to_github(filename, contenuto)


# --------------------------------
# ACCESSI UNIFICATI (UN SOLO FILE)
# --------------------------------

def leggi_accessi():
    try:
        with open("accessi.json", "r") as f:
            return json.load(f)
    except:
        return {"totale": 0, "giorni": {}}


def salva_accessi(data):
    with open("accessi.json", "w") as f:
        json.dump(data, f)


from datetime import datetime
from zoneinfo import ZoneInfo

def registra_accesso():
    data = leggi_accessi()

    oggi = datetime.now(ZoneInfo("Europe/Rome")).strftime("%d/%m/%Y")

    if oggi not in data["giorni"]:
        data["giorni"][oggi] = 0

    data["giorni"][oggi] += 1
    data["totale"] += 1

    salva_accessi(data)

def leggi_menu():
    try:
        with open("menu.json", "r") as f:
            return json.load(f)
    except:
        return {"pietanze": []}

def salva_menu(menu):
    with open("menu.json", "w") as f:
        json.dump(menu, f, indent=4)

# -------------------------------
# ROUTES
# -------------------------------

@app.route("/")
def home():
    registra_accesso()
    return render_template("home.html")


@app.route("/menu", methods=["GET", "POST"])
def menu():
    menu_items = get_menu()

    if request.method == "POST":
        cliente = request.form["cliente"]
        tavolo = request.form["tavolo"]
        coperti = request.form["coperti"]

        ordine = []
        totale = 0

        for item in menu_items:
            qta = request.form.get(item["nome"], "0")
            if qta.strip() != "" and int(qta) > 0:
                qta = int(qta)
                ordine.append({
                    "nome": item["nome"],
                    "qta": qta,
                    "prezzo": item["prezzo"]
                })
                totale += qta * item["prezzo"]

        numero = None

        return render_template("fattura.html",
                               numero=numero,
                               cliente=cliente,
                               tavolo=tavolo,
                               coperti=coperti,
                               ordine=ordine,
                               totale=totale)

    return render_template("menu.html", menu=menu_items)


@app.route("/contatti")
def contatti():
    try:
        with open("contatti.txt", "r", encoding="utf-8") as f:
            testo = f.read()
    except FileNotFoundError:
        testo = "File contatti.txt non trovato."
    return render_template("contatti.html", testo=testo)


@app.route("/istruzioni")
def istruzioni():
    try:
        with open("istruzioni.txt", "r", encoding="utf-8") as f:
            testo = f.read()
    except FileNotFoundError:
        testo = "File istruzioni.txt non trovato."
    return render_template("istruzioni.html", testo=testo)


@app.route("/info")
def info():
    try:
        with open("info_festa.txt", "r", encoding="utf-8") as f:
            testo = f.read()
    except FileNotFoundError:
        testo = "File info_festa.txt non trovato."

    utilizzi = leggi_accessi()["totale"]

    return render_template("info.html", testo=testo, utilizzi=utilizzi)


ADMIN_PASSWORD = "a"

@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        pwd = request.form.get("password")
        if pwd == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect("/admin/home")
        else:
            return render_template("admin.html", errore=True)

    return render_template("admin.html")

@app.route("/admin/home")
def admin_home():
    if not session.get("admin"):
        return redirect("/admin")
    return render_template("admin_home.html")

@app.route("/admin/accessi")
def admin_accessi():
    if not session.get("admin"):
        return redirect("/admin")

    accessi = leggi_accessi()  # usa la funzione che hai già
    return render_template("admin_accessi.html", accessi=accessi)

@app.route("/admin/menu", methods=["GET", "POST"])
def admin_menu():
    menu = leggi_menu()  # menu.json → {"pietanze": [...]}

    if request.method == "POST":
        for i, p in enumerate(menu["pietanze"]):
            chiave = f"esaurita_{i}"
            p["esaurita"] = (chiave in request.form)

        salva_menu(menu)

    # 🔥 PASSO SOLO LA LISTA DELLE PIETANZE
    return render_template("admin_menu.html", menu=menu["pietanze"])

@app.route("/ordina", methods=["POST"])
def ordina():
    menu = leggi_menu()["pietanze"]
    dati = request.form

    for item in menu:
        if item["esaurita"]:
            qta = int(dati.get(item["nome"], 0)) if dati.get(item["nome"]) else 0
            if qta > 0:
                return "❌ Questa pietanza è esaurita. Non puoi ordinarla."

    # continua con l'ordine...

@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect("/")

# -------------------------------
# AVVIO SERVER
# -------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
