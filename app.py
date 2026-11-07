import os, random
from flask import Flask, request, send_from_directory, session, redirect, jsonify, render_template, render_template_string
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "battle2026_long_key_123")

DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

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
HERO_IMG = "barbarian_game_size.png"

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
        rg = session.get("reward_g", 0)
        rs = session.get("reward_s", 0)
        rr = session.get("reward_r", 0)
        conn=get_db(); cur=conn.cursor()
        if DATABASE_URL:
            cur.execute("UPDATE players SET wins=COALESCE(wins,0)+1, gold=COALESCE(gold,0)+%s, silver=COALESCE(silver,0)+%s, rubin=COALESCE(rubin,0)+%s, exp=COALESCE(exp,0)+10 WHERE id=%s",(rg, rs, rr, uid))
            cur.execute("UPDATE players SET level=level+1, exp=0 WHERE id=%s AND exp >= level*100", (uid,))
        else:
            cur.execute("UPDATE players SET wins=COALESCE(wins,0)+1, gold=COALESCE(gold,0)+?, silver=COALESCE(silver,0)+?, rubin=COALESCE(rubin,0)+?, exp=COALESCE(exp,0)+10 WHERE id=?",(rg, rs, rr, uid))
            cur.execute("UPDATE players SET level=level+1, exp=0 WHERE id=? AND exp >= level*100", (uid,))
        conn.commit(); cur.close(); conn.close()
        convert_silver(uid)
    except Exception as e:
        print(f"add_win error {e}")

def add_loss(uid):
    try:
        conn=get_db(); cur=conn.cursor()
        if DATABASE_URL: cur.execute("UPDATE players SET losses=COALESCE(losses,0)+1 WHERE id=%s",(uid,))
        else: cur.execute("UPDATE players SET losses=COALESCE(losses,0)+1 WHERE id=?",(uid,))
        conn.commit(); cur.close(); conn.close()
    except: pass

BASE_CSS = """
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover">
<style>
*{box-sizing:border-box}
html,body{width:100%;overflow-x:hidden}
body{margin:0;background:#2b2218;font-family:Arial;-webkit-text-size-adjust:100%}
.wrap{width:100%;max-width:480px;margin:0 auto;min-height:100dvh;background:#e8d6...;padding-bottom:90px}
.btn-orange{display:block;width:90%;margin:10px auto;background:linear-gradient(#ffb84d,#ff8c00);border:2px solid #5a3e22;border-radius:6px;padding:12px;text-align:center;font-weight:bold;font-size:18px;color:#3d2817;text-decoration:none;cursor:pointer}
.bottom-bar{position:fixed;bottom:0;left:50%;transform:translateX(-50%);width:100%;max-width:480px;display:flex;gap:6px;padding:8px;padding-bottom:calc(8px + env(safe-area-inset-bottom));z-index:99}
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

MAP_HTML = """
<div style="max-width:480px;margin:0 auto;padding:10px;min-height:100vh;background:url('/static/lager.jpg') center/cover">
<div style="background:rgba(8,30,55,.92);border:2px solid #4a7ba6;padding:12px;display:flex;gap:10px;align-items:center"><a href="/game" style="color:#fff;text-decoration:none;font-size:24px">←</a><b style="font-size:22px;color:#fff">📍 КАРТА МИРА</b></div>
<p style="color:#fff;margin:12px 2px">Выбери куда отправиться. Фон главного экрана поменяется.</p>
<a href="/loc/lager" style="display:flex;gap:12px;background:rgba(8,30,55,.92);border:2px solid #e8c268;padding:12px;margin-bottom:12px;text-decoration:none;color:#fff;align-items:center"><img src="/static/lager.jpg" style="width:90px;height:90px;object-fit:cover"><div><h3 style="color:#f5d98a">🏕️ Лагерь</h3><p style="font-size:13px">Твой дом. Уровень 1+</p></div></a>
<a href="/loc/zastava" style="display:flex;gap:12px;background:rgba(8,30,55,.92);border:2px solid #4a7ba6;padding:12px;margin-bottom:12px;text-decoration:none;color:#fff;align-items:center"><img src="/static/zastava.jpg" style="width:90px;height:90px;object-fit:cover"><div><h3 style="color:#f5d98a">🛡️ Застава</h3><p style="font-size:13px">Пограничный пост. Уровень 3+</p></div></a>
<a href="/loc/oboz" style="display:flex;gap:12px;background:rgba(8,30,55,.92);border:2px solid #4a7ba6;padding:12px;margin-bottom:12px;text-decoration:none;color:#fff;align-items:center"><img src="/static/oboz.jpg" style="width:90px;height:90px;object-fit:cover"><div><h3 style="color:#f5d98a">🛒 Обоз / Ярмарка</h3><p style="font-size:13px">Торговцы, магазин и банк.</p></div></a>
<a href="/game" style="display:block;background:#0a2642;color:#fff;text-align:center;padding:14px;text-decoration:none;font-weight:bold;margin-top:20px">← ВЕРНУТЬСЯ В ИГРУ</a>
</div>
"""

@app.route("/map")
def map_page():
    if "uid" not in session: return redirect("/")
    return render_page(MAP_HTML, True)

@app.route("/loc/<code>")
def go_loc(code):
    if "uid" not in session: return redirect("/")
    alias = {"kremnev":"lager", "gati":"zastava", "yarmarka":"oboz"}
    real = alias.get(code, code)
    session["current_loc"] = real
    return redirect(f"/game?loc={real}")

@app.route("/game")
def game():
    if "uid" not in session: return redirect("/")
    p=get_player(session["uid"]); l,h,r,g,s = vals(p)
    try: exp = int(p.get("exp",0)) if isinstance(p, dict) or hasattr(p,'get') else 0
    except: exp = 0
    try: nick = p.get("name","") if isinstance(p, dict) or hasattr(p,'get') else "Воин"
    except: nick = "Воин"
    current = request.args.get("loc") or session.get("current_loc") or "lager"
    bg_map = {"lager":"/static/lager.jpg", "zastava":"/static/zastava.jpg", "oboz":"/static/oboz.jpg", "camp":"/static/camp.jpg"}
    bg = bg_map.get(current, "/static/lager.jpg")
    exp_per = min(100, exp % 100)

    html = f'''
    <div style="max-width:480px;margin:0 auto;min-height:100vh;background:url({bg}) center/cover no-repeat;display:flex;flex-direction:column;padding:10px;box-sizing:border-box">
      <div style="background:rgba(8,30,55,.88);border:2px solid #4a7ba6;padding:10px;display:flex;justify-content:space-around;font-weight:900;color:#fff;font-size:20px">
        <span>💎 {r} +</span><span>🪙 {s} +</span><span>🟡 {g} +</span>
      </div>
      <div style="margin-top:8px;background:rgba(8,30,55,.88);border:2px solid #4a7ba6;padding:8px 12px;display:flex;align-items:center;gap:10px;color:#fff">
        <div style="background:linear-gradient(#e8c268,#9a741f);width:42px;height:48px;display:flex;align-items:center;justify-content:center;font-weight:900;font-size:22px;clip-path:polygon(50% 0,100% 20%,100% 80%,50% 100%,0 80%,0 20%)">{l}</div>
        <div style="flex:1"><div style="font-weight:800">{nick} &nbsp;•&nbsp; {exp}/{100}</div><div style="height:8px;background:#0a1a2a;border-radius:10px;margin-top:4px;overflow:hidden"><div style="width:{exp_per}%;height:100%;background:#7ab8ff"></div></div></div>
        <a href="/hero" style="font-size:26px;text-decoration:none">⚙️</a>
      </div>

      <div style="flex:1;display:flex;justify-content:space-between;align-items:center;gap:8px;margin:14px 0">
        <div style="display:flex;flex-direction:column;gap:10px;width:104px">
          <a href="/top" style="background:rgba(10,38,66,.92);border:2px solid #4a7ba6;color:#fff;text-decoration:none;text-align:center;padding:12px 4px;font-weight:800">🏆<br>Топ игроков</a>
          <a href="/clan" style="background:rgba(10,38,66,.92);border:2px solid #4a7ba6;color:#fff;text-decoration:none;text-align:center;padding:12px 4px;font-weight:800">👥<br>Клан</a>
          <a href="/alliance" style="background:rgba(10,38,66,.92);border:2px solid #4a7ba6;color:#fff;text-decoration:none;text-align:center;padding:12px 4px;font-weight:800">🛡️<br>Альянс</a>
          <a href="/shop" style="background:rgba(10,38,66,.92);border:2px solid #4a7ba6;color:#fff;text-decoration:none;text-align:center;padding:12px 4px;font-weight:800">💎<br>Премиум</a>
          <a href="/bank" style="background:rgba(10,38,66,.92);border:2px solid #4a7ba6;color:#fff;text-decoration:none;text-align:center;padding:12px 4px;font-weight:800">🏛️<br>Банк</a>
        </div>
        <div style="flex:1;text-align:center">
          <a href="/promysel" style="text-decoration:none;color:#fff"><div style="background:rgba(8,30,55,.92);border:2px solid #4a7ba6;padding:14px 8px;display:inline-block;min-width:180px"><b style="color:#f5d98a;font-size:20px"></b><br><small id="locName">Лагерь</small><script>var p=new URLSearchParams(location.search);var cur=p.get("loc")||"zastava";var el=document.getElementById("locName");if(el)if(cur=="oboz")el.textContent="Обоз";else el.textContent="Лагерь";</script><div style="height:8px;background:#0a1a2a;margin-top:8px;border-radius:10px"><div style="height:100%;background:#f5d98a;width:0%"></div></div></div></a>
        </div>
        <div style="display:flex;flex-direction:column;gap:10px;width:104px">
          <a href="/online" style="background:rgba(10,38,66,.92);border:2px solid #4a7ba6;color:#fff;text-decoration:none;text-align:center;padding:12px 4px;font-weight:800">✉️<br>Почта</a>
          <a href="/quests" style="background:rgba(10,38,66,.92);border:2px solid #4a7ba6;color:#fff;text-decoration:none;text-align:center;padding:12px 4px;font-weight:800">📰<br>Новости</a>
          <a href="/online" style="background:rgba(10,38,66,.92);border:2px solid #4a7ba6;color:#fff;text-decoration:none;text-align:center;padding:12px 4px;font-weight:800">👥<br>Онлайн</a>
          <a href="/logout" style="background:rgba(10,38,66,.92);border:2px solid #4a7ba6;color:#fff;text-decoration:none;text-align:center;padding:12px 4px;font-weight:800">🚪<br>Выход</a>
        </div>
      </div>

      <div style="display:flex;gap:10px;margin-bottom:10px">
        <a href="/shop" style="flex:1;background:rgba(10,38,66,.92);border:2px solid #4a7ba6;color:#fff;text-decoration:none;text-align:center;padding:14px;font-weight:800;font-size:18px">🛒 Магазин</a>
        <a href="/hero" style="flex:1;background:rgba(10,38,66,.92);border:2px solid #4a7ba6;color:#fff;text-decoration:none;text-align:center;padding:14px;font-weight:800;font-size:18px">👤 Персонаж</a>
      </div>
      <div style="display:flex;gap:10px;align-items:stretch">
        <a href="/promysel" style="flex:1;background:rgba(10,38,66,.92);border:2px solid #4a7ba6;color:#fff;text-decoration:none;text-align:center;padding:14px;font-weight:800">⛏️<br>Промысел</a>
        <a href="/map" style="flex:2.2;background:linear-gradient(#1a3a5a,#0a1e35);border:2px solid #e8c268;color:#f5e6b0;text-decoration:none;text-align:center;padding:16px;font-weight:900;font-size:28px">📍 КАРТА</a>
        <a href="/pvp" style="flex:1;background:rgba(10,38,66,.92);border:2px solid #4a7ba6;color:#fff;text-decoration:none;text-align:center;padding:14px;font-weight:800">⚔️<br>PVP</a>
      </div>
    </div>
    '''
    return render_page(html, False)

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
    if "uid" not in session:
        return redirect("/")
    p = get_player(session["uid"])
    l,h,r,g,s_ = vals(p)
    cfg = MONSTERS_CFG.get(monster, MONSTERS_CFG["warrior"])
    session["enemy_type"] = monster
    session["enemy_hp"] = cfg.get("hp", 20)
    session["enemy_max"] = cfg.get("hp", 20)
    session["enemy_dmg"] = cfg.get("dmg", (2,4))
    session["enemy_img"] = cfg.get("img", "ancient_warrior.png")
    session["my_hp"] = h
    session["hit_count"] = 0
    session["rewarded"] = False
    session["reward_g"] = cfg.get("gold", 2)
    session["reward_s"] = cfg.get("silver", 10)
    session["reward_r"] = cfg.get("rubin", 0)
    session.modified = True
    return redirect("/fight_battle")

@app.route("/fight_battle", methods=["GET", "POST"])
def fight_battle():
    if "uid" not in session:
        return redirect("/")
    if "enemy_hp" not in session:
        return redirect("/promysel")

    p = get_player(session["uid"])
    lvl, my_max_hp, rubin, gold, silver = vals(p)

    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        m = data.get("m") or request.form.get("m", "hit")
        if m == "run":
            return jsonify({"status": "redirect", "url": "/promysel"})
        cur_my = session.get("my_hp", my_max_hp)
        cur_en = session.get("enemy_hp", 20)
        hit_cnt = session.get("hit_count", 0)
        dmg = 0
        edmg = 0
        if m == "hit" and cur_my > 0 and cur_en > 0:
            dmg = random.randint(3, 7)
            cur_en = max(0, cur_en - dmg)
            hit_cnt += 1
        elif m == "super" and hit_cnt >= 5:
            dmg = random.randint(10, 18)
            cur_en = max(0, cur_en - dmg)
            hit_cnt = 0
        if cur_en > 0 and m in ["hit", "super"]:
            emin, emax = session.get("enemy_dmg", [2,5])
            edmg = random.randint(emin, emax)
            cur_my = max(0, cur_my - edmg)

        session["enemy_hp"] = cur_en
        session["my_hp"] = cur_my
        session["hit_count"] = hit_cnt
        session.modified = True

        finished = False
        is_win = False
        if cur_en <= 0 and not session.get("rewarded"):
            add_win(session["uid"])
            session["rewarded"] = True
            finished = True
            is_win = True
        if cur_my <= 0 and not session.get("rewarded"):
            add_loss(session["uid"])
            session["rewarded"] = True
            finished = True
            is_win = False

        return jsonify({
            "enemy_hp": cur_en,
            "enemy_max": session.get("enemy_max", 20),
            "my_hp": cur_my,
            "my_max": my_max_hp,
            "hit_cnt": hit_cnt,
            "last_dmg": dmg,
            "edmg": edmg,
            "finished": finished,
            "is_win": is_win,
            "reward_g": session.get("reward_g", 0),
            "reward_s": session.get("reward_s", 0),
            "reward_r": session.get("reward_r", 0),
        })

    cur_enemy_hp = session.get("enemy_hp", 20)
    enemy_max_hp = session.get("enemy_max", 20)
    cur_my_hp = session.get("my_hp", my_max_hp)
    hit_cnt = session.get("hit_count", 0)
    enemy_name = session.get("enemy_type", "Древний Воин")
    enemy_map = {"warrior": "ancient_warrior.png", "ancient_warrior": "ancient_warrior.png", "wolf": "spirit_wolf_left.png"}
    raw = session.get("enemy_img", session.get("enemy_type", "warrior"))
    enemy_img = enemy_map.get(raw, "ancient_warrior.png")
    
    my_per = int(cur_my_hp * 100 / my_max_hp) if my_max_hp else 0
    enemy_per = int(cur_enemy_hp * 100 / enemy_max_hp) if enemy_max_hp else 0

    html = f'''
    <style>
    body {{ background: #1a0e0a; margin: 0; font-family: Arial; }}
    .fight-wrap {{ max-width: 420px; margin: 0 auto; padding: 10px; }}
    @keyframes attackLeft {{ 0%{{transform:translateX(0)}} 35%{{transform:translateX(40px)}} 100%{{transform:translateX(0)}} }}
    @keyframes shakeRight {{ 0%,100%{{transform:translateX(0)}} 20%{{transform:translateX(-7px)}} 40%{{transform:translateX(7px)}} }}
    .anim-attack {{ animation: attackLeft 0.32s ease; }} .anim-shake {{ animation: shakeRight 0.32s ease; }}
    .potions-bar {{ display: grid; grid-template-columns: repeat(10, 1fr); gap: 3px; background: #2b1a0e; padding: 6px; border: 2px solid #5a3e22; border-radius: 8px; margin-top: 10px; }}
    .potion-slot {{ background: linear-gradient(#4a3525, #2b1a0e); border: 1px solid #8a6a3d; border-radius: 4px; height: 36px; display: flex; align-items: center; justify-content: center; color: #ffb84d; font-weight: bold; font-size: 10px; cursor: pointer; }}
    .frame-end {{ border:3px solid gold; background: linear-gradient(#2b1a0e,#1a0e0a); padding:20px; border-radius:16px; margin-top:15px; display:none; text-align:center; color:#fff; box-shadow:0 0 20px gold; }}
    </style>
    <div class="fight-wrap" id="fightWrap">
<div id="log" style="text-align:center;color:#ffeb00;font-weight:bold;min-height:20px"></div>
      <div style="background:rgba(245,230,200,0.95);border:2px solid #8b5a2b;border-radius:10px;padding:5px 10px;margin-bottom:6px">
        <div style="display:flex;justify-content:space-between;font-weight:900"><span>{enemy_name}</span><span><span id="enHp">{cur_enemy_hp}</span>/{enemy_max_hp}</span></div>
        <div style="height:8px;background:#3a2a1a;border-radius:4px;overflow:hidden"><div id="enBar" style="width:{enemy_per}%;height:100%;background:#ff3b30;transition:width 0.3s"></div></div>
      </div>
      <div style="background:url(/static/camp.jpg) center/cover no-repeat;border-radius:16px;border:3px solid #c89b5e;height:260px;display:flex;align-items:flex-end;justify-content:space-between;padding:10px">
        <div style="flex:1;text-align:center"><img id="heroImg" src="/static/barbarian_game_size.png" style="height:160px;filter:drop-shadow(0 4px 12px black);"></div>
        <div style="flex:1;text-align:center"><img id="enemyImg" src="/static/{enemy_img}" style="height:160px;filter:drop-shadow(0 4px 12px black);"></div>
      </div>
      <div style="background:rgba(245,230,200,0.95);border:2px solid #8b5a2b;border-radius:10px;padding:5px 10px;margin:8px 0">
        <div style="display:flex;justify-content:space-between;font-weight:900"><span>ТЫ</span><span><span id="myHp">{cur_my_hp}</span>/{my_max_hp}</span></div>
        <div style="height:10px;background:#3a2a1a;border-radius:4px;overflow:hidden"><div id="myBar" style="width:{my_per}%;height:100%;background:#2ecc40;transition:width 0.3s"></div></div>
      </div>
      <div style="display:flex;gap:8px">
        <button type="button" onclick="makeAction('hit')" style="flex:1;background:#2b1a0e;border:3px solid #ff8c00;border-radius:12px;padding:8px;color:#ffb84d;font-weight:900">⚔️ УДАР (<span id="hitCnt">{hit_cnt}</span>)</button>
        <button type="button" onclick="makeAction('super')" id="superBtn" style="flex:1;background:#2b1a0e;border:3px solid #ffcc00;border-radius:12px;padding:8px;color:#ff0;font-weight:900">⚡ СУПЕР</button>
        <button type="button" onclick="makeAction('run')" style="background:#3a2a1a;border:2px solid #777;border-radius:10px;color:#ccc;padding:6px 12px;font-weight:900">БЕГ</button>
      </div>
      <div class="potions-bar">
        <div class="potion-slot">🍷1</div><div class="potion-slot">🧪2</div><div class="potion-slot">📜3</div><div class="potion-slot">🛡️4</div><div class="potion-slot">⚡5</div><div class="potion-slot">🔮6</div><div class="potion-slot">❤️7</div><div class="potion-slot">⭐8</div><div class="potion-slot">🟢9</div><div class="potion-slot">🔵10</div>
      </div>
      </div> <div id="endOverlay" style="position:fixed;inset:0;background:rgba(0,0,0,0.88);backdrop-filter:blur(8px);display:none;align-items:center;justify-content:center;z-index:9999;padding:20px">
  <div style="background:linear-gradient(#3a2510,#1a0e0a);border:3px solid #ffcc00;border-radius:22px;padding:26px;width:100%;max-width:320px;text-align:center;box-shadow:0 0 60px gold">
    <h2 id="endTitle" style="margin:0;color:gold;font-size:28px"></h2>
    <div id="trophyBox" style="background:rgba(255,215,0,0.12);border:1.5px solid #c9a45c;border-radius:14px;padding:14px;margin:14px 0;font-size:16px;line-height:2;color:#ffe9a3"></div>
    <a href="/promysel" style="display:block;background:linear-gradient(#ffcc00,#c9a45c);color:#000;padding:14px;border-radius:12px;font-weight:900;text-decoration:none">На промысел ➔</a>
  </div>
</div>
    </div>
    <script>
    async function makeAction(type) {{
       const overlay = document.getElementById('endOverlay');
if(overlay && overlay.style.display=='flex') return;
        const hero = document.getElementById('heroImg');
        const enemy = document.getElementById('enemyImg');
        if(type === 'hit' || type === 'super') {{
            hero.classList.remove('anim-attack'); void hero.offsetWidth; hero.classList.add('anim-attack');
            enemy.classList.remove('anim-shake'); void enemy.offsetWidth; enemy.classList.add('anim-shake');
        }}
        let r = await fetch('/fight_battle', {{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{m:type}})}});
        let data = await r.json();
        if(data.status === 'redirect') {{ location.href=data.url; return; }}
        document.getElementById('enHp').innerText = data.enemy_hp;
        document.getElementById('enBar').style.width = (data.enemy_hp * 100 / data.enemy_max) + '%';
        document.getElementById('myHp').innerText = data.my_hp;
        document.getElementById('myBar').style.width = (data.my_hp * 100 / data.my_max) + '%';
        document.getElementById('hitCnt').innerText = data.hit_cnt;
        document.getElementById('log').innerText = data.last_dmg ? Ты ${{data.last_dmg}} / Враг ${{data.edmg}} : '';
        if(data.finished){{
          document.getElementById('fightWrap').style.opacity='0.15';
          document.getElementById('fightWrap').style.pointerEvents='none';
          document.getElementById('endOverlay').style.display='flex';
          document.getElementById('endTitle').innerText=data.is_win?'🏆 ПОБЕДА!':'💀 ПОРАЖЕНИЕ';
          let box=document.getElementById('trophyBox');
          if(data.is_win){{
            box.innerHTML=ТРОФЕИ С МОНСТРА<br><br>💰 Золото: <b>+${{data.reward_g}}</b><br>⚪ Серебро: <b>+${{data.reward_s}}</b><br>⭐ Опыт: <b>+10</b>;
        }}else{{
          box.innerHTML=Ты пал в бою...<br>Попробуй снова, воин!;
    }}
}}
    </script>
    '''
    return render_page(html, True)

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
                <div style="background:#f5e6c0;border:2px solid #5a3e22;border-radius:14px;padding:12px 10px;font-weight:bold;color:#3d2817;">🏆 СЛАВА 0/100</div>
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

if game=="main_":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)))