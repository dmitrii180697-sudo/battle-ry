import os, random
from flask import Flask, request, redirect, session, render_template_string, send_from_directory
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "battle2026_long_key_123")

# ФИКС ДЛЯ RENDER POSTGRES
DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

print(f"DB URL SET: {bool(DATABASE_URL)}")

def get_db():
    if DATABASE_URL:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        return conn
    else:
        import sqlite3
        conn = sqlite3.connect('/tmp/battle.db')
        conn.row_factory = sqlite3.Row
        return conn

def init_db():
    try:
        conn=get_db(); cur=conn.cursor()
        if DATABASE_URL:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS players (
                    id SERIAL PRIMARY KEY, 
                    name TEXT, 
                    login TEXT UNIQUE, 
                    password TEXT, 
                    gold INT DEFAULT 15, 
                    silver INT DEFAULT 50, 
                    rubin INT DEFAULT 0, 
                    exp INT DEFAULT 0, 
                    level INT DEFAULT 1, 
                    hp INT DEFAULT 20,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            # Добавляем колонки если их нет (для старых баз)
            cur.execute("ALTER TABLE players ADD COLUMN IF NOT EXISTS gold INT DEFAULT 15")
            cur.execute("ALTER TABLE players ADD COLUMN IF NOT EXISTS silver INT DEFAULT 50")
            cur.execute("ALTER TABLE players ADD COLUMN IF NOT EXISTS rubin INT DEFAULT 0")
        else:
            cur.execute("CREATE TABLE IF NOT EXISTS players (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, login TEXT UNIQUE, password TEXT, gold INT DEFAULT 15, silver INT DEFAULT 50, rubin INT DEFAULT 0, exp INT DEFAULT 0, level INT DEFAULT 1, hp INT DEFAULT 20)")
        conn.commit(); cur.close(); conn.close()
        print("DB INIT OK")
    except Exception as e:
        print(f"DB INIT ERROR: {e}")

init_db()

def get_player(uid):
    try:
        conn=get_db(); cur=conn.cursor()
        if DATABASE_URL: cur.execute("SELECT * FROM players WHERE id=%s",(uid,))
        else: cur.execute("SELECT * FROM players WHERE id=?",(uid,))
        p=cur.fetchone(); cur.close(); conn.close()
        return p
    except Exception as e:
        print(f"get_player error {e}")
        return None

def vals(p):
    if not p: return (1,20,0,15,50)
    try:
        if isinstance(p, dict) or hasattr(p,'get'):
            l = p.get("level",1); h = p.get("hp",20); r = p.get("rubin",0); g = p.get("gold",15); s = p.get("silver",50)
        else:
            l = p["level"]; h = p["hp"]; g = p["gold"]; s = p["silver"]; r = p["rubin"]
        return int(l), int(h), int(r), int(g), int(s)
    except: return (1,20,0,15,50)

def add_reward(uid, add_g, add_s, add_r):
    try:
        conn=get_db(); cur=conn.cursor()
        if DATABASE_URL:
            cur.execute("UPDATE players SET gold=COALESCE(gold,0)+%s, silver=COALESCE(silver,0)+%s, rubin=COALESCE(rubin,0)+%s WHERE id=%s RETURNING gold, silver, rubin",(add_g, add_s, add_r, uid))
            row=cur.fetchone()
            print(f"REWARD OK uid={uid} +{add_g}/{add_s}/{add_r} now={row}")
        else:
            cur.execute("UPDATE players SET gold=COALESCE(gold,0)+?, silver=COALESCE(silver,0)+?, rubin=COALESCE(rubin,0)+? WHERE id=?",(add_g, add_s, add_r, uid))
        conn.commit(); cur.close(); conn.close()
        return True
    except Exception as e:
        print(f"REWARD FAIL {e}")
        return False

CSS = "<style>body{margin:0;background:#2b2218;font-family:Arial}.wrap{max-width:480px;margin:0 auto;min-height:100vh;background:#e8d6a8;position:relative}.btn-orange{display:block;width:90%;margin:10px auto;background:linear-gradient(#ffb84d,#ff8c00);border:2px solid #5a3e22;border-radius:6px;padding:12px;text-align:center;font-weight:bold;font-size:18px;color:#3d2817;text-decoration:none}</style>"

@app.route("/camp.jpg")
def camp_img():
    try: return send_from_directory('.','camp.jpg')
    except: return redirect("https://i.imgur.com/8Km9tLL.jpg")

@app.route("/")
def root():
    if "uid" in session: return redirect("/game")
    html = CSS + '<div class="wrap" style="padding:20px"><h1 style="text-align:center">BATTLE OF WARRIORS</h1><form method="post" action="/login"><input name="login" placeholder="Login" style="width:100%;padding:12px;margin:6px 0" required><input name="password" type="password" placeholder="Pass" style="width:100%;padding:12px;margin:6px 0" required><button class="btn-orange">Войти</button></form><a href="/reg" style="display:block;text-align:center;margin-top:10px">Регистрация</a><p style="text-align:center;font-size:12px;color:#5a3e22;margin-top:20px">DB: '+('Postgres ✅ Сохранение вечное' if DATABASE_URL else 'SQLite ⚠️ Временное')+'</p></div>'
    return render_template_string(html)

@app.route("/login", methods=["POST"])
def login():
    lg=request.form.get("login","").strip(); pw=request.form.get("password","")
    conn=get_db(); cur=conn.cursor()
    try:
        if DATABASE_URL: cur.execute("SELECT * FROM players WHERE login=%s",(lg,))
        else: cur.execute("SELECT * FROM players WHERE login=?",(lg,))
        row=cur.fetchone()
    except: row=None
    cur.close(); conn.close()
    if row:
        hpw = row["password"] if isinstance(row, dict) or hasattr(row,'get') else row[3]
        uid = row["id"] if isinstance(row, dict) or hasattr(row,'get') else row[0]
        if check_password_hash(hpw, pw):
            session["uid"]=uid; session["my_hp"]=20; session["log"]="В лагере"
            return redirect("/game")
    return "Неверный пароль <a href='/'>назад</a>"

@app.route("/reg", methods=["GET","POST"])
def reg():
    if request.method=="POST":
        name=request.form.get("name","").strip(); lg=request.form.get("login","").strip(); pw=request.form.get("password","")
        try:
            conn=get_db(); cur=conn.cursor(); h=generate_password_hash(pw)
            if DATABASE_URL: cur.execute("INSERT INTO players (name,login,password,gold,silver,rubin) VALUES (%s,%s,%s,15,50,0) RETURNING id",(name,lg,h)); uid=cur.fetchone()["id"]
            else: cur.execute("INSERT INTO players (name,login,password,gold,silver,rubin) VALUES (?,?,?,15,50,0)",(name,lg,h)); uid=cur.lastrowid
            conn.commit(); cur.close(); conn.close()
            print(f"NEW PLAYER id={uid} login={lg} SAVED")
            session["uid"]=uid; session["my_hp"]=20; session["log"]="Привет!"
            return redirect("/game")
        except Exception as e: 
            print(f"REG ERROR {e}")
            return f"Логин занят {e} <a href='/reg'>назад</a>"
    html = CSS + '<div class="wrap" style="padding:20px"><h2>Регистрация</h2><form method="post"><input name="name" placeholder="Имя персонажа" style="width:100%;padding:10px;margin:5px 0" required><input name="login" placeholder="Логин" style="width:100%;padding:10px;margin:5px 0" required><input name="password" type="password" placeholder="Пароль" style="width:100%;padding:10px;margin:5px 0" required><button class="btn-orange">Создать</button></form></div>'
    return render_template_string(html)

@app.route("/game")
def game():
    if "uid" not in session: return redirect("/")
    p=get_player(session["uid"]); l,h,r,g,s = vals(p)
    top = f'<div style="background:#e8d6a8;padding:8px;display:flex;justify-content:center"><div style="background:#fdf6c8;border:2px solid #8a6a3d;border-radius:16px;padding:6px 14px;display:flex;gap:14px;font-weight:bold;font-size:15px"><span>⭐ {l}</span><span>❤️ {h}</span><span>💎 {r}</span><span>🪙 {g}</span><span>⚪ {s}</span></div></div>'
    body = f'<div class="wrap" style="background:#e8d6a8">{top}<div style="margin:8px;background:#3d2817;padding:6px;border-radius:4px"><div style="height:300px;overflow:hidden;border:2px solid #2b1a0e;background:#000"><img src="/camp.jpg" style="width:100%;height:100%;object-fit:cover;display:block"></div></div><div style="display:flex;gap:8px;padding:10px 10px 0 10px"><a href="/promysel" style="flex:1;background:linear-gradient(#ffb84d,#ff8c00);border:2px solid #5a3e22;border-radius:8px;padding:12px;text-align:center;font-weight:bold;color:#3d2817;text-decoration:none">🌲 Промысел</a><a href="/pvp" style="flex:1;background:linear-gradient(#ffb84d,#ff8c00);border:2px solid #5a3e22;border-radius:8px;padding:12px;text-align:center;font-weight:bold;color:#3d2817;text-decoration:none">⚔️ PVP</a></div><div style="padding:10px"><a href="/camp" style="display:block;background:linear-gradient(#ff8c00,#ff7b00);border:2px solid #5a3e22;border-radius:8px;padding:14px;text-align:center;font-weight:bold;font-size:18px;color:#3d2817;text-decoration:none">🏕️ Лагерь</a></div><div style="height:70px"></div></div>'
    return render_template_string(CSS+body)

@app.route("/camp")
def camp():
    if "uid" not in session: return redirect("/")
    p=get_player(session["uid"]); l,h,r,g,s = vals(p)
    top = f'<div style="background:#e8d6a8;padding:8px;display:flex;justify-content:center"><div style="background:#fdf6c8;border:2px solid #8a6a3d;border-radius:16px;padding:6px 14px;display:flex;gap:14px;font-weight:bold"><span>⭐ {l}</span><span>❤️ {h}</span><span>💎 {r}</span><span>🪙 {g}</span><span>⚪ {s}</span></div></div>'
    body = top + '<div class="wrap" style="background:#e8d6a8;padding:10px"><div style="margin:8px;background:#3d2817;padding:6px;border-radius:4px"><div style="height:300px;overflow:hidden;border:2px solid #2b1a0e"><img src="/camp.jpg" style="width:100%;height:100%;object-fit:cover"></div></div><div style="background:#f5e6c0;border:2px solid #5a3e22;border-radius:6px;padding:12px;text-align:center"><b>🏕️ Лагерь</b></div><a href="/game" class="btn-orange">← На карту</a></div>'
    return render_template_string(CSS+body)

@app.route("/promysel")
def promysel():
    if "uid" not in session: return redirect("/")
    p=get_player(session["uid"]); l,h,r,g,s = vals(p)
    top = f'<div style="background:#e8d6a8;padding:8px;display:flex;justify-content:center"><div style="background:#fdf6c8;border:2px solid #8a6a3d;border-radius:16px;padding:6px 14px;display:flex;gap:14px;font-weight:bold"><span>⭐ {l}</span><span>❤️ {h}</span><span>💎 {r}</span><span>🪙 {g}</span><span>⚪ {s}</span></div></div>'
    body = top + '<div class="wrap" style="background:#e8d6a8;padding:10px"><h3 style="text-align:center">🌲 Промысел</h3><div style="background:#3d2817;padding:6px;border-radius:6px;margin:10px 0"><div style="background:#f5e6c0;border:2px solid #5a3e22;border-radius:6px;padding:12px;display:flex;gap:12px;align-items:center"><div style="width:55px;height:55px;background:#2b1a0e;border-radius:4px;display:flex;align-items:center;justify-content:center;font-size:28px">⚔️</div><div style="flex:1"><b>Древний воин</b><br><small>Опасный противник</small></div><a href="/fight/warrior" style="background:linear-gradient(#ff6b6b,#c92a2a);border:2px solid #5a3e22;border-radius:6px;padding:8px 16px;color:white;font-weight:bold;text-decoration:none">Бить</a></div></div><div style="background:#3d2817;padding:6px;border-radius:6px;margin:10px 0"><div style="background:#f5e6c0;border:2px solid #5a3e22;border-radius:6px;padding:12px;display:flex;gap:12px;align-items:center"><div style="width:55px;height:55px;background:#1a2e1a;border-radius:4px;display:flex;align-items:center;justify-content:center;font-size:28px">🐺</div><div style="flex:1"><b>Дух зверя</b><br><small>Дикий и свирепый</small></div><a href="/fight/beast" style="background:linear-gradient(#ff6b6b,#c92a2a);border:2px solid #5a3e22;border-radius:6px;padding:8px 16px;color:white;font-weight:bold;text-decoration:none">Бить</a></div></div><a href="/game" class="btn-orange">← На карту</a></div>'
    return render_template_string(CSS+body)

@app.route("/fight/<monster>")
def fight(monster):
    if "uid" not in session: return redirect("/")
    if monster=="warrior": session["enemy_name"]="Древний воин"; session["enemy_hp"]=20; session["enemy_max"]=20; session["enemy_dmg"]=(2,4); session["reward_g"]=2; session["reward_s"]=10; session["reward_r"]=0
    else: session["enemy_name"]="Дух зверя"; session["enemy_hp"]=35; session["enemy_max"]=35; session["enemy_dmg"]=(4,7); session["reward_g"]=5; session["reward_s"]=20; session["reward_r"]=1
    session["my_hp"]=20; session["rewarded"]=False; session["log"]=f"Встретил {session['enemy_name']}!"
    return redirect("/fight_battle")

@app.route("/fight_battle", methods=["GET","POST"])
def fight_battle():
    if "uid" not in session: return redirect("/")
    if "enemy_hp" not in session: return redirect("/promysel")
    if request.method=="POST":
        m=request.form.get("m")
        if m=="hit" and session["my_hp"]>0 and session["enemy_hp"]>0:
            dmg=random.randint(3,7); session["enemy_hp"]-=dmg; session["log"]=f"Ты бьешь {dmg}<br>"+session["log"]
            if session["enemy_hp"]<=0:
                if not session.get("rewarded"):
                    ok=add_reward(session["uid"], session["reward_g"], session["reward_s"], session["reward_r"])
                    if ok: session["rewarded"]=True; session["log"]=f"<b style='color:green'>ПОБЕДА! +{session['reward_g']}🪙 +{session['reward_s']}⚪ +{session['reward_r']}💎</b><br>"+session["log"]
                    else: session["log"]="<b style='color:red'>Ошибка сохранения</b><br>"+session["log"]
            else:
                ed=random.randint(session["enemy_dmg"][0], session["enemy_dmg"][1]); session["my_hp"]-=ed; session["log"]=f"{session['enemy_name']} бьет {ed}<br>"+session["log"]
        elif m=="run": return redirect("/promysel")
    p=get_player(session["uid"]); l,h,r,g,s = vals(p)
    top = f'<div style="background:#e8d6a8;padding:8px;display:flex;justify-content:center"><div style="background:#fdf6c8;border:2px solid #8a6a3d;border-radius:16px;padding:6px 14px;display:flex;gap:14px;font-weight:bold"><span>⭐ {l}</span><span>❤️ {h}</span><span>💎 {r}</span><span>🪙 {g}</span><span>⚪ {s}</span></div></div>'
    enemy_hp=max(0,session["enemy_hp"]); enemy_max=session["enemy_max"]; my_hp=max(0,session["my_hp"]); perc=int(enemy_hp*100/enemy_max) if enemy_max else 0
    body = top + f'<div class="wrap" style="background:#e8d6a8;padding:10px"><h3 style="text-align:center">{session["enemy_name"]} - {enemy_hp}/{enemy_max}</h3><div style="background:#3d2817;height:18px;border-radius:10px;overflow:hidden"><div style="width:{perc}%;height:100%;background:red"></div></div><div style="text-align:center">Ты: {my_hp}/20</div><div style="background:#fff8dc;border:1px dashed #5a3e22;padding:8px;height:110px;overflow:auto;margin:10px 0">{session["log"]}</div>'
    if enemy_hp>0 and my_hp>0: body+='<form method="post" style="display:flex;gap:8px"><button name="m" value="hit" class="btn-orange" style="flex:1">🗡️ Ударить</button><button name="m" value="run" class="btn-orange" style="flex:1;background:#bcaaa4">Сбежать</button></form>'
    else: body+='<a href="/promysel" class="btn-orange">← К монстрам</a><a href="/game" class="btn-orange" style="background:#d2b87e">На карту</a>'
    body+='</div>'; return render_template_string(CSS+body)

@app.route("/pvp")
def pvp():
    if "uid" not in session: return redirect("/")
    p=get_player(session["uid"]); l,h,r,g,s = vals(p)
    top = f'<div style="background:#e8d6a8;padding:8px;display:flex;justify-content:center"><div style="background:#fdf6c8;border:2px solid #8a6a3d;border-radius:16px;padding:6px 14px;display:flex;gap:14px;font-weight:bold"><span>⭐ {l}</span><span>❤️ {h}</span><span>💎 {r}</span><span>🪙 {g}</span><span>⚪ {s}</span></div></div>'
    return render_template_string(CSS+top+'<div class="wrap" style="background:#e8d6a8;padding:15px;text-align:center"><h2>⚔️ PVP</h2><p>Скоро: турниры, бои за локации</p><a href="/game" class="btn-orange">← На карту</a></div>')

@app.route("/logout")
def logout(): session.clear(); return redirect("/")

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)))
