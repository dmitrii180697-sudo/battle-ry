import os
from flask import Flask, request, redirect, session, render_template_string
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "battle_of_warriors_2026_secret")
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db():
    if DATABASE_URL:
        return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    else:
        import sqlite3
        conn = sqlite3.connect('battle.db')
        conn.row_factory = sqlite3.Row
        return conn

def init_db():
    try:
        conn = get_db()
        cur = conn.cursor()
        if DATABASE_URL:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS players (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                login TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                gold INT DEFAULT 0,
                exp INT DEFAULT 0,
                level INT DEFAULT 1
            );""")
        else:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                login TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                gold INT DEFAULT 0,
                exp INT DEFAULT 0,
                level INT DEFAULT 1
            );""")
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"DB INIT ERROR: {e}")

init_db()

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@700&display=swap');
body{margin:0;background:#d5c6a5;font-family:Arial}
.wrap{max-width:440px;margin:0 auto;min-height:100vh;background:#fdf6e3;padding:20px;box-sizing:border-box;border-left:3px double #8d7a5a;border-right:3px double #8d7a5a}
.logo{text-align:center;margin:10px 0 25px}
.logo h1{font-family:'Cinzel',serif;font-size:34px;line-height:1.1;color:#2b1d11;margin:10px 0;letter-spacing:1px}
.logo .axes{font-size:52px}
.card{background:#fbf0c8;border:2px solid #b89a66;border-radius:12px;padding:14px 16px;margin:14px 0;box-shadow:0 3px 0 #8d7a5a}
.card label{font-weight:bold;font-size:13px;text-transform:uppercase;color:#4e342e;display:block;margin-bottom:6px}
.card input{width:100%;border:0;background:transparent;font-size:18px;outline:none;color:#3e2723}
.btn{width:100%;padding:16px;background:#5a3523;color:#fbe9c5;border:0;border-radius:12px;font-size:20px;font-weight:bold;cursor:pointer;box-shadow:0 4px 0 #2b1d11;margin-top:18px}
.topbar{display:flex;justify-content:space-between;background:#3e2723;color:#f5e6c8;padding:10px 12px;font-size:14px}
</style>
"""

LOGIN_HTML = CSS + """
<div class="wrap">
<div class="logo"><div class="axes">⚔️</div><h1>BATTLE OF<br>WARRIORS</h1></div>
{% if err %}<div style="background:#ffcdd2;padding:10px;border-radius:8px;color:#b71c1c">{{err}}</div>{% endif %}
<form method="post">
<div class="card"><label>Логин для входа</label><input name="login" placeholder="Введите логин" required></div>
<div class="card"><label>Пароль (от 3 знаков)</label><input name="password" type="password" placeholder="Введите пароль" required></div>
<button class="btn">Вход</button>
</form>
<div style="text-align:center;margin-top:16px"><a href="/reg" style="color:#5a3523;font-weight:bold">Начать игру — Регистрация</a></div>
</div>
"""

REG_HTML = CSS + """
<div class="wrap">
<div class="logo"><div class="axes">⚔️</div><h1>BATTLE OF<br>WARRIORS</h1></div>
<h3 style="text-align:center;font-family:Cinzel;color:#3e2723">Регистрация</h3>
{% if err %}<div style="background:#ffcdd2;padding:10px;border-radius:8px;color:#b71c1c">{{err}}</div>{% endif %}
<form method="post">
<div class="card"><label>Имя героя</label><input name="name" placeholder="Введите имя героя" required></div>
<div class="card"><label>Логин для входа</label><input name="login" placeholder="Введите логин" required minlength="3"></div>
<div class="card"><label>Пароль (от 3 знаков)</label><input name="password" type="password" placeholder="Введите пароль" required minlength="3"></div>
<button class="btn">Зарегистрироваться</button>
</form>
<div style="text-align:center;margin-top:16px">Уже есть аккаунт? <a href="/" style="color:#5a3523;font-weight:bold">Войти</a></div>
</div>
"""

GAME_HTML = CSS + """
<div class="topbar"><span>Герой</span><span>💰 {{p[3] if p[3] else 0}} | ⭐ {{p[4] if p[4] else 0}}</span></div>
<div class="wrap">
<h2>Лагерь — BATTLE OF WARRIORS</h2>
<p>Привет, {{p[1]}}! Версия 0.1 готова.</p>
<p>✅ 3 поля регистрации — без расы, без рефки<br>✅ Золото чинится</p>
<a href="/school" class="btn" style="display:block;text-align:center;text-decoration:none">Школа воинов (скоро)</a>
<a href="/hunt" class="btn" style="display:block;text-align:center;text-decoration:none;background:#8d6e63;margin-top:10px">Промысел (скоро)</a>
<a href="/logout" style="display:block;text-align:center;margin-top:20px;color:#5a3523">Выход</a>
</div>
"""

@app.route("/", methods=["GET","POST"])
def index():
    if request.method=="POST":
        login=request.form.get("login","").strip()
        pw=request.form.get("password","")
        conn=get_db(); cur=conn.cursor()
        if DATABASE_URL:
            cur.execute("SELECT * FROM players WHERE login=%s", (login,))
        else:
            cur.execute("SELECT * FROM players WHERE login=?", (login,))
        row=cur.fetchone()
        cur.close(); conn.close()
        if row and check_password_hash(row[3] if not hasattr(row,'keys') else row["password"], pw):
            session["uid"]= row[0] if not hasattr(row,'keys') else row["id"]
            return redirect("/game")
        return render_template_string(LOGIN_HTML, err="Неверный логин или пароль")
    return render_template_string(LOGIN_HTML, err=None)

@app.route("/reg", methods=["GET","POST"])
def reg():
    if request.method=="POST":
        name=request.form.get("name","").strip()
        login=request.form.get("login","").strip()
        pw=request.form.get("password","")
        if len(name)<2 or len(login)<3 or len(pw)<3:
            return render_template_string(REG_HTML, err="Имя от 2, логин и пароль от 3 знаков")
        conn=get_db(); cur=conn.cursor()
        try:
            hashed=generate_password_hash(pw)
            if DATABASE_URL:
                cur.execute("INSERT INTO players (name, login, password) VALUES (%s,%s,%s) RETURNING id", (name,login,hashed))
                uid=cur.fetchone()["id"]
            else:
                cur.execute("INSERT INTO players (name, login, password) VALUES (?,?,?)", (name,login,hashed))
                uid=cur.lastrowid
            conn.commit()
            session["uid"]=uid
        except Exception as e:
            conn.rollback()
            return render_template_string(REG_HTML, err=f"Логин занят: {e}")
        finally:
            cur.close(); conn.close()
        return redirect("/game")
    return render_template_string(REG_HTML, err=None)

@app.route("/game")
def game():
    if "uid" not in session: return redirect("/")
    conn=get_db(); cur=conn.cursor()
    if DATABASE_URL:
        cur.execute("SELECT * FROM players WHERE id=%s", (session["uid"],))
    else:
        cur.execute("SELECT * FROM players WHERE id=?", (session["uid"],))
    p=cur.fetchone(); cur.close(); conn.close()
    if not p: return redirect("/logout")
    return render_template_string(GAME_HTML, p=p)

@app.route("/school")
def school():
    return "<h2>Школа воинов — в разработке</h2><a href='/game'>В лагерь</a>"
@app.route("/hunt")
def hunt():
    return "<h2>Промысел — в разработке</h2><a href='/game'>В лагерь</a>"
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")
if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)))
