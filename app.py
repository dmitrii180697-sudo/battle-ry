import os, random
from flask import Flask, request, redirect, session, render_template_string
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "battle_of_warriors_2026")
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
        conn = get_db(); cur = conn.cursor()
        q = """
        CREATE TABLE IF NOT EXISTS players (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            login TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            gold INT DEFAULT 10,
            exp INT DEFAULT 0,
            level INT DEFAULT 1,
            hp INT DEFAULT 30
        );""" if DATABASE_URL else """
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            login TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            gold INT DEFAULT 10,
            exp INT DEFAULT 0,
            level INT DEFAULT 1,
            hp INT DEFAULT 30
        );"""
        cur.execute(q); conn.commit(); cur.close(); conn.close()
    except Exception as e: print(e)

init_db()

BASE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@700&display=swap');
body{margin:0;background:#d5c6a5;font-family:Arial}
.wrap{max-width:480px;margin:0 auto;min-height:100vh;background:#fdf6e3;padding:14px;box-sizing:border-box;border-left:3px double #8d7a5a;border-right:3px double #8d7a5a}
.logo{text-align:center} .logo h1{font-family:'Cinzel',serif;font-size:30px;color:#2b1d11;margin:6px}
.card{background:#fbf0c8;border:2px solid #b89a66;border-radius:12px;padding:12px 14px;margin:10px 0}
.card input{width:100%;border:0;background:transparent;font-size:18px;outline:none}
.btn{width:100%;padding:14px;background:#5a3523;color:#fbe9c5;border:0;border-radius:12px;font-size:18px;font-weight:bold;cursor:pointer;box-shadow:0 4px 0 #2b1d11;margin-top:10px;display:block;text-align:center;text-decoration:none}
.top{display:flex;justify-content:space-between;background:#3e2723;color:#f5e6c8;padding:10px 12px;border-radius:8px;font-size:14px}
.hpbar{height:14px;background:#444;border-radius:7px;overflow:hidden;margin:6px 0}
.hpfill{height:100%;transition:0.3s}
.my{background:#4caf50} .enemy{background:#d32f2f}
.log{background:#fff8dc;border:1px dashed #b89a66;padding:8px;border-radius:8px;height:160px;overflow:auto;font-size:13px;line-height:1.4}
.move{border:2px solid #8d6e63;border-radius:10px;padding:10px;margin:6px 0;background:#efebe9;cursor:pointer;text-align:left;width:100%}
</style>
"""

LOGIN = BASE_CSS+"""<div class="wrap"><div class="logo"><h1>BATTLE OF<br>WARRIORS</h1><div style="font-size:50px">⚔️</div></div>
{% if err %}<div style="background:#ffcdd2;padding:10px;border-radius:8px;color:#b71c1c">{{err}}</div>{% endif %}
<form method="post"><div class="card"><input name="login" placeholder="Логин" required></div><div class="card"><input name="password" type="password" placeholder="Пароль" required></div><button class="btn">Вход</button></form>
<div style="text-align:center;margin-top:12px"><a href="/reg" style="color:#5a3523;font-weight:bold">Регистрация</a></div></div>"""

REG = BASE_CSS+"""<div class="wrap"><div class="logo"><h1>BATTLE OF<br>WARRIORS</h1></div><h3 style="text-align:center;font-family:Cinzel">Регистрация</h3>
{% if err %}<div style="background:#ffcdd2;padding:10px;border-radius:8px;color:#b71c1c">{{err}}</div>{% endif %}
<form method="post"><div class="card"><input name="name" placeholder="Имя героя" required></div><div class="card"><input name="login" placeholder="Логин" required minlength="3"></div><div class="card"><input name="password" type="password" placeholder="Пароль" required></div><button class="btn">Начать игру</button></form>
<div style="text-align:center;margin-top:12px">Есть аккаунт? <a href="/">Войти</a></div></div>"""

CAMP = BASE_CSS+"""
<div class="wrap"><div class="top"><span>{{p[1]}} [{{p[5]}} lvl]</span><span>💰{{p[3]}} ⭐{{p[4]}}</span></div>
<h2 style="font-family:Cinzel;text-align:center">Лагерь</h2>
<a href="/school" class="btn">⚔️ Школа Воинов [Бой с ответкой]</a>
<a href="/hunt" class="btn" style="background:#6d4c41">🌲 Промысел (скоро)</a>
<a href="/logout" style="display:block;text-align:center;margin-top:18px">Выход</a></div>"""

SCHOOL = BASE_CSS+"""
<div class="wrap">
<div class="top"><span>Школа</span><span>💰{{gold}} ⭐{{exp}}</span></div>
<h3 style="text-align:center;font-family:Cinzel">Манекен vs Ты</h3>
<div style="text-align:center">🪵 vs 🧍</div>

<div style="font-size:12px;margin-top:8px">ТЫ HP: {{my_hp}}/30</div>
<div class="hpbar"><div class="hpfill my" style="width:{{my_perc}}%"></div></div>

<div style="font-size:12px">МАНЕКЕН HP: {{hp}}/25</div>
<div class="hpbar"><div class="hpfill enemy" style="width:{{hp_perc}}%"></div></div>

<div class="log">{{log|safe}}</div>

{% if hp>0 and my_hp>0 %}
<form method="post">
<button name="m" value="1" class="move">🗡️ Колющий (3-5) - быстрый</button>
<button name="m" value="2" class="move">⚔️ Режущий (4-6) - точный</button>
<button name="m" value="3" class="move">🪓 Рубящий (3-7 +25% крит)</button>
</form>
{% elif hp<=0 %}
<div class="card" style="background:#c8e6c9;text-align:center"><b>Победа! Манекен сломан</b><br>+5 exp +{{reward}} gold</div>
<form method="post"><button name="m" value="reset" class="btn">Новый бой</button></form>
{% else %}
<div class="card" style="background:#ffcdd2;text-align:center"><b>Ты проиграл! Тебя вырубили</b><br>HP восстановлено</div>
<form method="post"><button name="m" value="reset" class="btn">Встать и драться</button></form>
{% endif %}

<a href="/game" class="btn" style="background:#8d6e63">← В лагерь</a>
</div>"""

@app.route("/", methods=["GET","POST"])
def index():
    if request.method=="POST":
        login=request.form.get("login","").strip(); pw=request.form.get("password","")
        conn=get_db(); cur=conn.cursor()
        if DATABASE_URL: cur.execute("SELECT * FROM players WHERE login=%s",(login,))
        else: cur.execute("SELECT * FROM players WHERE login=?",(login,))
        row=cur.fetchone(); cur.close(); conn.close()
        if row and check_password_hash(row[3] if not DATABASE_URL else row["password"], pw):
            session["uid"]=row[0] if not DATABASE_URL else row["id"]
            session["my_hp"]=30; session["dummy_hp"]=25; session["log"]="Вышел на арену. Бей!"
            session["last_dmg"]=0
            return redirect("/game")
        return render_template_string(LOGIN, err="Неверный логин/пароль")
    return render_template_string(LOGIN, err=None)

@app.route("/reg", methods=["GET","POST"])
def reg():
    if request.method=="POST":
        name=request.form.get("name","").strip(); login=request.form.get("login","").strip(); pw=request.form.get("password","")
        if len(name)<2 or len(login)<3 or len(pw)<3: return render_template_string(REG, err="Имя от 2, логин/пароль от 3")
        conn=get_db(); cur=conn.cursor()
        try:
            h=generate_password_hash(pw)
            if DATABASE_URL:
                cur.execute("INSERT INTO players (name,login,password) VALUES (%s,%s,%s) RETURNING id",(name,login,h)); uid=cur.fetchone()["id"]
            else:
                cur.execute("INSERT INTO players (name,login,password) VALUES (?,?,?)",(name,login,h)); uid=cur.lastrowid
            conn.commit(); session["uid"]=uid; session["my_hp"]=30; session["dummy_hp"]=25; session["log"]="Новый боец на арене!"
        except Exception:
            conn.rollback(); return render_template_string(REG, err="Логин занят")
        finally: cur.close(); conn.close()
        return redirect("/game")
    return render_template_string(REG, err=None)

@app.route("/game")
def game():
    if "uid" not in session: return redirect("/")
    conn=get_db(); cur=conn.cursor()
    if DATABASE_URL: cur.execute("SELECT * FROM players WHERE id=%s",(session["uid"],))
    else: cur.execute("SELECT * FROM players WHERE id=?",(session["uid"],))
    p=cur.fetchone(); cur.close(); conn.close()
    if not p: return redirect("/logout")
    return render_template_string(CAMP, p=p)

@app.route("/school", methods=["GET","POST"])
def school():
    if "uid" not in session: return redirect("/")
    if "dummy_hp" not in session: session["dummy_hp"]=25
    if "my_hp" not in session: session["my_hp"]=30
    if "log" not in session: session["log"]="Бой начался!"
    
    if request.method=="POST":
        m=request.form.get("m")
        if m=="reset":
            session["dummy_hp"]=25; session["my_hp"]=30
            session["log"]="Новый бой! Ты полон сил.<br>"+session["log"]
            session.pop("reward",None)
        else:
            # ТВОЙ УДАР
            dmg=0
            if m=="1": dmg=random.randint(3,5); name="Колющий"
            elif m=="2": dmg=random.randint(4,6); name="Режущий"
            else: dmg=random.randint(3,7); name="Рубящий"
            crit=False
            if m=="3" and random.random()<0.25: dmg+=4; crit=True
            
            session["dummy_hp"]-=dmg
            hit_msg = f"<div>⚔️ Ты [{name}] на <b>{dmg}{' КРИТ!' if crit else ''}</b></div>"
            session["log"]=hit_msg+session["log"]

            # ПРОВЕРКА ПОБЕДЫ
            if session["dummy_hp"]<=0:
                reward=random.randint(1,3)
                conn=get_db(); cur=conn.cursor()
                if DATABASE_URL: cur.execute("UPDATE players SET gold=gold+%s, exp=exp+5 WHERE id=%s",(reward,session["uid"]))
                else: cur.execute("UPDATE players SET gold=gold+?, exp=exp+5 WHERE id=?",(reward,session["uid"]))
                conn.commit(); cur.close(); conn.close()
                session["log"]=f"<div style='color:green'><b>💀 Манекен повержен! +5 exp +{reward}💰</b></div>"+session["log"]
                session["reward"]=reward
            else:
                # ОТВЕТ МАНЕКЕНА
                edmg=random.randint(2,5)
                if random.random()<0.15: edmg+=2
                session["my_hp"]-=edmg
                session["log"]=f"<div>🪵 Манекен бьет на <b style='color:#b71c1c'>{edmg}</b> в ответ!</div>"+session["log"]
                if session["my_hp"]<=0:
                    session["log"]=f"<div style='color:red'><b>☠️ Ты упал без сознания...</b></div>"+session["log"]

    conn=get_db(); cur=conn.cursor()
    if DATABASE_URL: cur.execute("SELECT gold,exp FROM players WHERE id=%s",(session["uid"],))
    else: cur.execute("SELECT gold,exp FROM players WHERE id=?",(session["uid"],))
    row=cur.fetchone(); cur.close(); conn.close()
    gold=row[0] if not DATABASE_URL else row["gold"]; exp=row[1] if not DATABASE_URL else row["exp"]
    
    hp=session["dummy_hp"]; my_hp=session["my_hp"]
    hp_perc=max(0,int(hp/25*100)); my_perc=max(0,int(my_hp/30*100))
    reward=session.get("reward",2)
    return render_template_string(SCHOOL, gold=gold, exp=exp, hp=hp, hp_perc=hp_perc, my_hp=my_hp, my_perc=my_perc, log=session["log"], reward=reward)

@app.route("/hunt")
def hunt(): return BASE_CSS+'<div class="wrap"><h3>Промысел скоро</h3><a href="/game" class="btn">В лагерь</a></div>'
@app.route("/logout")
def logout(): session.clear(); return redirect("/")
if __name__=="__main__": app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)))
