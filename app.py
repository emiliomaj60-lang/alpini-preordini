from flask import Flask, render_template, request
import os, json, re

app = Flask(__name__)

FOLDER = "FILE_PREORDINI"
os.makedirs(FOLDER, exist_ok=True)

COUNTER_FILE = "counter.json"
if not os.path.exists(COUNTER_FILE):
    with open(COUNTER_FILE, "w") as f:
        json.dump({"counter": 0}, f)

# -------------------------------
# FUNZIONI
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

def get_counter():
    with open(COUNTER_FILE, "r") as f:
        return json.load(f)["counter"]

def update_counter(new_value):
    with open(COUNTER_FILE, "w") as f:
        json.dump({"counter": new_value}, f)

def sanitize_filename(name):
    return re.sub(r"[^A-Za-z0-9]", "", name)

def save_order(cliente, tavolo, coperti, items, numero):
    cliente_clean = sanitize_filename(cliente)
    filename = f"{FOLDER}/{numero}_{cliente_clean}.csv"
    with open(filename, "w", encoding="utf-8") as f:
        f.write("NOME,VALORE\n")
        f.write(f"NOME_UTENTE,{cliente}\n")
        f.write(f"TAVOLO,{tavolo}\n")
        f.write(f"COPERTI,{coperti}\n")
        for nome, qta in items:
            f.write(f"{nome},{qta}\n")

# -------------------------------
# ROUTES
# -------------------------------
@app.route("/")
def home():
    return render_template("home.html")

@app.route("/menu", methods=["GET","POST"])
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

        numero = get_counter() + 1
        update_counter(numero)
        save_order(cliente, tavolo, coperti, [(o["nome"], o["qta"]) for o in ordine], numero)

        return render_template("fattura.html",
                               numero=numero,
                               cliente=cliente,
                               tavolo=tavolo,
                               coperti=coperti,
                               ordine=ordine,
                               totale=totale)
    return render_template("menu.html", menu=menu_items)

# -------------------------------
# CONTATTI (lettura da contatti.txt)
# -------------------------------
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
    port = int(os.environ.get("PORT", 5000))  # compatibile con Render
    app.run(host="0.0.0.0", port=port)