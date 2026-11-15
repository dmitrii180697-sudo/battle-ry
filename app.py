import os, random, json
from flask import Flask, request, send_from_directory, session, redirect, jsonify, render_template_string
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
XP_TABLE = [0, 0, 100, 300, 700, 1400, 2600, 4600, 7900, 13300, 22100, 36400, 59600, 97200, 158100, 256700, 416300, 674600, 1092600, 1769000, 2863500, 4634500]
MAX_LVL = 21
ADMIN_LOGIN = "admin"

def get_lvl_by_xp(xp):
    lvl = 1
    for i in range(1, MAX_LVL + 1):
        if xp >= XP_TABLE[i]: lvl = i
        else: break
    return lvl

app.secret_key = os.environ.get("SECRET_KEY", "battle2026_long_key_123")
DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

DEFAULT_MONSTERS = {
    "warrior": {"name": "Древний воин", "img": "ancient_warrior.png", "hp": 20, "dmg": [2,4], "gold": 2, "silver": 10, "rubin": 0},
    "beast": {"name": "Дух зверя", "img": "spirit_wolf_left.png", "hp": 100, "dmg": [4,7], "gold": 5, "silver": 20, "rubin": 1}
}

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
        conn = get_db(); cur = conn.cursor()
        if DATABASE_URL:
            cur.execute("CREATE TABLE IF NOT EXISTS players (id SERIAL PRIMARY KEY, name TEXT, login TEXT UNIQUE, password TEXT, gold INT DEFAULT 15, silver INT DEFAULT 50, rubin INT DEFAULT 0, exp INT DEFAULT 0, level INT DEFAULT 1, hp INT DEFAULT 20, wins INT DEFAULT 1, losses INT DEFAULT 0)")
            cur.execute("CREATE TABLE IF NOT EXISTS monster_cfg (key TEXT PRIMARY KEY, data TEXT)")
        else:
            cur.execute("CREATE TABLE IF NOT EXISTS players (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, login TEXT UNIQUE, password TEXT, gold INT DEFAULT 15, silver INT DEFAULT 50, rubin INT DEFAULT 0, exp INT DEFAULT 0, level INT DEFAULT 1, hp INTEGER DEFAULT 20, wins INT DEFAULT 1, losses INT DEFAULT 0)")
            cur.execute("CREATE TABLE IF NOT EXISTS monster_cfg (key TEXT PRIMARY KEY, data TEXT)")
        conn.commit()
        for k,v in DEFAULT_MONSTERS.items():
            if DATABASE_URL: cur.execute("SELECT * FROM monster_cfg WHERE key=%s",(k,))
            else: cur.execute("SELECT * FROM monster_cfg WHERE key=?",(k,))
            if not cur.fetchone():
                if DATABASE_URL: cur.execute("INSERT INTO monster_cfg (key,data) VALUES (%s,%s)",(k,json.dumps(v)))
                else: cur.execute("INSERT INTO monster_cfg (key,data) VALUES (?,?)",(k,json.dumps(v)))
        conn.commit(); cur.close(); conn.close()
    except Exception as e: print(f"DB INIT ERROR: {e}")
init_db()

def get_monsters():
    try:
        conn=get_db(); cur=conn.cursor()
        if DATABASE_URL: cur.execute("SELECT * FROM monster_cfg")
        else: cur.execute("SELECT * FROM monster_cfg")
        rows=cur.fetchall(); cur.close(); conn.close()
        out={}
        for r in rows:
            k = r["key"] if isinstance(r,dict) else r[0]
            d = r["data"] if isinstance(r,dict) else r[1]
            out[k]=json.loads(d)
        if not out: return DEFAULT_MONSTERS
        return out
    except: return DEFAULT_MONSTERS

def save_monster(key, data):
    conn=get_db(); cur=conn.cursor()
    if DATABASE_URL: cur.execute("UPDATE monster_cfg SET data=%s WHERE key=%s",(json.dumps(data),key))
    else: cur.execute("UPDATE monster_cfg SET data=? WHERE key=?",(json.dumps(data),key))
    conn.commit(); cur.close(); conn.close()

def convert_silver(uid):
    try:
        conn = get_db(); cur = conn.cursor()
        if DATABASE_URL: cur.execute("SELECT silver, gold FROM players WHERE id=%s",(uid,))
        else: cur.execute("SELECT silver, gold FROM players WHERE id=?",(uid,))
        row = cur.fetchone()
        if not row: cur.close(); conn.close(); return
        s = row["silver"] if isinstance(row, dict) or hasattr(row,'get') else row[0]
        g = row["gold"] if isinstance(row, dict) or hasattr(row,'get') else row[1]
        s, g = int(s or 0), int(g or 0)
        if s >= 100:
            if DATABASE_URL: cur.execute("UPDATE players SET gold=%s, silver=%s WHERE id=%s",(g+s//100, s%100, uid))
            else: cur.execute("UPDATE players SET gold=?, silver=? WHERE id=?",(g+s//100, s%100, uid))
            conn.commit()
        cur.close(); conn.close()
    except: pass

def get_player(uid):
    try:
        convert_silver(uid)
        conn = get_db(); cur = conn.cursor()
        if DATABASE_URL: cur.execute("SELECT * FROM players WHERE id=%s",(uid,))
        else: cur.execute("SELECT * FROM players WHERE id=?",(uid,))
        p = cur.fetchone(); cur.close(); conn.close(); return p
    except: return None

def is_admin():
    if "uid" not in session: return False
    p = get_player(session["uid"])
    if not p: return False
    lg = p.get("login") if isinstance(p,dict) else p[2]
    return lg == ADMIN_LOGIN

def vals(p):
    if not p: return (1, 20, 0, 15, 50)
    try:
        if isinstance(p, dict) or hasattr(p,'get'):
            return int(p.get("level",1)), int(p.get("hp",20)), int(p.get("rubin",0)), int(p.get("gold",15)), int(p.get("silver",50))
        else:
            return int(p["level"]), int(p["hp"]), int(p["rubin"]), int(p["gold"]), int(p["silver"])
    except: return (1, 20, 0, 15, 50)

def add_win(uid):
    try:
        rg = session.get("reward_g", 0); rs = session.get("reward_s", 0); rr = session.get("reward_r", 0)
        conn = get_db(); cur = conn.cursor()
        if DATABASE_URL:
            cur.execute("UPDATE players SET wins=COALESCE(wins,0)+1, gold=COALESCE(gold,0)+%s, silver=COALESCE(silver,0)+%s, rubin=COALESCE(rubin,0)+%s, exp=COALESCE(exp,0)+10 WHERE id=%s",(rg, rs, rr, uid))
        else:
            cur.execute("UPDATE players SET wins=COALESCE(wins,0)+1, gold=COALESCE(gold,0)+?, silver=COALESCE(silver,0)+?, rubin=COALESCE(rubin,0)+?, exp=COALESCE(exp,0)+10 WHERE id=?",(rg, rs, rr, uid))
        conn.commit()
        if DATABASE_URL: cur.execute("SELECT exp FROM players WHERE id=%s",(uid,))
        else: cur.execute("SELECT exp FROM players WHERE id=?",(uid,))
        row = cur.fetchone()
        exp_now = int(row["exp"] if isinstance(row,dict) else row[0] or 0)
        new_lvl = get_lvl_by_xp(exp_now)
        if new_lvl > MAX_LVL: new_lvl = MAX_LVL
        if DATABASE_URL: cur.execute("UPDATE players SET level=%s WHERE id=%s",(new_lvl, uid))
        else: cur.execute("UPDATE players SET level=? WHERE id=?",(new_lvl, uid))
        conn.commit(); cur.close(); conn.close(); convert_silver(uid)
    except Exception as e: print(f"add_win error {e}")

def add_loss(uid):
    try:
        conn = get_db(); cur = conn.cursor()
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
.wrap{width:100%;max-width:480px;margin:0 auto;min-height:100dvh;background:#e8d6a8;padding-bottom:90px}
.btn-orange{display:block;width:90%;margin:10px auto;background:linear-gradient(#ffb84d,#ff8c00);border:2px solid #5a3e22;border-radius:6px;padding:12px;text-align:center;font-weight:bold;font-size:18px;color:#3d2817;text-decoration:none;cursor:pointer}
input,select{width:100%;padding:10px;margin:5px 0;border:2px solid #8a6a3d;border-radius:8px;background:#fdf6c8}
.player-card{display:flex;gap:12px;align-items:center;background:#fdf6c8;border:2px solid #8a6a3d;border-radius:12px;padding:10px;margin:8px 0;color:#3d2817;text-decoration:none}
.player-card img{width:52px;height:52px;object-fit:cover;border-radius:50%;border:2px solid #c9a45c;background:#fff}
.bottom-sheet-overlay{position:fixed;inset:0;background:rgba(0,0,0,0.5);z-index:1000;display:none}
.bottom-sheet{position:fixed;bottom:0;left:50%;transform:translateX(-50%) translateY(100%);width:92%;max-width:380px;background:#e8d6a8;border:3px solid #5a3e22;border-bottom:0;border-radius:18px 18px 0 0;z-index:1001;transition:transform 0.32s ease;padding:14px;box-sizing:border-box;box-shadow:0 -8px 25px rgba(0,0,0,0.4)}
.bottom-sheet.open{transform:translateX(-50%) translateY(0)}
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

@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory('static', filename)

@app.route("/")
def root():
    if "uid" in session: return redirect("/game")
    html = f'<div class="wrap" style="padding:20px"><h1 style="text-align:center">BATTLE OF WARRIORS</h1><form method="post" action="/login"><input name="login" placeholder="Login" style="width:100%;padding:12px;margin:6px 0" required><input name="password" type="password" placeholder="Pass" style="width:100%;padding:12px;margin:6px 0" required><button class="btn-orange">Войти</button></form><a href="/reg" style="display:block;text-align:center;margin-top:10px">Регистрация</a><p style="text-align:center;font-size:12px;color:#666">Админ: логин admin</p></div>'
    return render_template_string(BASE_CSS+html)

@app.route("/login", methods=["POST"])
def login():
    lg = request.form.get("login","").strip(); pw = request.form.get("password","")
    conn = get_db(); cur = conn.cursor()
    if DATABASE_URL: cur.execute("SELECT * FROM players WHERE login=%s",(lg,))
    else: cur.execute("SELECT * FROM players WHERE login=?",(lg,))
    row = cur.fetchone(); cur.close(); conn.close()
    if row:
        hpw = row["password"] if isinstance(row, dict) or hasattr(row,'get') else row[3]
        uid = row["id"] if isinstance(row, dict) or hasattr(row,'get') else row[0]
        if check_password_hash(hpw, pw):
            session["uid"] = uid; session["my_hp"] = 20; session["current_loc"] = "lager"
            return redirect("/game")
    return "Неверный пароль <a href='/'>назад</a>"

@app.route("/reg", methods=["GET","POST"])
def reg():
    if request.method == "POST":
        name = request.form.get("name","").strip(); lg = request.form.get("login","").strip(); pw = request.form.get("password","")
        try:
            conn = get_db(); cur = conn.cursor(); h = generate_password_hash(pw)
            if DATABASE_URL:
                cur.execute("INSERT INTO players (name,login,password,gold,silver,rubin) VALUES (%s,%s,%s,15,50,0) RETURNING id",(name,lg,h)); uid = cur.fetchone()["id"]
            else:
                cur.execute("INSERT INTO players (name,login,password,gold,silver,rubin) VALUES (?,?,?,15,50,0)",(name,lg,h)); uid = cur.lastrowid
            conn.commit(); cur.close(); conn.close()
            session["uid"] = uid; session["my_hp"] = 20; session["current_loc"] = "lager"
            return redirect("/game")
        except Exception as e: return f"Логин занят {e} <a href='/reg'>назад</a>"
    html = '<div class="wrap" style="padding:20px"><h2>Регистрация</h2><form method="post"><input name="name" placeholder="Имя" style="width:100%;padding:10px;margin:5px 0" required><input name="login" placeholder="Логин" style="width:100%;padding:10px;margin:5px 0" required><input name="password" type="password" placeholder="Пароль" style="width:100%;padding:10px;margin:5px 0" required><button class="btn-orange">Создать</button></form></div>'
    return render_template_string(BASE_CSS+html)

MAP_HTML = """
<div style="max-width:480px;margin:0 auto;padding:10px;min-height:100vh;background:#1a0e0a;color:#fff">
<div style="background:rgba(8,30,55,.92);border:2px solid #4a7ba6;padding:12px;text-align:center"><h3 style="color:#fff;margin:0">📍 КАРТА МИРА</h3></div><br>
<a href="/loc/lager" style="display:block;background:rgba(8,30,55,.92);border:2px solid #f0c040;padding:16px;color:#fff;text-decoration:none;font-size:20px;font-weight:bold;border-radius:8px;margin-bottom:10px">🏕️ Лагерь</a>
<a href="/loc/zastava" style="display:block;background:rgba(8,30,55,.92);border:2px solid #3aa0ff;padding:16px;color:#fff;text-decoration:none;font-size:20px;font-weight:bold;border-radius:8px;margin-bottom:10px">🛡️ Застава</a>
<a href="/loc/oboz" style="display:block;background:rgba(8,30,55,.92);border:2px solid #3aa0ff;padding:16px;color:#fff;text-decoration:none;font-size:20px;font-weight:bold;border-radius:8px;margin-bottom:10px">🛒 Обоз</a>
<a href="/game" style="display:block;background:#5a3e22;color:#fff;text-align:center;padding:14px;text-decoration:none;font-weight:bold;border-radius:8px">← Вернуться в игру</a></div>
"""
@app.route("/map")
def map_page():
    if "uid" not in session: return redirect("/")
    return render_page(MAP_HTML, True)

@app.route("/loc/<code>")
def go_loc(code):
    if "uid" not in session: return redirect("/")
    session["current_loc"] = code
    if code == "promysel": return redirect("/promysel")
    return redirect(f"/game?loc={code}")

@app.route("/game")
def game():
    if "uid" not in session: return redirect("/")
    p = get_player(session["uid"]); l, h, r, g, s = vals(p)
    exp = int(p.get("exp",0)) if isinstance(p, dict) or hasattr(p,'get') else 0
    nick = p.get("name","Воин") if isinstance(p, dict) or hasattr(p,'get') else "Воин"
    current = request.args.get("loc") or session.get("current_loc") or "lager"
    session["current_loc"] = current
    bg_map = {"lager": "/static/camp.jpg", "zastava": "/static/camp.jpg", "oboz": "/static/camp.jpg"}
    bg = bg_map.get(current, "/static/camp.jpg")
    loc_names = {"lager": "🏕️ Лагерь", "zastava": "🛡️ Застава", "oboz": "🛒 Обоз"}
    loc_title = loc_names.get(current, "🏕️ Лагерь")
    if l >= MAX_LVL:
        lvl_exp = XP_TABLE[MAX_LVL]; exp_per = 100
    else:
        lvl_exp = XP_TABLE[l+1]
        exp_per = int((exp - XP_TABLE[l]) * 100 / max(1, (XP_TABLE[l+1] - XP_TABLE[l])))
        exp_per = max(0, min(100, exp_per))
    admin_btn = '<a href="/admin" style="display:block;background:linear-gradient(#ff0000,#8b0000);color:#fff;text-align:center;padding:12px;text-decoration:none;font-weight:900;border-radius:8px;margin:8px 0;border:2px solid gold">👑 АДМИН ПАНЕЛЬ</a>' if is_admin() else ""
    html = f'''
    <div style="max-width:480px;margin:0 auto;min-height:100vh;background:url('{bg}') center/cover no-repeat;display:flex;flex-direction:column;padding:10px;box-sizing:border-box">
      <div style="background:rgba(8,30,55,.9);border:2px solid #4a7ba6;padding:8px;text-align:center;color:#fff;font-weight:900;font-size:22px;border-radius:8px">BATTLE</div>
      {admin_btn}
      <div style="margin-top:8px;background:rgba(8,30,55,.88);border:2px solid #4a7ba6;padding:8px;display:flex;justify-content:space-around;font-weight:900;color:#fff;font-size:18px;border-radius:8px"><span>💎 {r}</span><span>🪙 {s}</span><span>🟡 {g}</span></div>
      <div style="margin-top:8px;background:rgba(8,30,55,.88);border:2px solid #4a7ba6;padding:8px 12px;display:flex;align-items:center;gap:10px;color:#fff;border-radius:8px">
        <div style="background:linear-gradient(#e8c268,#9a741f);width:42px;height:48px;display:flex;align-items:center;justify-content:center;font-weight:900;font-size:22px;clip-path:polygon(50% 0,100% 20%,100% 80%,50% 100%,0 80%,0 20%)">{l}</div>
        <div style="flex:1"><div style="font-weight:800">{nick} &nbsp;•&nbsp; {exp}/{lvl_exp}</div><div style="height:8px;background:#0a1a2a;border-radius:10px;margin-top:4px;overflow:hidden"><div style="width:{exp_per}%;height:100%;background:#7ab8ff"></div></div></div>
      </div>
      <div style="flex:1;display:flex;justify-content:space-between;align-items:center;gap:8px;margin:14px 0">
        <div style="display:flex;flex-direction:column;gap:10px;width:104px">
          <a href="/top" style="background:rgba(10,38,66,.92);border:2px solid #4a7ba6;color:#fff;text-decoration:none;text-align:center;padding:10px 4px;font-weight:800;border-radius:6px">🏆<br>Топ</a>
          <a href="/clan" style="background:rgba(10,38,66,.92);border:2px solid #4a7ba6;color:#fff;text-decoration:none;text-align:center;padding:10px 4px;font-weight:800;border-radius:6px">👥<br>Клан</a>
          <a href="/alliance" style="background:rgba(10,38,66,.92);border:2px solid #4a7ba6;color:#fff;text-decoration:none;text-align:center;padding:10px 4px;font-weight:800;border-radius:6px">🛡️<br>Альянс</a>
          <a href="/shop" style="background:rgba(10,38,66,.92);border:2px solid #4a7ba6;color:#fff;text-decoration:none;text-align:center;padding:10px 4px;font-weight:800;border-radius:6px">🛒<br>Магазин</a>
          <a href="/hero" style="background:rgba(10,38,66,.92);border:2px solid #4a7ba6;color:#fff;text-decoration:none;text-align:center;padding:10px 4px;font-weight:800;border-radius:6px">✉️<br>Почта</a>
          <a href="/bank" style="background:rgba(10,38,66,.92);border:2px solid #4a7ba6;color:#fff;text-decoration:none;text-align:center;padding:12px;border-radius:10px">🏦<br>Банк</a>
        </div>
        <div style="flex:1;text-align:center"><div style="background:rgba(8,30,55,.92);border:2px solid #4a7ba6;padding:14px 8px;border-radius:12px"><b style="color:#f5d98a;font-size:18px">Текущая зона</b><div style="font-size:24px;font-weight:bold;color:#fff;margin:10px 0">{loc_title}</div></div></div>
        <div style="display:flex;flex-direction:column;gap:10px;width:104px">
          <a href="/quests" style="background:rgba(10,38,66,.92);border:2px solid #4a7ba6;color:#fff;text-decoration:none;text-align:center;padding:10px 4px;font-weight:800;border-radius:6px">📜<br>Квесты</a>
          <a href="/online" style="background:rgba(10,38,66,.92);border:2px solid #4a7ba6;color:#fff;text-decoration:none;text-align:center;padding:10px 4px;font-weight:800;border-radius:6px">🟢<br>Онлайн</a>
          <a href="/hero" style="background:rgba(10,38,66,.92);border:2px solid #4a7ba6;color:#fff;text-decoration:none;text-align:center;padding:10px 4px;font-weight:800;border-radius:6px">⭐<br>Премиум</a>
          <a href="/online" style="background:rgba(10,38,66,.92);border:2px solid #4a7ba6;color:#fff;text-decoration:none;text-align:center;padding:10px 4px;font-weight:800;border-radius:6px">💬<br>Чат</a>
          <a href="/logout" style="background:rgba(10,38,66,.92);border:2px solid #4a7ba6;color:#fff;text-decoration:none;text-align:center;padding:10px 4px;font-weight:800;border-radius:6px">🚪<br>Выход</a>
          <a href="/pvp" style="background:rgba(10,38,66,.92);border:2px solid #4a7ba6;color:#fff;text-decoration:none;text-align:center;padding:12px;border-radius:10px">⚔️<br>PVP</a>
        </div>
      </div>
      <div style="display:flex;gap:10px;align-items:stretch">
        <a href="/promysel" style="flex:1;background:rgba(10,38,66,.92);border:2px solid #4a7ba6;color:#fff;text-decoration:none;text-align:center;padding:12px;font-weight:800;border-radius:8px">🌲<br>Промысел</a>
        <a href="/map" style="flex:2;background:linear-gradient(#1a3a5a,#0a1e35);border:2px solid #e8c268;color:#f5e6b0;text-decoration:none;text-align:center;padding:12px;font-weight:900;font-size:22px;border-radius:8px">📍 КАРТА</a>
        <a href="/hero" style="flex:1;background:rgba(10,38,66,.92);border:2px solid #4a7ba6;color:#fff;text-decoration:none;text-align:center;padding:12px;font-weight:800;border-radius:8px">👤<br>Герой</a>
      </div>
    </div>
    '''
    return render_page(html, False)

@app.route("/logout")
def logout():
    session.clear(); return redirect("/")

@app.route("/promysel")
def promysel():
    if "uid" not in session: return redirect("/")
    MONSTERS = get_monsters()
    p = get_player(session["uid"]); l, h, r, g, s = vals(p)
    top = f'<div style="background:#e8d6a8;padding:8px;display:flex;justify-content:center"><div style="background:#fdf6c8;border:2px solid #8a6a3d;border-radius:16px;padding:6px 14px;display:flex;gap:14px;font-weight:bold"><span>⭐ {l}</span><span>❤️ {h}</span><span>💎 {r}</span><span>🪙 {g}</span><span>⚪ {s}</span></div></div>'
    cards=""
    for key,cfg in MONSTERS.items():
        cards+=f'<div style="background:#3d2817;padding:6px;border-radius:6px;margin:10px 0"><div style="background:#f5e6c0;border:2px solid #5a3e22;border-radius:6px;padding:12px;display:flex;gap:12px;align-items:center"><img src="/static/{cfg["img"]}" style="width:55px;height:55px;object-fit:contain;background:#2b1a0e;border-radius:4px"><div style="flex:1"><b>{cfg["name"]}</b><br><small>HP: {cfg["hp"]} | Награда: {cfg["gold"]}🪙 {cfg["silver"]}⚪ {cfg["rubin"]}💎</small></div><a href="/fight/{key}" style="background:linear-gradient(#ff6b6b,#c92a2a);border:2px solid #5a3e22;border-radius:6px;padding:8px 16px;color:white;font-weight:bold;text-decoration:none">Атаковать</a></div></div>'
    body = top + f'<div class="wrap" style="background:#e8d6a8;padding:10px"><h3 style="text-align:center">🌲 Промысел - ОХОТА НА МОНСТРОВ</h3>{cards}<a href="/game" class="btn-orange">← На главную</a></div>'
    return render_page(body, True)

@app.route("/fight/<monster>")
def fight(monster):
    if "uid" not in session: return redirect("/")
    MONSTERS = get_monsters()
    p = get_player(session["uid"]); l, h, r, g, s_ = vals(p)
    cfg = MONSTERS.get(monster, MONSTERS["warrior"])
    session["enemy_type"] = cfg["name"]; session["enemy_hp"] = cfg.get("hp", 20); session["enemy_max"] = cfg.get("hp", 20)
    session["enemy_dmg"] = cfg.get("dmg", [2,4]); session["enemy_img"] = cfg.get("img", "ancient_warrior.png")
    session["my_hp"] = h; session["hit_count"] = 0; session["rewarded"] = False
    session["reward_g"] = cfg.get("gold", 2); session["reward_s"] = cfg.get("silver", 10); session["reward_r"] = cfg.get("rubin", 0)
    session.modified = True
    return redirect("/fight_battle")

@app.route("/fight_battle", methods=["GET", "POST"])
def fight_battle():
    if "uid" not in session: return redirect("/")
    if "enemy_hp" not in session: return redirect("/promysel")
    p = get_player(session["uid"]); lvl, my_max_hp, rubin, gold, silver = vals(p)
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        m = data.get("m") or request.form.get("m", "hit")
        if m == "run": return jsonify({"status": "redirect", "url": "/promysel"})
        cur_my = session.get("my_hp", my_max_hp); cur_en = session.get("enemy_hp", 20); hit_cnt = session.get("hit_count", 0)
        dmg = 0; edmg = 0
        if m == "enemy_auto":
            edmg = random.randint(2, 6); cur_my = max(0, cur_my - edmg)
        elif m == "hit" and cur_my > 0 and cur_en > 0:
            dmg = random.randint(3, 7); cur_en = max(0, cur_en - dmg); hit_cnt += 1
            if cur_en > 0:
                emin, emax = session.get("enemy_dmg", [2,5]); edmg = random.randint(emin, emax); cur_my = max(0, cur_my - edmg)
        elif m == "super" and hit_cnt >= 5 and cur_my > 0 and cur_en > 0:
            dmg = random.randint(10, 18); cur_en = max(0, cur_en - dmg); hit_cnt = 0
            if cur_en > 0:
                emin, emax = session.get("enemy_dmg", [2,5]); edmg = random.randint(emin, emax); cur_my = max(0, cur_my - edmg)
        session["enemy_hp"] = cur_en; session["my_hp"] = cur_my; session["hit_count"] = hit_cnt; session.modified = True
        finished = False; is_win = False
        if cur_en <= 0 and not session.get("rewarded"):
            add_win(session["uid"]); session["rewarded"] = True; finished = True; is_win = True
        elif cur_my <= 0 and not session.get("rewarded"):
            add_loss(session["uid"]); session["rewarded"] = True; finished = True; is_win = False
        return jsonify({"enemy_hp": cur_en, "enemy_max": session.get("enemy_max", 20), "my_hp": cur_my, "my_max": my_max_hp, "hit_cnt": hit_cnt, "last_dmg": dmg, "edmg": edmg, "finished": finished, "is_win": is_win, "reward_g": session.get("reward_g", 0), "reward_s": session.get("reward_s", 0), "reward_r": session.get("reward_r", 0)})
    cur_enemy_hp = session.get("enemy_hp", 20); enemy_max_hp = session.get("enemy_max", 20); cur_my_hp = session.get("my_hp", my_max_hp); hit_cnt = session.get("hit_count", 0)
    enemy_name = session.get("enemy_type", "Древний Воин"); enemy_img = session.get("enemy_img", "ancient_warrior.png")
    my_per = int(cur_my_hp * 100 / my_max_hp) if my_max_hp else 0; enemy_per = int(cur_enemy_hp * 100 / enemy_max_hp) if enemy_max_hp else 0
    html = f'''
    <style>
    body {{ background: #1a0e0a; margin: 0; font-family: Arial; }}
    .fight-wrap {{ max-width: 420px; margin: 0 auto; padding: 10px; }}
    @keyframes attackLeft {{ 0%{{transform:translateX(0)}} 50%{{transform:translateX(30px)}} 100%{{transform:translateX(0)}} }}
    @keyframes shakeRight {{ 0%,100%{{transform:translateX(0)}} 20%{{transform:translateX(-6px)}} 40%{{transform:translateX(6px)}} }}
    .potions-bar {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 4px; background: #2b1a0e; padding: 6px; border: 2px solid #5a3e22; border-radius: 8px; margin-top: 10px; }}
    .potion-slot {{ background: linear-gradient(#4a3525, #2b1a0e); border: 1px solid #8a6a3d; border-radius: 4px; height: 36px; display: flex; align-items: center; justify-content: center; color: #ffb84d; font-weight: bold; font-size: 12px; }}
    </style>
    <div class="fight-wrap" id="fightWrap">
      <div id="log" style="text-align:center;color:#ffeb00;font-weight:bold;min-height:24px;margin-bottom:6px">Приготовься к бою!</div>
      <div style="text-align:center;margin:0 10px 5px"><div style="height:8px;background:#222;border-radius:10px;overflow:hidden"><div id="timerBar" style="height:100%;width:100%;background:#ffcc00"></div></div><div id="turnText" style="font-size:13px;color:#ffcc00;margin-top:3px">Твой ход! 20 сек</div></div>
      <div style="background:rgba(245,230,200,0.95);border:2px solid #8b5a2b;border-radius:10px;padding:6px 10px;margin-bottom:6px"><div style="display:flex;justify-content:space-between;font-weight:900"><span>{enemy_name}</span><span><span id="enHp">{cur_enemy_hp}</span>/{enemy_max_hp}</span></div><div style="height:10px;background:#3a2a1a;border-radius:4px;overflow:hidden;margin-top:4px"><div id="enBar" style="width:{enemy_per}%;height:100%;background:#ff3b30;transition:width 0.2s"></div></div></div>
      <div style="background:url('/static/camp.jpg') center/cover no-repeat;border-radius:16px;border:3px solid #c89b5e;height:220px;display:flex;align-items:flex-end;justify-content:space-between;padding:10px">
        <div style="flex:1;text-align:center;position:relative"><img id="heroImg" src="/static/barbarian_game_size.png" style="height:130px;filter:drop-shadow(0 4px 8px black);"></div>
        <div style="flex:1;text-align:center;position:relative"><img id="enemyImg" src="/static/{enemy_img}" style="height:130px;filter:drop-shadow(0 4px 8px black);"></div>
      </div>
      <div style="background:rgba(245,230,200,0.95);border:2px solid #8b5a2b;border-radius:10px;padding:6px 10px;margin:8px 0"><div style="display:flex;justify-content:space-between;font-weight:900"><span>ВЫ</span><span><span id="myHp">{cur_my_hp}</span>/{my_max_hp}</span></div><div style="height:10px;background:#3a2a1a;border-radius:4px;overflow:hidden;margin-top:4px"><div id="myBar" style="width:{my_per}%;height:100%;background:#2ecc40;transition:width 0.2s"></div></div></div>
      <div id="battleLog" style="background:#1a0e0a;max-height:120px;overflow-y:auto;border:2px solid #5a3e22;border-radius:8px;margin:8px 10px;padding:4px"></div>
      <div style="display:flex;gap:8px">
        <button type="button" onclick="makeAction('hit')" style="flex:1;background:#2b1a0e;border:2px solid #ff8c00;border-radius:10px;padding:12px;color:#ffb84d;font-weight:900;cursor:pointer">⚔️ УДАР (<span id="hitCnt">{hit_cnt}</span>/5)</button>
        <button type="button" onclick="makeAction('super')" style="flex:1;background:#2b1a0e;border:2px solid #ffcc00;border-radius:10px;padding:12px;color:#ff0;font-weight:900;cursor:pointer">⚡ СУПЕР</button>
        <button type="button" onclick="makeAction('run')" style="background:#3a2a1a;border:2px solid #777;border-radius:10px;color:#ccc;padding:12px;font-weight:900;cursor:pointer">БЕГ</button>
      </div>
      <div class="potions-bar"><div class="potion-slot">🍷 1</div><div class="potion-slot">🧪 2</div><div class="potion-slot">📜 3</div><div class="potion-slot">🛡️ 4</div><div class="potion-slot">⚡ 5</div></div>
    </div>
    <div id="endOverlay" style="position:fixed;inset:0;background:rgba(0,0,0,0.88);backdrop-filter:blur(8px);display:none;align-items:center;justify-content:center;z-index:9999;padding:20px"><div style="background:linear-gradient(#3a2510,#1a0e0a);border:3px solid #ffcc00;border-radius:22px;padding:26px;width:100%;max-width:320px;text-align:center;box-shadow:0 0 40px gold"><h2 id="endTitle" style="margin:0;color:gold;font-size:26px"></h2><div id="trophyBox" style="background:rgba(255,215,0,0.12);border:1.5px solid #c9a45c;border-radius:14px;padding:14px;margin:14px 0;font-size:16px;line-height:1.8;color:#ffe9a3"></div><a href="/promysel" style="display:block;background:linear-gradient(#ffcc00,#c9a45c);color:#000;padding:14px;border-radius:12px;font-weight:900;text-decoration:none">На промысел ➔</a></div></div>
    <script src="/static/game.js"></script>
    '''
    return render_page(html, False)

@app.route("/shop")
def shop():
    if "uid" not in session: return redirect("/")
    return render_page('<div class="wrap" style="padding:15px"><h2 style="text-align:center">🛒 Магазин</h2><div style="background:#fdf6c8;border:2px solid #8a6a3d;border-radius:10px;padding:14px;margin:10px 0">🗡️ Меч воина - 10🪙<br><button class="btn-orange" onclick="alert(\'Скоро будет покупка!\')">Купить</button></div><div style="background:#fdf6c8;border:2px solid #8a6a3d;border-radius:10px;padding:14px;margin:10px 0">🛡️ Щит - 15🪙<br><button class="btn-orange" onclick="alert(\'Скоро будет покупка!\')">Купить</button></div><div style="background:#fdf6c8;border:2px solid #8a6a3d;border-radius:10px;padding:14px;margin:10px 0">🧪 Зелье HP - 5⚪<br><button class="btn-orange" onclick="alert(\'Скоро будет покупка!\')">Купить</button></div><a href="/game" class="btn-orange">← На главную</a></div>', True)

@app.route("/hero")
def hero():
    if "uid" not in session: return redirect("/")
    p = get_player(session["uid"]); l,h,r,g,s = vals(p)
    nick = p.get("name","Воин") if isinstance(p, dict) or hasattr(p,'get') else "Воин"
    exp = int(p.get("exp",0)) if isinstance(p, dict) or hasattr(p,'get') else 0
    wins = int(p.get("wins",0)) if isinstance(p, dict) or hasattr(p,'get') else 0
    losses = int(p.get("losses",0)) if isinstance(p, dict) or hasattr(p,'get') else 0
    admin_tag = " 👑 АДМИН" if is_admin() else ""
    return render_page(f'<div class="wrap" style="padding:15px;text-align:center"><h2>👤 {nick}{admin_tag}</h2><img src="/static/barbarian_game_size.png" style="height:180px"><div style="background:#fdf6c8;border:2px solid #8a6a3d;border-radius:10px;padding:14px;margin:10px;text-align:left"><b>Уровень:</b> {l}<br><b>HP:</b> {h}<br><b>Опыт:</b> {exp}<br><b>Побед:</b> {wins} | <b>Поражений:</b> {losses}<br><b>Золото:</b> {g}🪙 {s}⚪ {r}💎</div><a href="/game" class="btn-orange">← На главную</a></div>', True)

@app.route("/player/<int:pid>")
def player_view(pid):
    if "uid" not in session: return redirect("/")
    p = get_player(pid)
    if not p: return "Игрок не найден <a href='/online'>Назад</a>"
    nick = p.get("name","Воин") if isinstance(p,dict) else p[1]
    lg = p.get("login") if isinstance(p,dict) else p[2]
    gold = p.get("gold") if isinstance(p,dict) else p[4]
    silver = p.get("silver") if isinstance(p,dict) else p[5]
    rubin = p.get("rubin") if isinstance(p,dict) else p[6]
    exp = p.get("exp") if isinstance(p,dict) else p[7]
    lvl = p.get("level") if isinstance(p,dict) else p[8]
    hp = p.get("hp") if isinstance(p,dict) else p[9]
    wins = p.get("wins") if isinstance(p,dict) else p[10]
    losses = p.get("losses") if isinstance(p,dict) else p[11]
    is_me = (pid == session["uid"])
    admin_tag = " 👑 АДМИН" if lg == ADMIN_LOGIN else ""
    return render_page(f'<div class="wrap" style="padding:15px;text-align:center"><h2>👤 {nick}{admin_tag}</h2><p style="color:#666">@{lg} {"(Это ты!)" if is_me else ""}</p><img src="/static/barbarian_game_size.png" style="height:180px"><div style="background:#fdf6c8;border:2px solid #8a6a3d;border-radius:10px;padding:14px;margin:10px;text-align:left"><b>Уровень:</b> {lvl} / 21<br><b>HP:</b> {hp}<br><b>Опыт:</b> {exp}<br><b>Побед:</b> {wins} | <b>Поражений:</b> {losses}<br><b>Золото:</b> {gold}🪙 {silver}⚪ {rubin}💎</div><a href="/online" class="btn-orange">← К игрокам</a><a href="/game" class="btn-orange">← На главную</a></div>', True)

# === ТОП И ОНЛАЙН - ИГРОКИ ВИДЯТ ДРУГ ДРУГА ===
def _player_card(p, rank=None):
    pid = p["id"] if isinstance(p,dict) else p[0]
    nm = p["name"] if isinstance(p,dict) else p[1]
    lg = p["login"] if isinstance(p,dict) else p[2]
    gold = p["gold"] if isinstance(p,dict) else p[4]
    silver = p["silver"] if isinstance(p,dict) else p[5]
    rubin = p["rubin"] if isinstance(p,dict) else p[6]
    exp = p["exp"] if isinstance(p,dict) else p[7]
    lvl = p["level"] if isinstance(p,dict) else p[8]
    wins = p["wins"] if isinstance(p,dict) else p[10]
    losses = p["losses"] if isinstance(p,dict) else p[11]
    me = " (ТЫ)" if pid == session.get("uid") else ""
    crown = " 👑" if lg == ADMIN_LOGIN else ""
    rank_html = f"<b style='font-size:20px'>#{rank}</b>" if rank else "<span>🟢</span>"
    return f'<a href="/player/{pid}" class="player-card">{rank_html}<img src="/static/barbarian_game_size.png"><div style="flex:1;text-align:left"><b>{nm}{crown}{me}</b><br><small>@{lg} • ⭐ {lvl} ур. • 🏆 {wins} поб. • 💀 {losses} пор.</small><br><small>💎 {rubin} 🪙 {silver} 🟡 {gold} • XP {exp}</small></div><span style="font-size:22px">➔</span></a>'

@app.route("/top")
def top():
    if "uid" not in session: return redirect("/")
    try:
        conn=get_db(); cur=conn.cursor()
        if DATABASE_URL: cur.execute("SELECT * FROM players ORDER BY wins DESC, level DESC LIMIT 50")
        else: cur.execute("SELECT * FROM players ORDER BY wins DESC, level DESC LIMIT 50")
        rows=cur.fetchall(); cur.close(); conn.close()
    except: rows=[]
    items="".join([_player_card(r, i+1) for i,r in enumerate(rows)])
    if not items: items='<p style="text-align:center">Пока пусто — стань первым!</p>'
    return render_page(f'<div class="wrap" style="padding:15px"><h2 style="text-align:center">🏆 Топ игроков</h2><p style="text-align:center;font-size:13px;color:#666">Нажми на игрока, чтобы посмотреть его профиль</p>{items}<a href="/game" class="btn-orange">← На главную</a></div>', True)

@app.route("/online")
def online():
    if "uid" not in session: return redirect("/")
    try:
        conn=get_db(); cur=conn.cursor()
        if DATABASE_URL: cur.execute("SELECT * FROM players ORDER BY level DESC, wins DESC")
        else: cur.execute("SELECT * FROM players ORDER BY level DESC, wins DESC")
        rows=cur.fetchall(); cur.close(); conn.close()
    except: rows=[]
    items="".join([_player_card(r) for r in rows])
    if not items: items='<p style="text-align:center">Пока никого нет</p>'
    return render_page(f'<div class="wrap" style="padding:15px"><h2 style="text-align:center">🟢 Онлайн — {len(rows)} игроков</h2><p style="text-align:center;font-size:13px;color:#666">Все зарегистрированные игроки. Нажми на игрока — увидишь его профиль</p>{items}<a href="/game" class="btn-orange">← На главную</a></div>', True)

@app.route("/clan")
def clan():
    if "uid" not in session: return redirect("/")
    return render_page('<div class="wrap" style="padding:15px;text-align:center"><h2>🛡️ Клан</h2><div style="background:#fdf6c8;border:2px solid #8a6a3d;border-radius:10px;padding:20px">Тут скоро будут кланы!<br><br>Создай свой клан и зови друзей.</div><a href="/game" class="btn-orange">← На главную</a></div>', True)

@app.route("/alliance")
def alliance():
    if "uid" not in session: return redirect("/")
    return render_page('<div class="wrap" style="padding:15px;text-align:center"><h2>🤝 Альянс</h2><div style="background:#fdf6c8;border:2px solid #8a6a3d;border-radius:10px;padding:20px">Альянсы скоро появятся!</div><a href="/game" class="btn-orange">← На главную</a></div>', True)

@app.route("/bank", methods=["GET","POST"])
def bank():
    if "uid" not in session: return redirect("/")
    p=get_player(session["uid"]); l,hr,r,g,s=vals(p)
    # r = кристаллы, g = золото у тебя в vals
    if request.method=="POST":
        try: amount=int(request.form.get("amount",0))
        except: amount=0
        action=request.form.get("action")
        if amount>0:
            conn=get_db(); cur=conn.cursor()
            if action=="exchange" and r>=amount:
                # 1 кристалл = 500 золота
                cur.execute("UPDATE players SET rubies=rubies-%s, gold=gold+%s WHERE id=%s",(amount, amount*500, p["id"]))
                conn.commit()
            cur.close(); conn.close()
            return redirect("/bank")

    return render_page(f'''<div class="wrap" style="padding:15px;text-align:center">
    <h2>🏦 Банк</h2>
    <p style="font-size:18px">💎 Кристаллов: {r} | 🪙 Золота: {g}</p>
    <hr>
    <h3>💎 Купить кристаллы</h3>
    <p>100 💎 — 500 ₸</p>
    <p>550 💎 — 2500 ₸</p>
    <p>1200 💎 — 5000 ₸</p>
    <p>3000 💎 — 10000 ₸</p>
    <p style="color:#ffd700">Переведи на Kaspi и напиши админу свой ник!<br>Админ выдаст кристаллы вручную.</p>
    <hr>
    <h3>🔄 Обмен кристаллов на золото</h3>
    <p>Курс: 1 💎 = 500 🪙</p>
    <form method="post">
      <input name="amount" type="number" placeholder="Сколько кристаллов" style="padding:10px;width:70%">
      <br><br><button name="action" value="exchange" style="padding:10px 20px">Обменять на золото</button>
    </form>
    <br><a href="/game"><button>⬅ Назад</button></a>
    </div>''')

@app.route("/pvp")
def pvp():
    if "uid" not in session: return redirect("/")
    conn=get_db(); cur=conn.cursor()
    cur.execute("SELECT * FROM players WHERE id!=%s ORDER BY level DESC",(session["uid"],))
    rows=cur.fetchall(); cur.close(); conn.close()
    items="".join([f'<div style="border:1px solid #444;padding:10px;margin:8px;border-radius:10px">{r["username"]} — Ур. {r["level"]} | 🪙 {r["gold"]}<br><a href="/battle"><button>⚔️ Атаковать</button></a></div>' for r in rows])
    if not items: items='<p>Пока никого нет</p>'
    return render_page(f'<div class="wrap" style="padding:15px;text-align:center"><h2>⚔️ PVP — Выбери соперника</h2>{items}<br><a href="/game"><button>⬅ Назад</button></a></div>')

@app.route("/quests")
def quests():
    if "uid" not in session: return redirect("/")
    return render_page('<div class="wrap" style="padding:15px"><h2 style="text-align:center">📜 Задания</h2><div style="background:#fdf6c8;border:2px solid #8a6a3d;border-radius:10px;padding:14px;margin:10px 0">⚔️ Победи 3 монстра - Награда: 10🪙</div><div style="background:#fdf6c8;border:2px solid #8a6a3d;border-radius:10px;padding:14px;margin:10px 0">🏆 Дойди до 5 уровня - Награда: 5💎</div><a href="/game" class="btn-orange">← На главную</a></div>', True)

# === 👑 АДМИН ПАНЕЛЬ ===
@app.route("/admin", methods=["GET","POST"])
def admin():
    if "uid" not in session: return redirect("/")
    if not is_admin(): return "⛔ Нет доступа! Только для админа. <a href='/game'>На главную</a>"
    msg = ""
    if request.method == "POST":
        action = request.form.get("action")
        conn=get_db(); cur=conn.cursor()
        try:
            if action == "give":
                target_login = request.form.get("target_login","").strip()
                add_gold = int(request.form.get("add_gold") or 0)
                add_silver = int(request.form.get("add_silver") or 0)
                add_rubin = int(request.form.get("add_rubin") or 0)
                add_exp = int(request.form.get("add_exp") or 0)
                add_level = int(request.form.get("add_level") or 0)
                set_level = int(request.form.get("set_level") or 0)
                if DATABASE_URL: cur.execute("SELECT id, level, exp FROM players WHERE login=%s",(target_login,))
                else: cur.execute("SELECT id, level, exp FROM players WHERE login=?",(target_login,))
                row = cur.fetchone()
                if row:
                    tid = row["id"] if isinstance(row,dict) else row[0]
                    cur_lvl = int(row["level"] if isinstance(row,dict) else row[1] or 1)
                    cur_exp = int(row["exp"] if isinstance(row,dict) else row[2] or 0)
                    new_lvl = cur_lvl
                    if set_level > 0: new_lvl = set_level
                    elif add_level != 0: new_lvl = cur_lvl + add_level
                    if new_lvl > MAX_LVL: new_lvl = MAX_LVL
                    if new_lvl < 1: new_lvl = 1
                    if set_level > 0 or add_level != 0:
                        new_exp = XP_TABLE[new_lvl] + add_exp
                        new_lvl = get_lvl_by_xp(new_exp)
                        if new_lvl > MAX_LVL: new_lvl = MAX_LVL
                    else:
                        new_exp = cur_exp + add_exp
                        new_lvl = get_lvl_by_xp(new_exp)
                        if new_lvl > MAX_LVL: new_lvl = MAX_LVL
                        if new_exp > XP_TABLE[MAX_LVL]: new_exp = XP_TABLE[MAX_LVL]
                    if DATABASE_URL: cur.execute("UPDATE players SET gold=gold+%s, silver=silver+%s, rubin=rubin+%s, exp=%s, level=%s WHERE id=%s",(add_gold,add_silver,add_rubin,new_exp,new_lvl,tid))
                    else: cur.execute("UPDATE players SET gold=gold+?, silver=silver+?, rubin=rubin+?, exp=?, level=? WHERE id=?",(add_gold,add_silver,add_rubin,new_exp,new_lvl,tid))
                    conn.commit()
                    msg = f"✅ Выдано {target_login}: +{add_gold}🪙 +{add_silver}⚪ +{add_rubin}💎 +{add_exp} XP | Уровень теперь: {new_lvl} (было {cur_lvl})"
                else: msg = "❌ Игрок не найден"
            elif action == "edit_player":
                pid = int(request.form.get("pid"))
                lvl = int(request.form.get("level") or 1)
                if lvl > MAX_LVL: lvl = MAX_LVL
                if lvl < 1: lvl = 1
                exp = int(request.form.get("exp") or 0)
                if exp > XP_TABLE[MAX_LVL]: exp = XP_TABLE[MAX_LVL]
                gold = int(request.form.get("gold") or 0); silver = int(request.form.get("silver") or 0); rubin = int(request.form.get("rubin") or 0)
                hp = int(request.form.get("hp") or 20); wins = int(request.form.get("wins") or 0)
                if DATABASE_URL: cur.execute("UPDATE players SET level=%s, exp=%s, gold=%s, silver=%s, rubin=%s, hp=%s, wins=%s WHERE id=%s",(lvl,exp,gold,silver,rubin,hp,wins,pid))
                else: cur.execute("UPDATE players SET level=?, exp=?, gold=?, silver=?, rubin=?, hp=?, wins=? WHERE id=?",(lvl,exp,gold,silver,rubin,hp,wins,pid))
                conn.commit(); msg = "✅ Игрок обновлён!"
            elif action == "edit_monster":
                key = request.form.get("mkey")
                monsters = get_monsters()
                if key in monsters:
                    m = monsters[key]
                    m["hp"] = int(request.form.get("m_hp") or m["hp"])
                    m["gold"] = int(request.form.get("m_gold") or 0)
                    m["silver"] = int(request.form.get("m_silver") or 0)
                    m["rubin"] = int(request.form.get("m_rubin") or 0)
                    m["dmg"] = [int(request.form.get("m_dmg_min") or 2), int(request.form.get("m_dmg_max") or 4)]
                    save_monster(key, m); msg = f"✅ Монстр {m['name']} обновлён! Теперь награда {m['gold']}🪙 {m['silver']}⚪ {m['rubin']}💎"
        except Exception as e: msg = f"❌ Ошибка: {e}"
        cur.close(); conn.close()
    conn=get_db(); cur=conn.cursor()
    if DATABASE_URL: cur.execute("SELECT * FROM players ORDER BY id")
    else: cur.execute("SELECT * FROM players ORDER BY id")
    players = cur.fetchall(); cur.close(); conn.close()
    monsters = get_monsters()
    players_html = ""
    for p in players:
        pid = p["id"] if isinstance(p,dict) else p[0]
        nm = p["name"] if isinstance(p,dict) else p[1]
        lg = p["login"] if isinstance(p,dict) else p[2]
        gold = p["gold"] if isinstance(p,dict) else p[4]
        silver = p["silver"] if isinstance(p,dict) else p[5]
        rubin = p["rubin"] if isinstance(p,dict) else p[6]
        exp = p["exp"] if isinstance(p,dict) else p[7]
        lvl = p["level"] if isinstance(p,dict) else p[8]
        hp = p["hp"] if isinstance(p,dict) else p[9]
        wins = p["wins"] if isinstance(p,dict) else p[10]
        players_html += f'''
        <form method="post" style="background:#fdf6c8;border:2px solid #8a6a3d;border-radius:10px;padding:12px;margin:10px 0">
          <b>{nm} (@{lg}) — ID {pid}</b><br>
          <input type="hidden" name="action" value="edit_player">
          <input type="hidden" name="pid" value="{pid}">
          Уровень (1-21): <input name="level" type="number" value="{lvl}" min="1" max="21">
          Опыт: <input name="exp" type="number" value="{exp}">
          Золото 🪙: <input name="gold" type="number" value="{gold}">
          Серебро ⚪: <input name="silver" type="number" value="{silver}">
          Рубины 💎: <input name="rubin" type="number" value="{rubin}">
          HP ❤️: <input name="hp" type="number" value="{hp}">
          Побед 🏆: <input name="wins" type="number" value="{wins}">
          <button class="btn-orange" style="margin:5px auto">💾 Сохранить игрока</button>
        </form>'''
    monsters_html = ""
    for key,m in monsters.items():
        monsters_html += f'''
        <form method="post" style="background:#fff3cd;border:2px solid #c9a45c;border-radius:10px;padding:12px;margin:10px 0">
          <b>👹 {m["name"]} ({key})</b><br>
          <input type="hidden" name="action" value="edit_monster">
          <input type="hidden" name="mkey" value="{key}">
          HP монстра: <input name="m_hp" type="number" value="{m["hp"]}">
          Награда Золото 🪙: <input name="m_gold" type="number" value="{m["gold"]}">
          Награда Серебро ⚪: <input name="m_silver" type="number" value="{m["silver"]}">
          Награда Рубины 💎: <input name="m_rubin" type="number" value="{m["rubin"]}">
          Урон мин: <input name="m_dmg_min" type="number" value="{m["dmg"][0]}">
          Урон макс: <input name="m_dmg_max" type="number" value="{m["dmg"][1]}">
          <button class="btn-orange" style="margin:5px auto">💾 Сохранить монстра</button>
        </form>'''
    html = f'''
    <div class="wrap" style="padding:15px">
      <h2 style="text-align:center">👑 АДМИН ПАНЕЛЬ</h2>
      <p style="text-align:center;color:green;font-weight:bold">{msg}</p>
      <h3>🎁 Быстрая выдача + УРОВНИ</h3>
      <form method="post" style="background:#e8ffd6;border:2px solid green;border-radius:10px;padding:12px">
        <input type="hidden" name="action" value="give">
        Логин игрока: <input name="target_login" placeholder="например: warrior123" required>
        + Золото 🪙: <input name="add_gold" type="number" value="0">
        + Серебро ⚪: <input name="add_silver" type="number" value="0">
        + Рубины 💎: <input name="add_rubin" type="number" value="0">
        + Опыт XP: <input name="add_exp" type="number" value="0">
        <div style="background:#fff3cd;border:2px solid #c9a45c;border-radius:8px;padding:10px;margin:8px 0">
          <b>⭐ ВЫДАЧА УРОВНЕЙ:</b><br>
          + Добавить уровней: <input name="add_level" type="number" value="0" placeholder="например: +3">
          Поставить точный уровень (1-21): <input name="set_level" type="number" value="0" min="0" max="21" placeholder="0 = не менять">
        </div>
        <button class="btn-orange">🎁 ВЫДАТЬ</button>
      </form>
      <h3>👹 Награды за монстров</h3>
      {monsters_html}
      <h3>👥 Все игроки</h3>
      {players_html}
      <a href="/game" class="btn-orange">← На главную</a>
    </div>'''
    return render_page(html, False)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)