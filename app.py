import os, random
from flask import Flask, request, redirect, session, render_template_string, send_from_directory
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "battle2026_long_key_123")

DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# ===== ТВОИ МОНСТРЫ С КАРТИНКАМИ ИЗ STATIC =====
MONSTERS_CFG = {
    "warrior": {
        "name": "Древний воин",
        "img": "ancient_warrior.png",
        "hp": 20,
        "dmg": (2,4),
        "gold": 2, "silver": 10, "rubin": 0
    },
    "beast": {
        "name": "Дух зверя",
        "img": "spirit_wolf_left.png",
        "hp": 1000,
        "dmg": (4,7),
        "gold": 5, "silver": 20, "rubin": 1
    }
}
HERO_IMG = "barbarian_game_size.png" # твой варвар с дубинкой

def get_db():
    if DATABASE_URL:
        return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    else:
        import sqlite3
        conn = sqlite3.connect('/tmp/battle.db')
        conn.row_factory = sqlite3.Row
        return conn

def init_db():
    try:
        conn=get_db(); cur=conn.cursor()
        if DATABASE_URL:
            cur.execute("CREATE TABLE IF NOT EXISTS players (id SERIAL PRIMARY KEY, name TEXT, login TEXT UNIQUE, password TEXT, gold INT DEFAULT 15, silver INT DEFAULT 50, rubin INT DEFAULT 0, exp INT DEFAULT 0, level INT DEFAULT 1, hp INT DEFAULT 20, wins INT DEFAULT 1, losses INT DEFAULT 0)")
        else:
            cur.execute("CREATE TABLE IF NOT EXISTS players (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, login TEXT UNIQUE, password TEXT, gold INT DEFAULT 15, silver INT DEFAULT 50, rubin INT DEFAULT 0, exp INT DEFAULT 0, level INT DEFAULT 1, hp INT DEFAULT 20, wins INT DEFAULT 1, losses INT DEFAULT 0)")
        conn.commit(); cur.close(); conn.close()
    except Exception as e:
        print(f"DB INIT ERROR: {e}")
init_db()

def convert_silver(uid):
    try:
        conn=get_db(); cur=conn.cursor()
        if DATABASE_URL: cur.execute("SELECT silver, gold FROM players WHERE id=%s",(uid,))
        else: cur.execute("SELECT silver, gold FROM players WHERE id=?",(uid,))
        row=cur.fetchone()
        if not row: cur.close(); conn.close(); return
        s=row.get("silver",0) if isinstance(row, dict) or hasattr(row,'get') else row[0]
        g=row.get("gold",0) if isinstance(row, dict) or hasattr(row,'get') else row[1]
        s=int(s or 0); g=int(g or 0)
        if s >= 100:
            if DATABASE_URL: cur.execute("UPDATE players SET gold=%s, silver=%s WHERE id=%s",(g+s//100, s%100, uid))
            else: cur.execute("UPDATE players SET gold=?, silver=? WHERE id=?",(g+s//100, s%100, uid))
            conn.commit()
        cur.close(); conn.close()
    except: pass

def get_player(uid):
    try:
        convert_silver(uid)
        conn=get_db(); cur=conn.cursor()
        if DATABASE_URL: cur.execute("SELECT * FROM players WHERE id=%s",(uid,))
        else: cur.execute("SELECT * FROM players WHERE id=?",(uid,))
        p=cur.fetchone(); cur.close(); conn.close()
        return p
    except: return None

def vals(p):
    if not p: return (1,20,0,15,50)
    try:
        if isinstance(p, dict) or hasattr(p,'get'):
            return int(p.get("level",1)), int(p.get("hp",20)), int(p.get("rubin",0)), int(p.get("gold",15)), int(p.get("silver",50))
        else:
            return int(p["level"]), int(p["hp"]), int(p["rubin"]), int(p["gold"]), int(p["silver"])
    except: return (1,20,0,15,50)

def add_reward(uid, add_g, add_s, add_r):
    try:
        conn=get_db(); cur=conn.cursor()
        if DATABASE_URL: cur.execute("UPDATE players SET gold=COALESCE(gold,0)+%s, silver=COALESCE(silver,0)+%s, rubin=COALESCE(rubin,0)+%s WHERE id=%s",(add_g, add_s, add_r, uid))
        else: cur.execute("UPDATE players SET gold=COALESCE(gold,0)+?, silver=COALESCE(silver,0)+?, rubin=COALESCE(rubin,0)+? WHERE id=?",(add_g, add_s, add_r, uid))
        conn.commit(); cur.close(); conn.close()
        convert_silver(uid); return True
    except: return False

def add_win(uid):
    try:
        conn=get_db(); cur=conn.cursor()
        if DATABASE_URL: cur.execute("UPDATE players SET wins=COALESCE(wins,0)+1 WHERE id=%s",(uid,))
        else: cur.execute("UPDATE players SET wins=COALESCE(wins,0)+1 WHERE id=?",(uid,))
        conn.commit(); cur.close(); conn.close()
    except: pass

def add_loss(uid):
    try:
        conn=get_db(); cur=conn.cursor()
        if DATABASE_URL: cur.execute("UPDATE players SET losses=COALESCE(losses,0)+1 WHERE id=%s",(uid,))
        else: cur.execute("UPDATE players SET losses=COALESCE(losses,0)+1 WHERE id=?",(uid,))
        conn.commit(); cur.close(); conn.close()
    except: pass

BASE_CSS = """
<style>
body{margin:0;background:#2b2218;font-family:Arial}
.wrap{max-width:480px;margin:0 auto;min-height:100vh;background:#e8d6a8;position:relative;padding-bottom:80px}
.btn-orange{display:block;width:90%;margin:10px auto;background:linear-gradient(#ffb84d,#ff8c00);border:2px solid #5a3e22;border-radius:6px;padding:12px;text-align:center;font-weight:bold;font-size:18px;color:#3d2817;text-decoration:none}
.bottom-bar{position:fixed;bottom:0;left:50%;transform:translateX(-50%);width:100%;max-width:480px;background:#3d2817;display:flex;justify-content:space-between;padding:10px;border-top:2px solid #8a6a3d;box-sizing:border-box;z-index:999;gap:10px}
.bottom-bar a, .bottom-bar button{flex:1;background:linear-gradient(#ffb84d,#ff8c00);border:2px solid #5a3e22;border-radius:12px;padding:10px 0;font-weight:bold;color:#3d2817;text-decoration:none;text-align:center;font-size:15px;cursor:pointer}
.bottom-sheet-overlay{position:fixed;inset:0;background:rgba(0,0,0,0.5);z-index:1000;display:none}
.bottom-sheet{position:fixed;bottom:0;left:50%;transform:translateX(-50%) translateY(100%);width:92%;max-width:380px;background:#e8d6a8;border:3px solid #5a3e22;border-bottom:0;border-radius:18px 18px 0 0;z-index:1001;transition:transform 0.32s ease;padding:14px;box-sizing:border-box;box-shadow:0 -8px 25px rgba(0,0,0,0.4)}
.bottom-sheet.open{transform:translateX(-50%) translateY(0)}
@media(min-width:700px){ .bottom-sheet{width:40%} }
.sheet-handle{width:44px;height:5px;background:#8a6a3d;border-radius:3px;margin:0 auto 12px}
.sheet-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.sheet-item{background:#fdf6c8;border:2px solid #8a6a3d;border-radius:10px;padding:14px;text-align:center;color:#3d2817;text-decoration:none;font-weight:bold}
</style>
<script>
function toggleMenu(){document.getElementById('sheetOverlay').style.display='block';setTimeout(()=>document.getElementById('bottomSheet').classList.add('open'),10);}
function closeMenu(){document.getElementById('bottomSheet').classList.remove('open');setTimeout(()=>document.getElementById('sheetOverlay').style.display='none',320);}
</script>
"""

MENU_HTML = """
<div class="bottom-bar">
  <button onclick="toggleMenu()">☰ Меню</button>
  <a href="/logout">Выход</a>
</div>
<div class="bottom-sheet-overlay" id="sheetOverlay" onclick="closeMenu()"></div>
<div class="bottom-sheet" id="bottomSheet">
  <div class="sheet-handle"></div>
  <div class="sheet-grid">
    <a href="/shop" class="sheet-item">🛒 Магазин</a>
    <a href="/bank" class="sheet-item">🏦 Банк</a>
    <a href="/clan" class="sheet-item">🛡️ Клан</a>
    <a href="/alliance" class="sheet-item">🤝 Альянс</a>
    <a href="/top" class="sheet-item">🏆 Топ</a>
    <a href="/quests" class="sheet-item">📜 Задания</a>
    <a href="/online" class="sheet-item">🟢 Онлайн</a>
    <a href="/hero" class="sheet-item">👤 Персонаж</a>
  </div>
  <button onclick="closeMenu()" style="width:100%;margin-top:12px;padding:10px;background:#5a3e22;color:#e8d6a8;border:0;border-radius:8px;font-weight:bold">Закрыть</button>
</div>
"""

def render_page(inner_html, show_menu=True):
    menu = MENU_HTML if show_menu else ""
    return render_template_string(BASE_CSS + inner_html + menu)

# ==== СТАТИКА - ТЕПЕРЬ ИЗ ПАПКИ static ====
@app.route("/camp.jpg")
def camp_img():
    return send_from_directory('static','camp.jpg')

@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory('static', filename)

@app.route("/")
def root():
    if "uid" in session: return redirect("/game")
    html = f'<div class="wrap" style="padding:20px"><h1 style="text-align:center">BATTLE OF WARRIORS</h1><form method="post" action="/login"><input name="login" placeholder="Login" style="width:100%;padding:12px;margin:6px 0" required><input name="password" type="password" placeholder="Pass" style="width:100%;padding:12px;margin:6px 0" required><button class="btn-orange">Войти</button></form><a href="/reg" style="display:block;text-align:center;margin-top:10px">Регистрация</a><p style="text-align:center;font-size:12px;color:#5a3e22;margin-top:20px">DB: {"Postgres ✅" if DATABASE_URL else "SQLite ⚠️"}</p></div>'
    return render_template_string(BASE_CSS+html)

@app.route("/login", methods=["POST"])
def login():
    lg=request.form.get("login","").strip(); pw=request.form.get("password","")
    conn=get_db(); cur=conn.cursor()
    if DATABASE_URL: cur.execute("SELECT * FROM players WHERE login=%s",(lg,))
    else: cur.execute("SELECT * FROM players WHERE login=?",(lg,))
    row=cur.fetchone(); cur.close(); conn.close()
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
            session["uid"]=uid; session["my_hp"]=20; session["log"]="Привет!"
            return redirect("/game")
        except Exception as e: return f"Логин занят {e} <a href='/reg'>назад</a>"
    html = '<div class="wrap" style="padding:20px"><h2>Регистрация</h2><form method="post"><input name="name" placeholder="Имя" style="width:100%;padding:10px;margin:5px 0" required><input name="login" placeholder="Логин" style="width:100%;padding:10px;margin:5px 0" required><input name="password" type="password" placeholder="Пароль" style="width:100%;padding:10px;margin:5px 0" required><button class="btn-orange">Создать</button></form></div>'
    return render_template_string(BASE_CSS+html)

@app.route("/game")
def game():
    if "uid" not in session: return redirect("/")
    p=get_player(session["uid"]); l,h,r,g,s = vals(p)
    top = f'<div style="background:#e8d6a8;padding:8px;display:flex;justify-content:center"><div style="background:#fdf6c8;border:2px solid #8a6a3d;border-radius:16px;padding:6px 14px;display:flex;gap:14px;font-weight:bold"><span>⭐ {l}</span><span>❤️ {h}</span><span>💎 {r}</span><span>🪙 {g}</span><span>⚪ {s}</span></div></div>'
    body = f'<div class="wrap" style="background:#e8d6a8;min-height:100vh;display:flex;flex-direction:column">{top}<div style="margin:8px;background:#3d2817;padding:6px;border-radius:4px"><div style="height:300px;overflow:hidden;border:2px solid #2b1a0e"><img src="/static/camp.jpg" style="width:100%;height:100%;object-fit:cover"></div></div><div style="display:flex;gap:8px;padding:10px 10px 0 10px"><a href="/promysel" style="flex:1;background:linear-gradient(#ffb84d,#ff8c00);border:2px solid #5a3e22;border-radius:8px;padding:12px;text-align:center;font-weight:bold;color:#3d2817;text-decoration:none">🌲 Промысел</a><a href="/pvp" style="flex:1;background:linear-gradient(#ffb84d,#ff8c00);border:2px solid #5a3e22;border-radius:8px;padding:12px;text-align:center;font-weight:bold;color:#3d2817;text-decoration:none">⚔️ PVP</a></div><div style="padding:10px"><a href="/camp" style="display:block;background:linear-gradient(#ff8c00,#ff7b00);border:2px solid #5a3e22;border-radius:8px;padding:14px;text-align:center;font-weight:bold;font-size:18px;color:#3d2817;text-decoration:none">🏕️ Лагерь</a></div><div style="flex-grow:1"></div></div>'
    return render_page(body, True)

@app.route("/camp")
def camp():
    if "uid" not in session: return redirect("/")
    p=get_player(session["uid"]); l,h,r,g,s = vals(p)
    top = f'<div style="background:#e8d6a8;padding:8px;display:flex;justify-content:center"><div style="background:#fdf6c8;border:2px solid #8a6a3d;border-radius:16px;padding:6px 14px;display:flex;gap:14px;font-weight:bold"><span>⭐ {l}</span><span>❤️ {h}</span><span>💎 {r}</span><span>🪙 {g}</span><span>⚪ {s}</span></div></div>'
    return render_page(top + '<div class="wrap" style="background:#e8d6a8;padding:10px"><div style="margin:8px;background:#3d2817;padding:6px;border-radius:4px"><div style="height:300px;overflow:hidden;border:2px solid #2b1a0e"><img src="/static/camp.jpg" style="width:100%;height:100%;object-fit:cover"></div></div><a href="/game" class="btn-orange">← На карту</a></div>', True)

@app.route("/promysel")
def promysel():
    if "uid" not in session: return redirect("/")
    p=get_player(session["uid"]); l,h,r,g,s = vals(p)
    top = f'<div style="background:#e8d6a8;padding:8px;display:flex;justify-content:center"><div style="background:#fdf6c8;border:2px solid #8a6a3d;border-radius:16px;padding:6px 14px;display:flex;gap:14px;font-weight:bold"><span>⭐ {l}</span><span>❤️ {h}</span><span>💎 {r}</span><span>🪙 {g}</span><span>⚪ {s}</span></div></div>'
    body = top + f'''
    <div class="wrap" style="background:#e8d6a8;padding:10px">
    <h3 style="text-align:center">🌲 Промысел - ТВОИ МОНСТРЫ</h3>
    <div style="background:#3d2817;padding:6px;border-radius:6px;margin:10px 0">
      <div style="background:#f5e6c0;border:2px solid #5a3e22;border-radius:6px;padding:12px;display:flex;gap:12px;align-items:center">
        <img src="/static/{MONSTERS_CFG["warrior"]["img"]}" style="width:55px;height:55px;object-fit:contain;background:#2b1a0e;border-radius:4px">
        <div style="flex:1"><b>{MONSTERS_CFG["warrior"]["name"]}</b><br><small>{MONSTERS_CFG["warrior"]["gold"]}🪙 {MONSTERS_CFG["warrior"]["silver"]}⚪</small></div>
        <a href="/fight/warrior" style="background:linear-gradient(#ff6b6b,#c92a2a);border:2px solid #5a3e22;border-radius:6px;padding:8px 16px;color:white;font-weight:bold;text-decoration:none">Бить</a>
      </div>
    </div>
    <div style="background:#3d2817;padding:6px;border-radius:6px;margin:10px 0">
      <div style="background:#f5e6c0;border:2px solid #5a3e22;border-radius:6px;padding:12px;display:flex;gap:12px;align-items:center">
        <img src="/static/{MONSTERS_CFG["beast"]["img"]}" style="width:55px;height:55px;object-fit:contain;background:#1a2e1a;border-radius:4px">
        <div style="flex:1"><b>{MONSTERS_CFG["beast"]["name"]}</b><br><small>{MONSTERS_CFG["beast"]["gold"]}🪙 {MONSTERS_CFG["beast"]["silver"]}⚪ {MONSTERS_CFG["beast"]["rubin"]}💎</small></div>
        <a href="/fight/beast" style="background:linear-gradient(#ff6b6b,#c92a2a);border:2px solid #5a3e22;border-radius:6px;padding:8px 16px;color:white;font-weight:bold;text-decoration:none">Бить</a>
      </div>
    </div>
    <a href="/game" class="btn-orange">← На карту</a></div>'''
    return render_page(body, True)

@app.route("/fight/<monster>")
def fight(monster):
    if "uid" not in session: return redirect("/")
    cfg = MONSTERS_CFG.get(monster, MONSTERS_CFG["warrior"])
    session["enemy_name"]=cfg["name"]
    session["enemy_img"]=cfg["img"]
    session["enemy_hp"]=cfg["hp"]
    session["enemy_max"]=cfg["hp"]
    session["enemy_dmg"]=cfg["dmg"]
    session["reward_g"]=cfg["gold"]
    session["reward_s"]=cfg["silver"]
    session["reward_r"]=cfg["rubin"]
    session["my_hp"]=20
    session["rewarded"]=False
    session["hit_count"]=0        
    session["super_used"]=False
    session["log"]=f"Встретил {cfg['name']}!"
    return redirect("/fight_battle")

@app.route("/fight_battle", methods=["GET","POST"])
def fight_battle():
    if "uid" not in session:
        return redirect("/")
    if "enemy_hp" not in session:
        return redirect("/promysel")
    # счетчики боя
    if "hit_count" not in session:
        session["hit_count"]=0
    if "super_used" not in session:
        session["super_used"]=False

    if request.method=="POST":
        m=request.form.get("m")
        if m=="hit" and session["my_hp"]>0 and session["enemy_hp"]>0:
            dmg=random.randint(3,7)
            session["enemy_hp"]-=dmg
            session["hit_count"]+=1
            session["last_dmg"]=dmg
            session["last_hit"]="my"
            session["is_super"]=False
            if session["enemy_hp"]<=0:
                if not session.get("rewarded"):
                    add_reward(session["uid"], session["reward_g"], session["reward_s"], session["reward_r"])
                    session["rewarded"]=True
                    add_win(session["uid"])
            else:
                ed=random.randint(session["enemy_dmg"][0], session["enemy_dmg"][1])
                session["my_hp"]-=ed
                session["last_edmg"]=ed
                if session["my_hp"]<=0 and not session.get("rewarded"):
                    add_loss(session["uid"])
                    session["rewarded"]=True
        elif m=="super" and session["my_hp"]>0 and session["enemy_hp"]>0 and not session.get("super_used") and session.get("hit_count",0)>=5:
            dmg=random.randint(3,7)*5
            session["enemy_hp"]-=dmg
            session["super_used"]=True
            session["last_dmg"]=dmg
            session["last_hit"]="my"
            session["is_super"]=True
            if session["enemy_hp"]<=0:
                if not session.get("rewarded"):
                    add_reward(session["uid"], session["reward_g"], session["reward_s"], session["reward_r"])
                    session["rewarded"]=True
                    add_win(session["uid"])
            else:
                ed=random.randint(session["enemy_dmg"][0], session["enemy_dmg"][1])
                session["my_hp"]-=ed
                session["last_edmg"]=ed
                if session["my_hp"]<=0 and not session.get("rewarded"):
                    add_loss(session["uid"])
                    session["rewarded"]=True
        elif m=="run":
            return redirect("/promysel")

    eh=max(0, session["enemy_hp"])
    mh=max(0, session["my_hp"])
    ehp=int(eh*100/session["enemy_max"]) if session["enemy_max"] else 0
    mhp=int(mh*100/20) if mh else 0
    enemy_img = session.get("enemy_img","ancient_warrior.png")
    
    if eh<=0 or mh<=0:
        is_win=eh<=0
        title="ПОБЕДА!" if is_win else "ПОРАЖЕНИЕ!"
        color="#00ff66" if is_win else "#ff3333"
        reward=f"+{session['reward_g']} 🪙 +{session['reward_s']} ⚪ +{session['reward_r']} 💎" if is_win else "Ты пал..."
        html=f"""
        <div class="wrap" style="background:#1a0e0a;padding:12px;min-height:100vh;display:flex;align-items:center;justify-content:center">
            <div style="background:#f5e6c0;border:3px solid #5a3e22;border-radius:16px;padding:20px;text-align:center;width:100%;max-width:320px">
                <div style="font-size:42px">{"🏆" if is_win else "💀"}</div>
                <div style="font-size:28px;font-weight:900;color:{color}">{title}</div>
                <div style="margin:12px 0">{reward}</div>
                <a href="/promysel" style="display:block;background:linear-gradient(#ffb84d,#ff8c00);border:2px solid #5a3e22;border-radius:10px;padding:14px;font-weight:bold;text-decoration:none;color:#000">В ПРОМЫСЕЛ</a>
            </div>
        </div>"""
        return render_page(html, False)

    hit_count=session.get("hit_count",0)
    super_used=session.get("super_used",False)
    super_ready=hit_count>=5 and not super_used
    # прогресс до суперудара
    super_text = f"СУПЕР УДАР x5 (ГОТОВ!)" if super_ready else f"СУПЕР УДАР ({hit_count}/5)"
    
    html=f"""
    <div class="wrap" style="background:#1a0e0a;padding:12px;min-height:100vh;">
        <div style="background:#f5e6c0;border:2px solid #5a3e22;border-radius:14px;padding:10px;margin-bottom:10px">
            <div style="display:flex;justify-content:space-between;font-weight:bold;font-size:13px"><span>{session['enemy_name']}</span><span>{eh}/{session['enemy_max']}</span></div>
            <div style="background:#300;height:12px;border-radius:6px"><div style="width:{ehp}%;height:100%;background:linear-gradient(#ff4d4d,#b30000);border-radius:6px;transition:width 0.5s"></div></div>
        </div>
        <div style="display:flex;justify-content:space-between;align-items:end;background:radial-gradient(#3a2412,#1a0e0a);border:2px solid #5a3e22;border-radius:12px;padding:10px;margin-bottom:12px;height:280px;position:relative;overflow:hidden">
            <img id="hero-img" src="/static/barbarian_game_size.png" style="height:240px;object-fit:contain;filter:drop-shadow(0 0 10px black)">
            <div style="position:relative">
                <img id="enemy-img" src="/static/{enemy_img}" style="height:240px;object-fit:contain;;filter:drop-shadow(0 0 10px black)">
                <div id="dmg-float-enemy" class="dmg">-5</div>
            </div>
        </div>
        <div style="background:#f5e6c0;border:2px solid #5a3e22;border-radius:14px;padding:10px;margin-bottom:12px">
            <div style="display:flex;justify-content:space-between;font-weight:bold;font-size:13px"><span>Ты</span><span>{mh}/20</span></div>
            <div style="background:#300;height:14px;border-radius:7px"><div style="width:{mhp}%;height:100%;background:linear-gradient(#4dff4d,#00b300);border-radius:7px;transition:width 0.5s"></div></div>
        </div>
        <form id="hit-form" method="post" style="display:flex;flex-direction:column;gap:8px">
            <input type="hidden" id="action-input" name="m" value="hit">
            <button type="button" onclick="doHit(false)" style="width:100%;background:linear-gradient(#ffb84d,#ff8c00);border:2px solid #5a3e22;border-radius:10px;padding:16px;font-weight:900;font-size:16px">🪓 УДАР ДУБИНОЙ [{hit_count}]</button>
            <button type="button" id="super-btn" onclick="doHit(true)" {"disabled" if not super_ready else ""} style="width:100%;background:{'linear-gradient(#ff4444,#ffcc00)' if super_ready else '#888'};border:2px solid #5a3e22;border-radius:10px;padding:16px;font-weight:900;font-size:16px;opacity:{'1' if super_ready else '0.5'};color:#000">🔥 {super_text}</button>
        </form>
    </div>
    <script>const lastDmg={session.get('last_dmg',5)}; const isSuper={str(session.get('is_super',False)).lower()};</script>
    <script src="/static/game.js"></script>
    """
    return render_page(html, False)

    # === ЭКРАН БОЯ - БЕЗ ЛОГА И БЕЗ МЕНЮ ===
    html=f"""
    <div class="wrap" style="background:#1a0e0a;padding:12px;min-height:100vh;">
        <div style="background:#f5e6c0;border:2px solid #5a3e22;border-radius:14px;padding:10px;margin-bottom:10px">
            <div style="display:flex;justify-content:space-between;font-weight:bold;font-size:13px;margin-bottom:4px"><span>{session['enemy_name']}</span><span>{eh}/{session['enemy_max']}</span></div>
            <div style="background:#300;height:12px;border-radius:6px;overflow:hidden"><div style="width:{ehp}%;height:100%;background:linear-gradient(#ff4d4d,#b30000);border-radius:6px;transition: width 0.5s"></div></div>
        </div>
        
        <div style="display:flex;justify-content:space-between;align-items:end;background:radial-gradient(#3a2412,#1a0e0a);border:2px solid #5a3e22;border-radius:12px;padding:10px;margin-bottom:12px;height:280px;position:relative;overflow:hidden">
            <img id="hero-img" src="/static/barbarian_game_size.png" style="height:240px;object-fit:contain;filter:drop-shadow(0 0 10px black);transition:0.12s">
            <div style="position:relative">
                <img id="enemy-img" src="/static/{enemy_img}" style="height:240px;object-fit:contain;transform:scaleX(-1);filter:drop-shadow(0 0 10px black)">
                <div id="dmg-float-enemy" class="dmg">-5</div>
                <div id="dmg-float-hero" class="dmg" style="left:-60px;color:#4dff4d">-3</div>
            </div>
        </div>

        <div style="background:#f5e6c0;border:2px solid #5a3e22;border-radius:14px;padding:10px;margin-bottom:14px">
            <div style="display:flex;justify-content:space-between;font-weight:bold;font-size:13px;margin-bottom:4px"><span>Ты</span><span>{mh}/20</span></div>
            <div style="background:#300;height:14px;border-radius:7px;overflow:hidden"><div style="width:{mhp}%;height:100%;background:linear-gradient(#4dff4d,#00b300);border-radius:7px;transition: width 0.5s"></div></div>
        </div>
        
        <form id="hit-form" method="post" style="display:flex;gap:8px">
            <input type="hidden" name="m" value="hit">
            <button type="button" onclick="doHit()" style="flex:1;background:linear-gradient(#ffb84d,#ff8c00);border:2px solid #5a3e22;border-radius:10px;padding:16px;font-weight:900;font-size:16px;box-shadow:0 3px 0 #5a3e22">🗡️ УДАР ДУБИНОЙ</button>
            <button name="m" value="run" formnovalidate formaction="/promysel" style="background:#ccc;border:2px solid #5a3e22;border-radius:10px;padding:16px;font-weight:bold">🏃</button>
        </form>
    </div>
    <script>
    const lastDmg = {session.get('last_dmg', 5)};
    const lastEdmg = {session.get('last_edmg', 3)};
    const lastHit = '{session.get('last_hit','')}';
    </script>
    <script src="/static/game.js"></script>
    """
    return render_page(html, False)

@app.route("/pvp")
def pvp():
    if "uid" not in session: return redirect("/")
    return render_page('<div class="wrap" style="padding:20px;text-align:center"><h2>⚔️ PVP скоро</h2><a href="/game" class="btn-orange">← На карту</a></div>', True)

@app.route("/shop")
def shop(): return render_page('<div class="wrap" style="padding:20px"><h2>🛒 Магазин скоро</h2><a href="/game" class="btn-orange">← На карту</a></div>', True)
@app.route("/bank")
def bank(): return render_page('<div class="wrap" style="padding:20px"><h2>🏦 Банк скоро</h2><a href="/game" class="btn-orange">← На карту</a></div>', True)
@app.route("/clan")
def clan(): return render_page('<div class="wrap" style="padding:20px"><h2>🛡️ Клан скоро</h2><a href="/game" class="btn-orange">← На карту</a></div>', True)
@app.route("/alliance")
def alliance(): return render_page('<div class="wrap" style="padding:20px"><h2>🤝 Альянс скоро</h2><a href="/game" class="btn-orange">← На карту</a></div>', True)
@app.route("/top")
def top_r(): return render_page('<div class="wrap" style="padding:20px"><h2>🏆 Топ скоро</h2><a href="/game" class="btn-orange">← На карту</a></div>', True)
@app.route("/quests")
def quests(): return render_page('<div class="wrap" style="padding:20px"><h2>📜 Задания скоро</h2><a href="/game" class="btn-orange">← На карту</a></div>', True)
@app.route("/online")
def online(): return render_page('<div class="wrap" style="padding:20px"><h2>🟢 Онлайн скоро</h2><a href="/game" class="btn-orange">← На карту</a></div>', True)
@app.route("/hero")
def hero_page():
    if "uid" not in session: return redirect("/")
    p=get_player(session["uid"]); l,h,r,g,s = vals(p)
    try:
        nick = p.get("name","") if isinstance(p, dict) or hasattr(p,'get') else ""
        if nick.lower() == "admin":
            session["is_admin"] = True
    except: pass
    lvl = max(1, 1)
    try:
        wins = int(p.get("wins",1) if isinstance(p, dict) or hasattr(p,'get') else 1)
        losses = int(p.get("losses",0) if isinstance(p, dict) or hasattr(p,'get') else 0)
    except: wins, losses = 1, 0
    exp = int(p.get("exp",0) if isinstance(p, dict) or hasattr(p,'get') else 0)
    exp_need = 100 * lvl
    add = lvl - 1
    life = 15 + add * 10
    sila = 2 + add
    metkost = 9 + add
    zashita = 0 + add
    lovkost = 4 + add
    shield = 0 + add
    admin_block = ""
    if session.get("is_admin"):
        admin_block = '<div style="background:#ff0000;border:2px solid gold;border-radius:10px;padding:12px;text-align:center;margin:10px"><a href="/admin" style="color:white;font-weight:bold;text-decoration:none;font-size:18px">👑 АДМИНКА</a></div>'
    html = f"""
    <div class="wrap" style="background:#2b1a0e;min-height:100vh;padding:0">
        {admin_block}
        <div style="background:#e8d6a8;padding:8px;display:flex;justify-content:center">
            <div style="background:#fdf6c8;border:2px solid #8a6a3d;border-radius:16px;padding:6px 14px;display:flex;gap:14px;font-weight:bold">
                <span>⭐ {lvl}</span><span>❤️ {h}</span><span>💎 {r}</span><span>🪙 {g}</span><span>⚪ {s}</span>
            </div>
        </div>
        <div style="padding:12px;background:#3b2314;min-height:calc(100vh - 50px)">
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px">
                <div style="background:#f5e6c0;border:2px solid #5a3e22;border-radius:14px;padding:12px 10px;font-weight:bold;color:#3d2817;">🌟 ОПЫТ {exp}/{exp_need}</div>
                <div style="background:#f5e6c0;border:2px solid #5a3e22;border-battradius:14px;padding:12px 10px;font-weight:bold;color:#3d2817;">🏆 СЛАВА 0/100</div>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;align-items:start">
                <div style="display:flex;flex-direction:column;gap:12px">
                    <div style="background:#f5e6c0;border:2px solid #5a3e22;border-radius:14px;padding:18px 14px;font-weight:bold;color:#3d2817;">🏅 ПОБЕДЫ ИГРОКОВ 0</div>
                    <div style="background:#f5e6c0;border:2px solid #5a3e22;border-radius:14px;padding:18px 14px;font-weight:bold;color:#3d2817;font-size:18px;line-height:1.1;">⚔️ ПОБЕДЫ / ПОРАЖЕНИЯ<br><span style="font-size:24px">{wins}/{losses}</span></div>
                    <img src="/static/{HERO_IMG}" style="width:100%;background:#2b1a0e;border-radius:12px;padding:10px;box-sizing:border-box">
                </div>
                <div style="display:flex;flex-direction:column;gap:8px">
                    <div style="background:#f5e6c0;border:2px solid #5a3e22;border-radius:10px;padding:10px 12px;font-weight:bold;color:#3d2817;">❤️ ЖИЗНЬ {life}</div>
                    <div style="background:#f5e6c0;border:2px solid #5a3e22;border-radius:10px;padding:10px 12px;font-weight:bold;color:#3d2817;">🗡️ СИЛА {sila}</div>
                    <div style="background:#f5e6c0;border:2px solid #5a3e22;border-radius:10px;padding:10px 12px;font-weight:bold;color:#3d2817;">🎯 МЕТКОСТЬ {metkost}</div>
                    <div style="background:#f5e6c0;border:2px solid #5a3e22;border-radius:10px;padding:10px 12px;font-weight:bold;color:#3d2817;">🛡️ ЗАЩИТА {zashita}</div>
                    <div style="background:#f5e6c0;border:2px solid #5a3e22;border-radius:10px;padding:10px 12px;font-weight:bold;color:#3d2817;">➡️ ЛОВКОСТЬ {lovkost}</div>
                    <div style="background:#f5e6c0;border:2px solid #5a3e22;border-radius:10px;padding:10px 12px;font-weight:bold;color:#3d2817;">🛡️ ПРОЧНОСТЬ ЩИТА {shield}</div>
                </div>
            </div>
            <a href="/game" style="display:block;margin-top:20px;background:linear-gradient(#ffb84d,#ff8c00);border:2px solid #5a3e22;border-radius:8px;padding:12px;text-align:center;font-weight:bold;color:#3d2817;text-decoration:none">← На карту</a>
        </div>
    </div>
    """
    return render_page(html, True)

@app.route("/logout")
def logout(): session.clear(); return redirect("/")

ADMIN_PASSWORD = "admin123"

def is_admin():
    if session.get("is_admin"):
        return True
    if "uid" not in session:
        return False
    try:
        p = get_player(session["uid"])
        if not p: return False
        nick = p.get("name","") if isinstance(p, dict) or hasattr(p,'get') else ""
        if nick.lower() == "admin":
            return session.get("is_admin", False)
    except: pass
    return False

@app.route("/admin/login", methods=["GET","POST"])
def admin_login():
    if "uid" not in session:
        return redirect("/")
    if request.method == "POST":
        pwd = request.form.get("pwd","")
        if pwd == ADMIN_PASSWORD:
            session["is_admin"] = True
            return redirect("/admin")
        else:
            return render_page('<div style="background:#1a0e0a;padding:20px;min-height:100vh;color:#f5e6c0"><h3>❌ Неверный пароль</h3><a href="/admin/login" style="color:#ffb84d">Назад</a></div>', True)
    html = """
    <div class="wrap" style="background:#1a0e0a;padding:20px;min-height:100vh;color:#f5e6c0">
        <h2 style="text-align:center">🔐 Админ вход</h2>
        <form method="post" style="background:#f5e6c0;padding:16px;border-radius:12px;max-width:320px;margin:0 auto">
            <input type="password" name="pwd" placeholder="Пароль админа" style="width:100%;padding:12px;border-radius:8px;border:2px solid #5a3e22;margin-bottom:10px">
            <button style="width:100%;background:linear-gradient(#ffb84d,#ff8c00);border:2px solid #5a3e22;border-radius:8px;padding:12px;font-weight:bold">Войти</button>
        </form>
        <a href="/game" style="display:block;text-align:center;margin-top:14px;color:#f5e6c0">← На карту</a>
    </div>
    """
    return render_page(html, True)

@app.route("/admin/logout")
def admin_logout():
    session.pop("is_admin", None)
    return redirect("/game")

@app.route("/admin")
def admin_page():
    if not is_admin():
        return redirect("/admin/login")
    html = """
    <div class="wrap" style="background:#1a0e0a;padding:12px;min-height:100vh;color:#f5e6c0">
        <h2 style="text-align:center">👑 АДМИН МЕНЮ</h2>
        <div style="display:grid;gap:10px">
            <a href="/admin/players" style="background:#f5e6c0;color:#3d2817;padding:14px;border-radius:10px;text-align:center;font-weight:bold;text-decoration:none">👥 Игроки</a>
            <a href="/admin/logout" style="background:#600;color:#fff;padding:14px;border-radius:10px;text-align:center;font-weight:bold;text-decoration:none">🚪 Выйти из админки</a>
            <a href="/game" style="background:#666;color:#fff;padding:14px;border-radius:10px;text-align:center;font-weight:bold;text-decoration:none">← На карту</a>
        </div>
    </div>
    """
    return render_page(html, True)

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)))
