import os, random
from flask import Flask, request, redirect, session, render_template_string, send_from_directory
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
        if DATABASE_URL:
            cur.execute("""CREATE TABLE IF NOT EXISTS players (id SERIAL PRIMARY KEY, name TEXT, login TEXT UNIQUE, password TEXT, gold INT DEFAULT 15, silver INT DEFAULT 50, rubin INT DEFAULT 0, exp INT DEFAULT 0, level INT DEFAULT 1, hp INT DEFAULT 20)""")
            cur.execute("ALTER TABLE players ADD COLUMN IF NOT EXISTS silver INT DEFAULT 50")
            cur.execute("ALTER TABLE players ADD COLUMN IF NOT EXISTS rubin INT DEFAULT 0")
        else:
            cur.execute("""CREATE TABLE IF NOT EXISTS players (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, login TEXT UNIQUE, password TEXT, gold INT DEFAULT 15, silver INT DEFAULT 50, rubin INT DEFAULT 0, exp INT DEFAULT 0, level INT DEFAULT 1, hp INT DEFAULT 20)""")
            try: cur.execute("ALTER TABLE players ADD COLUMN silver INT DEFAULT 50")
            except: pass
            try: cur.execute("ALTER TABLE players ADD COLUMN rubin INT DEFAULT 0")
            except: pass
        conn.commit(); cur.close(); conn.close()
    except Exception as e: print("init", e)
init_db()

MOBI_CSS = """
<style>
body{margin:0;background:#2b2218;font-family:Arial}
.wrap{max-width:480px;margin:0 auto;min-height:100vh;background:#d2b87e;position:relative}
.topbar{background:#e6c78f;border-bottom:3px solid #5a3e22;display:flex;justify-content:center;padding:6px}
.top-scroll{background:#fdf6c8;border:2px solid #8a6a3d;border-radius:12px;padding:5px 10px;display:flex;gap:10px;font-weight:bold;font-size:14px;box-shadow:inset 0 2px 0 #fff;flex-wrap:wrap;justify-content:center}
.frame{margin:8px;background:#3d2817;padding:8px;border-radius:4px;box-shadow:0 0 0 3px #7a5a33,0 0 0 6px #3d2817}
.frame-inner{position:relative;background:#000;height:220px;overflow:hidden;border:2px solid #2b1a0e}
.frame-inner img{width:100%;height:100%;object-fit:cover}
.label{margin:-14px auto 0;width:260px;background:#f5e6c0;border:2px solid #5a3e22;text-align:center;padding:10px;font-weight:bold;font-family:serif;border-radius:8px}
.btn-orange{display:block;width:90%;margin:10px auto;background:linear-gradient(#ffb84d,#ff8c00);border:2px solid #5a3e22;border-radius:6px;padding:12px;text-align:center;font-weight:bold;font-size:18px;color:#3d2817;text-decoration:none;box-shadow:0 3px 0 #5a3e22}
.btn-row{display:flex;background:#e8d9b0;border:2px solid #5a3e22;margin:8px;border-radius:6px;padding:6px;align-items:center;justify-content:space-between}
.bottom{position:fixed;bottom:0;left:0;right:0;max-width:480px;margin:0 auto;background:#5a321a;color:#f5e6c0;display:flex;justify-content:space-between;padding:10px 16px;font-size:13px}
</style>
"""

def get_player(uid):
    conn=get_db(); cur=conn.cursor()
    if DATABASE_URL: cur.execute("SELECT * FROM players WHERE id=%s",(uid,))
    else: cur.execute("SELECT * FROM players WHERE id=?",(uid,))
    p=cur.fetchone(); cur.close(); conn.close()
    return p

def topbar_html(p):
    lvl = p["level"] if DATABASE_URL else p[7] if len(p)>7 else 1
    gold = p["gold"] if DATABASE_URL else p[4] if len(p)>4 else 15
    silver = p["silver"] if DATABASE_URL else (p["silver"] if "silver" in p.keys() else 50) if not DATABASE_URL else p.get("silver",50)
    # safe fallback
    try: silver = p["silver"]
    except: silver = 50
    try: rubin = p["rubin"]
    except: rubin = 0
    try: hp = p["hp"]
    except: hp = 20
    if not DATABASE_URL:
        lvl = p["level"] if "level" in p.keys() else 1
        gold = p["gold"] if "gold" in p.keys() else 15
    return f'<div class="topbar"><div class="top-scroll"><span>⭐ {lvl}</span><span>❤️ {hp}</span><span>💎 {rubin}</span><span>🪙 {gold}</span><span>⚪ {silver}</span></div></div>'

GAME = MOBI_CSS + """
<div class="wrap">
{{topbar|safe}}
<div class="frame"><div class="frame-inner"><img src="/camp.jpg" onerror="this.src='https://i.imgur.com/8Km9tLL.jpg'"></div></div>
<div class="label">Боевой Лагерь</div>
<a href="/camp" class="btn-orange">🏕️ Лагерь</a>
<a href="/promysel" class="btn-orange" style="background:linear-gradient(#aed581,#689f38)">🌲 Промысел</a>
<div class="btn-row"><span>📜 Задания (0/1/0)</span><a href="/quests" class="btn-orange" style="width:auto;margin:0;padding:6px 18px;font-size:14px;text-decoration:none;color:#3d2817">Пасс</a></div>
<div style="height:60px"></div>
<div class="bottom"><span>Меню</span><span id="clock">--:--:--</span><span><a href="/logout" style="color:#f5e6c0;text-decoration:none">Выход</a></span></div>
</div>
<script>setInterval(()=>{let d=new Date();document.getElementById('clock').innerText=d.toLocaleTimeString('ru-RU')},1000)</script>
"""

@app.route("/camp.jpg")
def camp_img():
    try: return send_from_directory('.', 'camp.jpg')
    except: return redirect("https://i.imgur.com/8Km9tLL.jpg")

@app.route("/")
def index_root():
    if "uid" in session: return redirect("/game")
    return render_template_string(MOBI_CSS+"""
<div class="wrap" style="display:flex;flex-direction:column;justify-content:center;padding:20px"><h1 style="text-align:center;font-family:serif">BATTLE OF<br>WARRIORS</h1>
<form method="post" action="/login"><div style="background:#f5e6c0;border:2px solid #5a3e22;padding:10px;margin:8px"><input name="login" placeholder="Логин" style="width:100%;border:0;background:transparent;font-size:18px" required></div>
<div style="background:#f5e6c0;border:2px solid #5a3e22;padding:10px;margin:8px"><input name="password" type="password" placeholder="Пароль" style="width:100%;border:0;background:transparent;font-size:18px" required></div>
<button class="btn-orange">Вход</button></form><a href="/reg" style="text-align:center;display:block;margin-top:10px;color:#3d2817;font-weight:bold">Регистрация</a></div>""")

@app.route("/login", methods=["POST"])
def login():
    login=request.form.get("login","").strip(); pw=request.form.get("password","")
    conn=get_db(); cur=conn.cursor()
    if DATABASE_URL: cur.execute("SELECT * FROM players WHERE login=%s",(login,))
    else: cur.execute("SELECT * FROM players WHERE login=?",(login,))
    row=cur.fetchone(); cur.close(); conn.close()
    if row and check_password_hash(row["password"] if DATABASE_URL else row[3], pw):
        session["uid"]=row["id"] if DATABASE_URL else row["id"]; session["my_hp"]=20; session["dummy_hp"]=25; session["log"]="В лагере"
        return redirect("/game")
    return "Неверный логин/пароль <a href='/'>назад</a>"

@app.route("/reg", methods=["GET","POST"])
def reg():
    if request.method=="POST":
        name=request.form.get("name","").strip(); login=request.form.get("login","").strip(); pw=request.form.get("password","")
        conn=get_db(); cur=conn.cursor()
        try:
            h=generate_password_hash(pw)
            if DATABASE_URL: cur.execute("INSERT INTO players (name,login,password,gold,silver,rubin) VALUES (%s,%s,%s,15,50,0) RETURNING id",(name,login,h)); uid=cur.fetchone()["id"]
            else: cur.execute("INSERT INTO players (name,login,password,gold,silver,rubin) VALUES (?,?,?,15,50,0)",(name,login,h)); uid=cur.lastrowid
            conn.commit(); session["uid"]=uid; session["my_hp"]=20; session["dummy_hp"]=25
        except Exception as e: print(e); conn.rollback(); return "Логин занят <a href='/reg'>назад</a>"
        finally: cur.close(); conn.close()
        return redirect("/game")
    return render_template_string(MOBI_CSS+"""<div class="wrap" style="padding:20px"><h2 style="text-align:center">Регистрация</h2>
<form method="post"><div style="background:#f5e6c0;border:2px solid #5a3e22;padding:10px;margin:8px"><input name="name" placeholder="Имя героя" style="width:100%;border:0;background:transparent" required></div>
<div style="background:#f5e6c0;border:2px solid #5a3e22;padding:10px;margin:8px"><input name="login" placeholder="Логин" style="width:100%;border:0;background:transparent" required></div>
<div style="background:#f5e6c0;border:2px solid #5a3e22;padding:10px;margin:8px"><input name="password" type="password" placeholder="Пароль" style="width:100%;border:0;background:transparent" required></div>
<button class="btn-orange">Начать</button></form></div>""")

@app.route("/game")
def game():
    if "uid" not in session: return redirect("/")
    p=get_player(session["uid"])
    top=topbar_html(p)
    return render_template_string(GAME, topbar=top)

@app.route("/camp")
def camp():
    if "uid" not in session: return redirect("/")
    p=get_player(session["uid"])
    top=topbar_html(p)
    return render_template_string(MOBI_CSS+f"""<div class="wrap">{top}<div style="padding:10px">
<h3 style="text-align:center">Лагерь Воинов</h3>
<div class="frame"><div class="frame-inner" style="height:160px"><img src="/camp.jpg"></div></div>
<p style="padding:10px;background:#f5e6c0;border:2px solid #5a3e22">Твой боевой лагерь. Отдых тут. В сундуке меч.</p>
<a href="/school" class="btn-orange">⚔️ Тренировка с манекеном [бьет в ответ]</a>
<a href="/game" class="btn-orange" style="background:#d2b87e">← На карту</a></div></div>""")

@app.route("/school", methods=["GET","POST"])
def school():
    if "uid" not in session: return redirect("/")
    if "dummy_hp" not in session: session["dummy_hp"]=25
    if "my_hp" not in session: session["my_hp"]=20
    if "log" not in session: session["log"]="Бой!"
    if request.method=="POST":
        m=request.form.get("m")
        if m=="reset": session["dummy_hp"]=25; session["my_hp"]=20; session["log"]="Новый бой!"
        else:
            dmg=random.randint(3,6) if m!="3" else random.randint(3,7)+ (4 if random.random()<0.25 else 0)
            session["dummy_hp"]-=dmg; session["log"]=f"Ты бьешь {dmg}<br>"+session["log"]
            if session["dummy_hp"]<=0:
                rew=random.randint(2,5); sil=random.randint(5,10)
                conn=get_db(); cur=conn.cursor()
                if DATABASE_URL: cur.execute("UPDATE players SET gold=gold+%s, silver=silver+%s, exp=exp+5 WHERE id=%s",(rew,sil,session["uid"]))
                else: cur.execute("UPDATE players SET gold=gold+?, silver=silver+?, exp=exp+5 WHERE id=?",(rew,sil,session["uid"]))
                conn.commit(); cur.close(); conn.close()
                session["log"]=f"<b style='color:green'>Победа +{rew}🪙 +{sil}⚪ +5 exp</b><br>"+session["log"]
            else:
                ed=random.randint(2,4); session["my_hp"]-=ed; session["log"]=f"Манекен бьет {ed} в ответ<br>"+session["log"]
    p=get_player(session["uid"])
    top=topbar_html(p)
    return render_template_string(MOBI_CSS+f"""<div class="wrap">{top}<div style="padding:10px">
<div style="background:#fff8dc;border:1px dashed #5a3e22;padding:8px;height:120px;overflow:auto">{session["log"]}</div>
<form method="post" style="margin-top:10px">
<button name="m" value="1" class="btn-orange">🗡️ Колющий</button>
<button name="m" value="2" class="btn-orange" style="background:linear-gradient(#ffe082,#ff8c00)">⚔️ Режущий</button>
<button name="m" value="3" class="btn-orange" style="background:linear-gradient(#ffab91,#d32f2f)">🪓 Рубящий</button>
<button name="m" value="reset" class="btn-orange" style="background:#d2b87e">Новый манекен</button>
</form><a href="/camp" class="btn-orange" style="background:#bcaaa4">← В лагерь</a></div></div>""")

@app.route("/promysel")
def promysel():
    if "uid" not in session: return redirect("/")
    p=get_player(session["uid"]); top=topbar_html(p)
    return render_template_string(MOBI_CSS+f"""<div class="wrap">{top}<div style="padding:10px">
<h3 style="text-align:center">Промысел</h3>
<div class="frame"><div class="frame-inner" style="height:160px;background:#a5d6a7;display:flex;align-items:center;justify-content:center;font-size:60px">🌲🍄🌿</div></div>
<p style="padding:10px;background:#f5e6c0;border:2px solid #5a3e22">Ищешь травы в лесу. Находки дают серебро и золото.</p>
<form method="post" action="/promysel_go"><button class="btn-orange">🌿 Искать (момент)</button></form>
<a href="/game" class="btn-orange" style="background:#d2b87e">← На карту</a></div></div>""")

@app.route("/promysel_go", methods=["POST"])
def promysel_go():
    if "uid" not in session: return redirect("/")
    g=random.randint(1,3); s=random.randint(5,15); r=1 if random.random()<0.1 else 0
    conn=get_db(); cur=conn.cursor()
    if DATABASE_URL: cur.execute("UPDATE players SET gold=gold+%s, silver=silver+%s, rubin=rubin+%s WHERE id=%s",(g,s,r,session["uid"]))
    else: cur.execute("UPDATE players SET gold=gold+?, silver=silver+?, rubin=rubin+? WHERE id=?",(g,s,r,session["uid"]))
    conn.commit(); cur.close(); conn.close()
    p=get_player(session["uid"]); top=topbar_html(p)
    return render_template_string(MOBI_CSS+f"""<div class="wrap">{top}<div style="padding:20px;text-align:center">
<h3>Добыча!</h3><div style="font-size:50px">🌿</div>
<p>+{g} 🪙 +{s} ⚪ { '+1 💎' if r else ''}</p>
<a href="/promysel" class="btn-orange">Искать еще</a>
<a href="/game" class="btn-orange" style="background:#d2b87e">На карту</a></div></div>""")

@app.route("/quests")
def quests():
    p=get_player(session["uid"]); top=topbar_html(p)
    return render_template_string(MOBI_CSS+f"""<div class="wrap">{top}<div style="padding:20px"><h3>Задания</h3><p>Скоро</p><a href="/game" class="btn-orange">На карту</a></div></div>""")

@app.route("/hunt")
def hunt(): return redirect("/promysel")
@app.route("/logout")
def logout(): session.clear(); return redirect("/")
if __name__=="__main__": app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)))
