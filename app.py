from flask import Flask, render_template, request
import os, json, re, base64, requests

app = Flask(__name__)

# -------------------------------
# CONFIGURAZIONE GITHUB
# -------------------------------
GITHUB_REPO = "emiliomaj60-lang/emiliodati"
GITHUB_PATH = "FILE_PREORDINI"
GITHUB_COUNTER = "counter.json"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")  # su Render va messo nelle Environment Variables

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

# -------------------------------
# FUNZIONI GITHUB
# -------------------------------

def github_get_file(path):
    """Legge un file da GitHub e restituisce (contenuto, sha)."""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    r = requests.get(url, headers=HEADERS)

    if r.status_code == 200:
        data = r.json()
        content = base64.b64decode(data["content"]).decode("utf-8")
        return content, data["sha"]

    return None, None


def github_write_file(path, content, message, sha=None):
    """Scrive o aggiorna un file su GitHub."""
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
    """Legge counter.json da GitHub, lo crea se non esiste."""
    content, sha = github_get_file(GITHUB_COUNTER)

    if content is None:
        # crea counter.json
        github_write_file(GITHUB_COUNTER, '{"counter": 0}', "Create counter.json")
        return 0, None

    data = json.loads(content)
    return data["counter"], sha


def update_counter(new_value, sha):
    """Aggiorna counter.json su GitHub."""
    content = json.dumps({"counter": new_value})
    github_write_file(GITHUB_COUNTER, content, f"Update counter to {new_value}", sha)


# -------------------------------
# UPLOAD ORDINI SU GITHUB
# -------------------------------

def upload_to_github(filename, content):
    """Carica un file CSV su GitHub tramite API."""
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


# -------------------------------
# ROUTES
# -------------------------------

@app.route("/")
def home():
    return "Railway funziona!"


#@app.route("/")
#def home():
 #   return render_template("home.html")


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

        # --- COUNTER SU GITHUB ---
        counter, sha = get_counter()
        numero = counter + 1
        update_counter(numero, sha)

        save_order(cliente, tavolo, coperti, [(o["nome"], o["qta"]) for o in ordine], numero)

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
    return render_template("info.html", testo=testo)


# -------------------------------
# AVVIO SERVER
# -------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)