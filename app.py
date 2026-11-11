from curses import longname
import os, random
from flask import Flask, request, send_from_directory, session, redirect, jsonify, render_template_string
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
        "hp": 100,
        "dmg": (4,7),
        "gold": 5, "silver": 20, "rubin": 1
    }
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
        conn = get_db()
        cur = conn.cursor()
        if DATABASE_URL:
            cur.execute("CREATE TABLE IF NOT EXISTS players (id SERIAL PRIMARY KEY, name TEXT, login TEXT UNIQUE, password TEXT, gold INT DEFAULT 15, silver INT DEFAULT 50, rubin INT DEFAULT 0, exp INT DEFAULT 0, level INT DEFAULT 1, hp INT DEFAULT 20, wins INT DEFAULT 1, losses INT DEFAULT 0)")
        else:
            cur.execute("CREATE TABLE IF NOT EXISTS players (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, login TEXT UNIQUE, password TEXT, gold INT DEFAULT 15, silver INT DEFAULT 50, rubin INT DEFAULT 0, exp INT DEFAULT 0, level INT DEFAULT 1, hp INTEGER DEFAULT 20, wins INT DEFAULT 1, losses INT DEFAULT 0)")
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"DB INIT ERROR: {e}")
init_db()

def convert_silver(uid):
    try:
        conn = get_db()
        cur = conn.cursor()
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
        conn = get_db()
        cur = conn.cursor()
        if DATABASE_URL: cur.execute("SELECT * FROM players WHERE id=%s",(uid,))
        else: cur.execute("SELECT * FROM players WHERE id=?",(uid,))
        p = cur.fetchone()
        cur.close()
        conn.close()
        return p
    except: return None

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
        rg = session.get("reward_g", 0)
        rs = session.get("reward_s", 0)
        rr = session.get("reward_r", 0)
        conn = get_db()
        cur = conn.cursor()
        if DATABASE_URL:
            cur.execute("UPDATE players SET wins=COALESCE(wins,0)+1, gold=COALESCE(gold,0)+%s, silver=COALESCE(silver,0)+%s, rubin=COALESCE(rubin,0)+%s, exp=COALESCE(exp,0)+10 WHERE id=%s",(rg, rs, rr, uid))
            cur.execute("UPDATE players SET level=level+1, exp=0 WHERE id=%s AND exp >= level*100", (uid,))
        else:
            cur.execute("UPDATE players SET wins=COALESCE(wins,0)+1, gold=COALESCE(gold,0)+?, silver=COALESCE(silver,0)+?, rubin=COALESCE(rubin,0)+?, exp=COALESCE(exp,0)+10 WHERE id=?",(rg, rs, rr, uid))
            cur.execute("UPDATE players SET level=level+1, exp=0 WHERE id=? AND exp >= level*100", (uid,))
        conn.commit()
        cur.close()
        conn.close()
        convert_silver(uid)
    except Exception as e:
        print(f"add_win error {e}")

def add_loss(uid):
    try:
        conn = get_db()
        cur = conn.cursor()
        if DATABASE_URL: cur.execute("UPDATE players SET losses=COALESCE(losses,0)+1 WHERE id=%s",(uid,))
        else: cur.execute("UPDATE players SET losses=COALESCE(losses,0)+1 WHERE id=?",(uid,))
        conn.commit()
        cur.close()
        conn.close()
    except: pass

BASE_CSS = """
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover">
<style>
*{box-sizing:border-box}
html,body{width:100%;overflow-x:hidden}
body{margin:0;background:#2b2218;font-family:Arial;-webkit-text-size-adjust:100%}
.wrap{width:100%;max-width:480px;margin:0 auto;min-height:100dvh;background:#e8d6a8;padding-bottom:90px}
.btn-orange{display:block;width:90%;margin:10px auto;background:linear-gradient(#ffb84d,#ff8c00);border:2px solid #5a3e22;border-radius:6px;padding:12px;text-align:center;font-weight:bold;font-size:18px;color:#3d2817;text-decoration:none;cursor:pointer}
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
    html = f'<div class="wrap" style="padding:20px"><h1 style="text-align:center">BATTLE OF WARRIORS</h1><form method="post" action="/login"><input name="login" placeholder="Login" style="width:100%;padding:12px;margin:6px 0" required><input name="password" type="password" placeholder="Pass" style="width:100%;padding:12px;margin:6px 0" required><button class="btn-orange">Войти</button></form><a href="/reg" style="display:block;text-align:center;margin-top:10px">Регистрация</a></div>'
    return render_template_string(BASE_CSS+html)

@app.route("/login", methods=["POST"])
def login():
    lg = request.form.get("login","").strip()
    pw = request.form.get("password","")
    conn = get_db()
    cur = conn.cursor()
    if DATABASE_URL: cur.execute("SELECT * FROM players WHERE login=%s",(lg,))
    else: cur.execute("SELECT * FROM players WHERE login=?",(lg,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row:
        hpw = row["password"] if isinstance(row, dict) or hasattr(row,'get') else row[3]
        uid = row["id"] if isinstance(row, dict) or hasattr(row,'get') else row[0]
        if check_password_hash(hpw, pw):
            session["uid"] = uid
            session["my_hp"] = 20
            session["current_loc"] = "lager"
            return redirect("/game")
    return "Неверный пароль <a href='/'>назад</a>"

@app.route("/reg", methods=["GET","POST"])
def reg():
    if request.method == "POST":
        name = request.form.get("name","").strip()
        lg = request.form.get("login","").strip()
        pw = request.form.get("password","")
        try:
            conn = get_db()
            cur = conn.cursor()
            h = generate_password_hash(pw)
            if DATABASE_URL: 
                cur.execute("INSERT INTO players (name,login,password,gold,silver,rubin) VALUES (%s,%s,%s,15,50,0) RETURNING id",(name,lg,h))
                uid = cur.fetchone()["id"]
            else: 
                cur.execute("INSERT INTO players (name,login,password,gold,silver,rubin) VALUES (?,?,?,15,50,0)",(name,lg,h))
                uid = cur.lastrowid
            conn.commit()
            cur.close()
            conn.close()
            session["uid"] = uid
            session["my_hp"] = 20
            session["current_loc"] = "lager"
            return redirect("/game")
        except Exception as e: 
            return f"Логин занят {e} <a href='/reg'>назад</a>"
    html = '<div class="wrap" style="padding:20px"><h2>Регистрация</h2><form method="post"><input name="name" placeholder="Имя" style="width:100%;padding:10px;margin:5px 0" required><input name="login" placeholder="Логин" style="width:100%;padding:10px;margin:5px 0" required><input name="password" type="password" placeholder="Пароль" style="width:100%;padding:10px;margin:5px 0" required><button class="btn-orange">Создать</button></form></div>'
    return render_template_string(BASE_CSS+html)

MAP_HTML = """
<div style="max-width:480px;margin:0 auto;padding:10px;min-height:100vh;background:#1a0e0a;color:#fff">
<div style="background:rgba(8,30,55,.92);border:2px solid #4a7ba6;padding:12px;text-align:center">
<h3 style="color:#fff;margin:0">📍 КАРТА МИРА</h3>
</div>
<br>
<a href="/loc/lager" style="display:block;background:rgba(8,30,55,.92);border:2px solid #f0c040;padding:16px;color:#fff;text-decoration:none;font-size:20px;font-weight:bold;border-radius:8px;margin-bottom:10px">🏕️ Лагерь</a>
<a href="/loc/zastava" style="display:block;background:rgba(8,30,55,.92);border:2px solid #3aa0ff;padding:16px;color:#fff;text-decoration:none;font-size:20px;font-weight:bold;border-radius:8px;margin-bottom:10px">🛡️ Застава</a>
<a href="/loc/oboz" style="display:block;background:rgba(8,30,55,.92);border:2px solid #3aa0ff;padding:16px;color:#fff;text-decoration:none;font-size:20px;font-weight:bold;border-radius:8px;margin-bottom:10px">🛒 Обоз</a>
<a href="/game" style="display:block;background:#5a3e22;color:#fff;text-align:center;padding:14px;text-decoration:none;font-weight:bold;border-radius:8px">← Вернуться в игру</a>
</div>
"""

@app.route("/map")
def map_page():
    if "uid" not in session: return redirect("/")
    return render_page(MAP_HTML, True)

@app.route("/loc/<code>")
def go_loc(code):
    if "uid" not in session: return redirect("/")
    session["current_loc"] = code
    if code == "promysel":
        return redirect("/promysel")
    return redirect(f"/game?loc={code}")

@app.route("/game")
def game():
    if "uid" not in session: return redirect("/")
    p = get_player(session["uid"])
    l, h, r, g, s = vals(p)
    exp = int(p.get("exp",0)) if isinstance(p, dict) or hasattr(p,'get') else 0
    nick = p.get("name","Воин") if isinstance(p, dict) or hasattr(p,'get') else "Воин"

    current = request.args.get("loc") or session.get("current_loc") or "lager"
    session["current_loc"] = current
    
    bg_map = {
        "lager": "/static/lager.jpg", 
        "zastava": "/static/zastava.jpg", 
        "oboz": "/static/oboz.jpg"
    }
    bg = bg_map.get(current, "/static/lager.jpg")

    loc_names = {
        "lager": "🏕️ Лагерь",
        "zastava": "🛡️ Застава",
        "oboz": "🛒 Обоз"
    }
    loc_title = loc_names.get(current, "🏕️ Лагерь")
    lvl_exp = max(100, l * 100)
    exp_per = min(100, exp % 100)

    html = f'''
    <div style="max-width:480px;margin:0 auto;min-height:100vh;background:url('{bg}') center/cover no-repeat;display:flex;flex-direction:column;padding:10px;box-sizing:border-box">
      <div style="background:rgba(8,30,55,.9);border:2px solid #4a7ba6;padding:8px;text-align:center;color:#fff;font-weight:900;font-size:22px;border-radius:8px">BATTLE</div>
      
      <div style="margin-top:8px;background:rgba(8,30,55,.88);border:2px solid #4a7ba6;padding:8px;display:flex;justify-content:space-around;font-weight:900;color:#fff;font-size:18px;border-radius:8px">
        <span>💎 {r}</span><span>🪙 {s}</span><span>🟡 {g}</span>
      </div>

      <div style="margin-top:8px;background:rgba(8,30,55,.88);border:2px solid #4a7ba6;padding:8px 12px;display:flex;align-items:center;gap:10px;color:#fff;border-radius:8px">
        <div style="background:linear-gradient(#e8c268,#9a741f);width:42px;height:48px;display:flex;align-items:center;justify-content:center;font-weight:900;font-size:22px;clip-path:polygon(50% 0,100% 20%,100% 80%,50% 100%,0 80%,0 20%)">{l}</div>
        <div style="flex:1">
          <div style="font-weight:800">{nick} &nbsp;•&nbsp; {exp}/{lvl_exp}</div>
          <div style="height:8px;background:#0a1a2a;border-radius:10px;margin-top:4px;overflow:hidden">
            <div style="width:{exp_per}%;height:100%;background:#7ab8ff"></div>
          </div>
        </div>
      </div>

      <div style="flex:1;display:flex;justify-content:space-between;align-items:center;gap:8px;margin:14px 0">
        <div style="display:flex;flex-direction:column;gap:10px;width:104px">
          <a href="/top" style="background:rgba(10,38,66,.92);border:2px solid #4a7ba6;color:#fff;text-decoration:none;text-align:center;padding:10px 4px;font-weight:800;border-radius:6px">🏆<br>Топ</a>
          <a href="/clan" style="background:rgba(10,38,66,.92);border:2px solid #4a7ba6;color:#fff;text-decoration:none;text-align:center;padding:10px 4px;font-weight:800;border-radius:6px">👥<br>Клан</a>
          <a href="/alliance" style="background:rgba(10,38,66,.92);border:2px solid #4a7ba6;color:#fff;text-decoration:none;text-align:center;padding:10px 4px;font-weight:800;border-radius:6px">🛡️<br>Альянс</a>
        </div>

        <div style="flex:1;text-align:center">
          <div style="background:rgba(8,30,55,.92);border:2px solid #4a7ba6;padding:14px 8px;border-radius:12px">
            <b style="color:#f5d98a;font-size:18px">Текущая зона</b>
            <div style="font-size:24px;font-weight:bold;color:#fff;margin:10px 0">{loc_title}</div>
          </div>
        </div>

        <div style="display:flex;flex-direction:column;gap:10px;width:104px">
          <a href="/quests" style="background:rgba(10,38,66,.92);border:2px solid #4a7ba6;color:#fff;text-decoration:none;text-align:center;padding:10px 4px;font-weight:800;border-radius:6px">📜<br>Квесты</a>
          <a href="/online" style="background:rgba(10,38,66,.92);border:2px solid #4a7ba6;color:#fff;text-decoration:none;text-align:center;padding:10px 4px;font-weight:800;border-radius:6px">🟢<br>Онлайн</a>
          <a href="/online" style="background:rgba(10,38,66,.92);border:2px solid #4a7ba6;color:#fff;text-decoration:none;text-align:center;padding:10px 4px;font-weight:800;border-radius:6px">🟢<br>Премиум</a>
          <a href="/online" style="background:rgba(10,38,66,.92);border:2px solid #4a7ba6;color:#fff;text-decoration:none;text-align:center;padding:10px 4px;font-weight:800;border-radius:6px">🟢<br>Чат</a> 
          <a href="/online" style="background:rgba(10,38,66,.92);border:2px solid #4a7ba6;color:#fff;text-decoration:none;text-align:center;padding:10px 4px;font-weight:800;border-radius:6px">🟢<br>Выход</a>
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
    session.clear()
    return redirect("/")

@app.route("/promysel")
def promysel():
    if "uid" not in session: return redirect("/")
    p = get_player(session["uid"])
    l, h, r, g, s = vals(p)
    top = f'<div style="background:#e8d6a8;padding:8px;display:flex;justify-content:center"><div style="background:#fdf6c8;border:2px solid #8a6a3d;border-radius:16px;padding:6px 14px;display:flex;gap:14px;font-weight:bold"><span>⭐ {l}</span><span>❤️ {h}</span><span>💎 {r}</span><span>🪙 {g}</span><span>⚪ {s}</span></div></div>'
    body = top + f'''
    <div class="wrap" style="background:#e8d6a8;padding:10px">
    <h3 style="text-align:center">🌲 Промысел - ОХОТА НА МОНСТРОВ</h3>
    
    <div style="background:#3d2817;padding:6px;border-radius:6px;margin:10px 0">
      <div style="background:#f5e6c0;border:2px solid #5a3e22;border-radius:6px;padding:12px;display:flex;gap:12px;align-items:center">
        <img src="/static/{MONSTERS_CFG["warrior"]["img"]}" style="width:55px;height:55px;object-fit:contain;background:#2b1a0e;border-radius:4px">
        <div style="flex:1"><b>{MONSTERS_CFG["warrior"]["name"]}</b><br><small>Награда: {MONSTERS_CFG["warrior"]["gold"]}🪙 {MONSTERS_CFG["warrior"]["silver"]}⚪</small></div>
        <a href="/fight/warrior" style="background:linear-gradient(#ff6b6b,#c92a2a);border:2px solid #5a3e22;border-radius:6px;padding:8px 16px;color:white;font-weight:bold;text-decoration:none">Атаковать</a>
      </div>
    </div>
    
    <div style="background:#3d2817;padding:6px;border-radius:6px;margin:10px 0">
      <div style="background:#f5e6c0;border:2px solid #5a3e22;border-radius:6px;padding:12px;display:flex;gap:12px;align-items:center">
        <img src="/static/{MONSTERS_CFG["beast"]["img"]}" style="width:55px;height:55px;object-fit:contain;background:#1a2e1a;border-radius:4px">
        <div style="flex:1"><b>{MONSTERS_CFG["beast"]["name"]}</b><br><small>Награда: {MONSTERS_CFG["beast"]["gold"]}🪙 {MONSTERS_CFG["beast"]["silver"]}⚪ {MONSTERS_CFG["beast"]["rubin"]}💎</small></div>
        <a href="/fight/beast" style="background:linear-gradient(#ff6b6b,#c92a2a);border:2px solid #5a3e22;border-radius:6px;padding:8px 16px;color:white;font-weight:bold;text-decoration:none">Атаковать</a>
      </div>
    </div>
    
    <a href="/game" class="btn-orange">← На главную</a></div>'''
    return render_page(body, True)

@app.route("/fight/<monster>")
def fight(monster):
    if "uid" not in session: return redirect("/")
    p = get_player(session["uid"])
    l, h, r, g, s_ = vals(p)
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
        elif m == "super" and hit_cnt >= 5 and cur_my > 0 and cur_en > 0:
            dmg = random.randint(10, 18)
            cur_en = max(0, cur_en - dmg)
            hit_cnt = 0
        
        if cur_en > 0 and m in ["hit", "super"] and cur_my > 0:
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
        elif cur_my <= 0 and not session.get("rewarded"):
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
    enemy_img = session.get("enemy_img", "ancient_warrior.png")
    
    my_per = int(cur_my_hp * 100 / my_max_hp) if my_max_hp else 0
    enemy_per = int(cur_enemy_hp * 100 / enemy_max_hp) if enemy_max_hp else 0

    html = f'''
    <style>
    body {{ background: #1a0e0a; margin: 0; font-family: Arial; }}
    .fight-wrap {{ max-width: 420px; margin: 0 auto; padding: 10px; }}
    @keyframes attackLeft {{ 0%{{transform:translateX(0)}} 50%{{transform:translateX(30px)}} 100%{{transform:translateX(0)}} }}
    @keyframes shakeRight {{ 0%,100%{{transform:translateX(0)}} 20%{{transform:translateX(-6px)}} 40%{{transform:translateX(6px)}} }}
    .anim-attack {{ animation: attackLeft 0.3s ease; }}
    .anim-shake {{ animation: shakeRight 0.3s ease; }}
    .potions-bar {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 4px; background: #2b1a0e; padding: 6px; border: 2px solid #5a3e22; border-radius: 8px; margin-top: 10px; }}
    .potion-slot {{ background: linear-gradient(#4a3525, #2b1a0e); border: 1px solid #8a6a3d; border-radius: 4px; height: 36px; display: flex; align-items: center; justify-content: center; color: #ffb84d; font-weight: bold; font-size: 12px; cursor: pointer; }}
    </style>

    <div class="fight-wrap" id="fightWrap">
      <div id="log" style="text-align:center;color:#ffeb00;font-weight:bold;min-height:24px;margin-bottom:6px">Приготовься к бою!</div>
      
      <div style="background:rgba(245,230,200,0.95);border:2px solid #8b5a2b;border-radius:10px;padding:6px 10px;margin-bottom:6px">
        <div style="display:flex;justify-content:space-between;font-weight:900"><span>{enemy_name}</span><span><span id="enHp">{cur_enemy_hp}</span>/{enemy_max_hp}</span></div>
        <div style="height:10px;background:#3a2a1a;border-radius:4px;overflow:hidden;margin-top:4px"><div id="enBar" style="width:{enemy_per}%;height:100%;background:#ff3b30;transition:width 0.2s"></div></div>
      </div>

      <div style="background:url('/static/camp.jpg') center/cover no-repeat;border-radius:16px;border:3px solid #c89b5e;height:220px;display:flex;align-items:flex-end;justify-content:space-between;padding:10px">
        <div style="flex:1;text-align:center"><img id="heroImg" src="/static/barbarian_game_size.png" style="height:130px;filter:drop-shadow(0 4px 8px black);"></div>
        <div style="flex:1;text-align:center"><img id="enemyImg" src="/static/{enemy_img}" style="height:130px;filter:drop-shadow(0 4px 8px black);"></div>
      </div>

      <div style="background:rgba(245,230,200,0.95);border:2px solid #8b5a2b;border-radius:10px;padding:6px 10px;margin:8px 0">
        <div style="display:flex;justify-content:space-between;font-weight:900"><span>ВЫ</span><span><span id="myHp">{cur_my_hp}</span>/{my_max_hp}</span></div>
        <div style="height:10px;background:#3a2a1a;border-radius:4px;overflow:hidden;margin-top:4px"><div id="myBar" style="width:{my_per}%;height:100%;background:#2ecc40;transition:width 0.2s"></div></div>
      </div>

      <div style="display:flex;gap:8px">
        <button type="button" onclick="makeAction('hit')" style="flex:1;background:#2b1a0e;border:2px solid #ff8c00;border-radius:10px;padding:12px;color:#ffb84d;font-weight:900;cursor:pointer">⚔️ УДАР (<span id="hitCnt">{hit_cnt}</span>/5)</button>
        <button type="button" onclick="makeAction('super')" id="superBtn" style="flex:1;background:#2b1a0e;border:2px solid #ffcc00;border-radius:10px;padding:12px;color:#ff0;font-weight:900;cursor:pointer">⚡ СУПЕР</button>
        <button type="button" onclick="makeAction('run')" style="background:#3a2a1a;border:2px solid #777;border-radius:10px;color:#ccc;padding:12px;font-weight:900;cursor:pointer">БЕГ</button>
      </div>

      <div class="potions-bar">
        <div class="potion-slot">🍷 1</div>
        <div class="potion-slot">🧪 2</div>
        <div class="potion-slot">📜 3</div>
        <div class="potion-slot">🛡️ 4</div>
        <div class="potion-slot">⚡ 5</div>
      </div>
    </div>

    <div id="endOverlay" style="position:fixed;inset:0;background:rgba(0,0,0,0.88);backdrop-filter:blur(8px);display:none;align-items:center;justify-content:center;z-index:9999;padding:20px">
      <div style="background:linear-gradient(#3a2510,#1a0e0a);border:3px solid #ffcc00;border-radius:22px;padding:26px;width:100%;max-width:320px;text-align:center;box-shadow:0 0 40px gold">
        <h2 id="endTitle" style="margin:0;color:gold;font-size:26px"></h2>
        <div id="trophyBox" style="background:rgba(255,215,0,0.12);border:1.5px solid #c9a45c;border-radius:14px;padding:14px;margin:14px 0;font-size:16px;line-height:1.8;color:#ffe9a3"></div>
        <a href="/promysel" style="display:block;background:linear-gradient(#ffcc00,#c9a45c);color:#000;padding:14px;border-radius:12px;font-weight:900;text-decoration:none">На промысел ➔</a>
      </div>
    </div>

    <script>
    async function makeAction(type) {{
        const overlay = document.getElementById('endOverlay');
        if (overlay && overlay.style.display === 'flex') return;

        const hero = document.getElementById('heroImg');
        const enemy = document.getElementById('enemyImg');

        if (type === 'hit' || type === 'super') {{
            hero.classList.remove('anim-attack'); void hero.offsetWidth; hero.classList.add('anim-attack');
            enemy.classList.remove('anim-shake'); void enemy.offsetWidth; enemy.classList.add('anim-shake');
        }}

        try {{
            let r = await fetch('/fight_battle', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{m: type}})
            }});
            
            let data = await r.json();
            if (data.status === 'redirect') {{
                location.href = data.url;
                return;
            }}

            document.getElementById('enHp').innerText = data.enemy_hp;
            document.getElementById('enBar').style.width = Math.max(0, (data.enemy_hp * 100 / data.enemy_max)) + '%';
            document.getElementById('myHp').innerText = data.my_hp;
            document.getElementById('myBar').style.width = Math.max(0, (data.my_hp * 100 / data.my_max)) + '%';
            document.getElementById('hitCnt').innerText = data.hit_cnt;

            let logEl = document.getElementById('log');
            if (type === 'hit') {{
                logEl.innerHTML = `Вы нанесли <span style="color:#ff4d4d">-${data.last_dmg}</span> HP! Враг ответил <span style="color:#ff4d4d">-${data.edmg}</span> HP`;
            }} else if (type === 'super') {{
                logEl.innerHTML = `🔥 СУПЕРУДАР! Нанесено <span style="color:#ff4d4d">-${data.last_dmg}</span> HP! Враг ответил <span style="color:#ff4d4d">-${data.edmg}</span> HP`;
            }}

            if (data.finished) {{
                document.getElementById('endOverlay').style.display = 'flex';
                if (data.is_win) {{
                    document.getElementById('endTitle').innerText = '🏆 ПОБЕДА!';
                    document.getElementById('trophyBox').innerHTML = `<b>Получено:</b><br>🪙 Золото: +${data.reward_g}<br>⚪ Серебро: +${data.reward_s}<br>💎 Рубины: +${data.reward_r}`;
                }} else {{
                    document.getElementById('endTitle').innerText = '💀 ПОРАЖЕНИЕ!';
                    document.getElementById('endTitle').style.color = '#ff4d4d';
                    document.getElementById('trophyBox').innerHTML = 'Вы пали в бою... Попробуйте восстановить силы!';
                }}
            }}
        }} catch(e) {{
            console.error("Ошибка боя:", e);
        }}
    }}
    </script>
    '''
    return render_page(html, False)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)