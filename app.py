import os, random, json, time, re
from flask import Flask, request, send_from_directory, session, redirect, jsonify, render_template_string, render_template
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

# ===== ДАННЫЕ ИЗ ПАПКИ data/ - ЕДИНЫЙ ИСТОЧНИК ПРАВДЫ =====
def load_json(name):
    path = os.path.join(os.path.dirname(__file__), "data", f"{name}.json")
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_json(name, data):
    path = os.path.join(os.path.dirname(__file__), "data", f"{name}.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

LOCATIONS = load_json("locations")
DEFAULT_MONSTERS = load_json("monsters") or {
    "warrior": {"name": "Древний воин", "img": "ancient_warrior.png", "hp": 20, "dmg": [2,4], "gold": 2, "silver": 10, "rubin": 0, "location": "promysel"},
    "beast": {"name": "Дух зверя", "img": "spirit_wolf_left.png", "hp": 100, "dmg": [4,7], "gold": 5, "silver": 20, "rubin": 1, "location": "promysel"},
}
SHOP = load_json("shop") or {}

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
            cur.execute("CREATE TABLE IF NOT EXISTS chat_messages (id SERIAL PRIMARY KEY, uid INT, tab TEXT DEFAULT 'all', text TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
            # === БОЙ: таблица для незавершённых боёв ===
            cur.execute("CREATE TABLE IF NOT EXISTS fights (uid INT PRIMARY KEY, enemy TEXT, enemy_hp INT, enemy_max INT, enemy_dmg_min INT, enemy_dmg_max INT, enemy_img TEXT, enemy_name TEXT, my_hp INT, hit_count INT DEFAULT 0, super_used INT DEFAULT 0, super_hits INT DEFAULT 0, shield_active BOOLEAN DEFAULT FALSE, reward_g INT DEFAULT 0, reward_s INT DEFAULT 0, reward_r INT DEFAULT 0, last_seen BIGINT DEFAULT 0)")
        else:
            cur.execute("CREATE TABLE IF NOT EXISTS players (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, login TEXT UNIQUE, password TEXT, gold INT DEFAULT 15, silver INT DEFAULT 50, rubin INT DEFAULT 0, exp INT DEFAULT 0, level INT DEFAULT 1, hp INTEGER DEFAULT 20, wins INT DEFAULT 1, losses INT DEFAULT 0)")
            cur.execute("CREATE TABLE IF NOT EXISTS chat_messages (id INTEGER PRIMARY KEY AUTOINCREMENT, uid INT, tab TEXT DEFAULT 'all', text TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
            cur.execute("CREATE TABLE IF NOT EXISTS fights (uid INTEGER PRIMARY KEY, enemy TEXT, enemy_hp INTEGER, enemy_max INTEGER, enemy_dmg_min INTEGER, enemy_dmg_max INTEGER, enemy_img TEXT, enemy_name TEXT, my_hp INTEGER, hit_count INTEGER DEFAULT 0, super_used INTEGER DEFAULT 0, super_hits INTEGER DEFAULT 0, shield_active INTEGER DEFAULT 0, reward_g INTEGER DEFAULT 0, reward_s INTEGER DEFAULT 0, reward_r INTEGER DEFAULT 0, last_seen INTEGER DEFAULT 0)")
        conn.commit(); cur.close(); conn.close()
    except Exception as e: print(f"DB INIT ERROR: {e}")
init_db()

# ===== ФУНКЦИИ БОЯ (сохранение в БД, бой продолжается офлайн) =====
def get_fight_db(uid):
    if not uid: return None
    try:
        conn = get_db(); cur = conn.cursor()
        q = "SELECT * FROM fights WHERE uid=%s" if DATABASE_URL else "SELECT * FROM fights WHERE uid=?"
        cur.execute(q, (uid,))
        row = cur.fetchone(); cur.close(); conn.close()
        if not row: return None
        # RealDictCursor / sqlite Row -> dict
        if isinstance(row, dict): return dict(row)
        try: return dict(row)
        except: return {"uid": row[0], "enemy": row[1], "enemy_hp": row[2], "enemy_max": row[3], "enemy_dmg_min": row[4], "enemy_dmg_max": row[5], "enemy_img": row[6], "enemy_name": row[7], "my_hp": row[8], "hit_count": row[9], "super_used": row[10], "super_hits": row[11], "shield_active": row[12], "reward_g": row[13], "reward_s": row[14], "reward_r": row[15], "last_seen": row[16]}
    except Exception as e:
        print(f"get_fight error {e}"); return None

def save_fight_db(uid, data):
    try:
        conn = get_db(); cur = conn.cursor()
        if DATABASE_URL:
            cur.execute("INSERT INTO fights (uid, enemy, enemy_hp, enemy_max, enemy_dmg_min, enemy_dmg_max, enemy_img, enemy_name, my_hp, hit_count, super_used, super_hits, shield_active, reward_g, reward_s, reward_r, last_seen) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (uid) DO UPDATE SET enemy=EXCLUDED.enemy, enemy_hp=EXCLUDED.enemy_hp, enemy_max=EXCLUDED.enemy_max, enemy_dmg_min=EXCLUDED.enemy_dmg_min, enemy_dmg_max=EXCLUDED.enemy_dmg_max, enemy_img=EXCLUDED.enemy_img, enemy_name=EXCLUDED.enemy_name, my_hp=EXCLUDED.my_hp, hit_count=EXCLUDED.hit_count, super_used=EXCLUDED.super_used, super_hits=EXCLUDED.super_hits, shield_active=EXCLUDED.shield_active, reward_g=EXCLUDED.reward_g, reward_s=EXCLUDED.reward_s, reward_r=EXCLUDED.reward_r, last_seen=EXCLUDED.last_seen",
                (uid, data.get("enemy"), data.get("enemy_hp"), data.get("enemy_max"), data.get("enemy_dmg_min",2), data.get("enemy_dmg_max",4), data.get("enemy_img"), data.get("enemy_name"), data.get("my_hp"), data.get("hit_count",0), data.get("super_used",0), data.get("super_hits",0), bool(data.get("shield_active", False)), data.get("reward_g",0), data.get("reward_s",0), data.get("reward_r",0), int(data.get("last_seen", time.time()))))
        else:
            cur.execute("INSERT OR REPLACE INTO fights (uid, enemy, enemy_hp, enemy_max, enemy_dmg_min, enemy_dmg_max, enemy_img, enemy_name, my_hp, hit_count, super_used, super_hits, shield_active, reward_g, reward_s, reward_r, last_seen) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (uid, data.get("enemy"), data.get("enemy_hp"), data.get("enemy_max"), data.get("enemy_dmg_min",2), data.get("enemy_dmg_max",4), data.get("enemy_img"), data.get("enemy_name"), data.get("my_hp"), data.get("hit_count",0), data.get("super_used",0), data.get("super_hits",0), 1 if data.get("shield_active") else 0, data.get("reward_g",0), data.get("reward_s",0), data.get("reward_r",0), int(data.get("last_seen", time.time()))))
        conn.commit(); cur.close(); conn.close()
    except Exception as e: print(f"save_fight error {e}")

def clear_fight_db(uid):
    try:
        conn = get_db(); cur = conn.cursor()
        q = "DELETE FROM fights WHERE uid=%s" if DATABASE_URL else "DELETE FROM fights WHERE uid=?"
        cur.execute(q, (uid,)); conn.commit(); cur.close(); conn.close()
    except: pass

def apply_offline_damage(uid, fight):
    # Монстр бьёт каждые 8 секунд, пока игрока нет. Максимум 5 ударов за одно возвращение.
    if not fight: return fight
    now = int(time.time())
    last = int(fight.get("last_seen") or now)
    passed = now - last
    if passed < 8: return fight
    hits = min(passed // 8, 5)
    dmg_total = 0
    for _ in range(hits):
        dmg_total += random.randint(int(fight.get("enemy_dmg_min",2)), int(fight.get("enemy_dmg_max",4)))
    # если был щит - один удар блокируется
    if fight.get("shield_active"):
        dmg_total = max(0, dmg_total - random.randint(int(fight.get("enemy_dmg_min",2)), int(fight.get("enemy_dmg_max",4))))
        fight["shield_active"] = False
    fight["my_hp"] = max(0, int(fight.get("my_hp",20)) - dmg_total)
    fight["last_seen"] = now
    fight["_offline_dmg"] = dmg_total
    fight["_offline_hits"] = hits
    return fight

# === ЗАПРЕТ ВЫХОДА ИЗ БОЯ ===
@app.before_request
def block_exit_during_fight():
    # Разрешённые маршруты во время боя
    allowed = {"static_files", "fight", "fight_battle", "root", "login", "reg", None}
    # static
    if request.path.startswith("/static/"): return None
    if "uid" not in session: return None
    if request.endpoint in allowed: return None
    # если есть активный бой - обратно в бой
    f = get_fight_db(session.get("uid"))
    if f and int(f.get("enemy_hp", 1)) > 0 and int(f.get("my_hp", 1)) > 0:
        return redirect("/fight_battle")
    return None

def get_monsters():
    data = load_json("monsters")
    if not data: return DEFAULT_MONSTERS
    for kk in data:
        if "location" not in data[kk]: data[kk]["location"] = "promysel"
    return data

def save_monster(key, data):
    monsters = get_monsters()
    monsters[key] = data
    save_json("monsters", monsters)

def delete_monster(key):
    monsters = get_monsters()
    if key in monsters:
        del monsters[key]
        save_json("monsters", monsters)

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
        # если награда в бое из БД - берём оттуда
        f = get_fight_db(uid)
        if f:
            rg = int(f.get("reward_g", rg or 0)); rs = int(f.get("reward_s", rs or 0)); rr = int(f.get("reward_r", rr or 0))
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
        clear_fight_db(uid)
    except Exception as e: print(f"add_win error {e}")

def add_loss(uid):
    try:
        conn = get_db(); cur = conn.cursor()
        if DATABASE_URL: cur.execute("UPDATE players SET losses=COALESCE(losses,0)+1 WHERE id=%s",(uid,))
        else: cur.execute("UPDATE players SET losses=COALESCE(losses,0)+1 WHERE id=?",(uid,))
        conn.commit(); cur.close(); conn.close()
        clear_fight_db(uid)
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
            # если был незавершённый бой - сразу в бой
            if get_fight_db(uid):
                return redirect("/fight_battle")
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

@app.route("/map")
def map_page():
    if "uid" not in session: return redirect("/")
    links = ""
    for code, info in LOCATIONS.items():
        if code == "promysel": continue
        links += f'<a href="/loc/{code}" style="display:block;background:rgba(8,30,55,.92);border:2px solid #3aa0ff;padding:16px;color:#fff;text-decoration:none;font-size:20px;font-weight:bold;border-radius:8px;margin-bottom:10px">{info["name"]}</a>'
    html = f"""
    <div style="max-width:480px;margin:0 auto;padding:10px;min-height:100vh;background:#1a0e0a;color:#fff">
    <div style="background:rgba(8,30,55,.92);border:2px solid #4a7ba6;padding:12px;text-align:center"><h3 style="color:#fff;margin:0">📍 КАРТА МИРА</h3></div><br>
    {links}
    <a href="/game" style="display:block;background:#5a3e22;color:#fff;text-align:center;padding:14px;text-decoration:none;font-weight:bold;border-radius:8px">← Вернуться в игру</a></div>
    """
    return render_page(html, True)

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
    loc_names = {k: v["name"] for k,v in LOCATIONS.items()}
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
          <a href="/chat" style="background:rgba(10,38,66,.92);border:2px solid #4a7ba6;color:#fff;text-decoration:none;text-align:center;padding:10px 4px;font-weight:800;border-radius:6px">💬<br>Чат</a>
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
    # ВАЖНО: бой НЕ удаляем! Если вышел во время боя - бой продолжится, при следующем входе кикнет обратно в бой
    session.clear(); return redirect("/")

def _monster_cards(monsters, loc_code):
    cards = ""
    for key, cfg in monsters.items():
        if cfg.get("location", "promysel") != loc_code: continue
        cards += f'<div style="background:#3d2817;padding:6px;border-radius:6px;margin:10px 0"><div style="background:#f5e6c0;border:2px solid #5a3e22;border-radius:6px;padding:12px;display:flex;gap:12px;align-items:center"><img src="/static/{cfg["img"]}" style="width:55px;height:55px;object-fit:contain;background:#2b1a0e;border-radius:4px"><div style="flex:1"><b>{cfg["name"]}</b><br><small>HP: {cfg["hp"]} | Награда: {cfg["gold"]}🪙 {cfg["silver"]}⚪ {cfg["rubin"]}💎</small></div><a href="/fight/{key}" style="background:linear-gradient(#ff6b6b,#c92a2a);border:2px solid #5a3e22;border-radius:6px;padding:8px 16px;color:white;font-weight:bold;text-decoration:none">Атаковать</a></div></div>'
    return cards

@app.route("/promysel")
def promysel():
    if "uid" not in session: return redirect("/")
    MONSTERS = get_monsters()
    cur = session.get("current_loc", "lager")
    cards = _monster_cards(MONSTERS, cur)
    if not cards:
        cards = '<p style="text-align:center">В этой локации пока нет монстров. Админ может добавить!</p>'
    body = f'<div class="wrap" style="background:#e8d6a8;padding:10px"><h3 style="text-align:center">🌲 Промысел</h3>{cards}<a href="/game" class="btn-orange">← На главную</a></div>'
    return render_page(body, True)

@app.route("/loc/<code>")
def go_loc(code):
    if "uid" not in session: return redirect("/")
    if code == "promysel": return redirect("/promysel")
    if code not in LOCATIONS: return redirect("/game")
    session["current_loc"] = code
    loc_name = LOCATIONS[code]["name"]
    body = f'<div class="wrap" style="background:#e8d6a8;padding:10px"><h3 style="text-align:center">{loc_name}</h3><a href="/game" class="btn-orange">← На главную</a><a href="/map" class="btn-orange">📍 Карта</a></div>'
    return render_page(body, True)

@app.route("/fight/<monster>")
def fight(monster):
    if "uid" not in session: return redirect("/")
    # если уже есть бой - в него, новый не создаём
    existing = get_fight_db(session["uid"])
    if existing and int(existing.get("enemy_hp", 0)) > 0 and int(existing.get("my_hp", 0)) > 0:
        return redirect("/fight_battle")
    MONSTERS = get_monsters()
    p = get_player(session["uid"]); l, h, r, g, s_ = vals(p)
    cfg = MONSTERS.get(monster, MONSTERS["warrior"])
    # сохраняем бой в БД
    save_fight_db(session["uid"], {
        "enemy": monster, "enemy_hp": cfg.get("hp", 20), "enemy_max": cfg.get("hp", 20),
        "enemy_dmg_min": cfg.get("dmg", [2,4])[0], "enemy_dmg_max": cfg.get("dmg", [2,4])[1],
        "enemy_img": cfg.get("img", "ancient_warrior.png"), "enemy_name": cfg["name"],
        "my_hp": h, "hit_count": 0, "super_used": 0, "super_hits": 0, "shield_active": False,
        "reward_g": cfg.get("gold", 2), "reward_s": cfg.get("silver", 10), "reward_r": cfg.get("rubin", 0),
        "last_seen": int(time.time())
    })
    # для совместимости со старым кодом - дублируем в session
    session["enemy_type"] = cfg["name"]; session["enemy_hp"] = cfg.get("hp", 20); session["enemy_max"] = cfg.get("hp", 20)
    session["enemy_dmg"] = cfg.get("dmg", [2,4]); session["enemy_img"] = cfg.get("img", "ancient_warrior.png")
    session["my_hp"] = h; session["hit_count"] = 0; session["rewarded"] = False
    session["super_used"] = 0; session["super_hits"] = 0
    session["shield_active"] = False
    session["reward_g"] = cfg.get("gold", 2); session["reward_s"] = cfg.get("silver", 10); session["reward_r"] = cfg.get("rubin", 0)
    session.modified = True
    return redirect("/fight_battle")

@app.route("/fight_battle", methods=["GET", "POST"])
def fight_battle():
    if "uid" not in session: return redirect("/")
    uid = session["uid"]
    # бой берём из БД - он главный
    f = get_fight_db(uid)
    if not f:
        # нет боя в БД - пробуем старый session-бой, если его нет - в промысел
        if "enemy_hp" not in session: return redirect("/promysel")
        f = {"enemy": "warrior", "enemy_hp": session.get("enemy_hp", 20), "enemy_max": session.get("enemy_max", 20), "enemy_dmg_min": session.get("enemy_dmg", [2,4])[0], "enemy_dmg_max": session.get("enemy_dmg", [2,4])[1], "enemy_img": session.get("enemy_img", "ancient_warrior.png"), "enemy_name": session.get("enemy_type", "Древний Воин"), "my_hp": session.get("my_hp", 20), "hit_count": session.get("hit_count", 0), "super_used": session.get("super_used", 0), "super_hits": session.get("super_hits", 0), "shield_active": session.get("shield_active", False), "reward_g": session.get("reward_g", 0), "reward_s": session.get("reward_s", 0), "reward_r": session.get("reward_r", 0), "last_seen": int(time.time())}
        save_fight_db(uid, f)
    # === бой продолжается пока тебя нет ===
    f = apply_offline_damage(uid, f)
    if int(f.get("my_hp", 1)) <= 0:
        # умер пока был офлайн
        add_loss(uid)
        # clear уже в add_loss, но session тоже чистим
        session.pop("enemy_hp", None)
        return redirect("/game")
    # сохраняем обновлённое время
    f["last_seen"] = int(time.time())
    save_fight_db(uid, f)
    # синхронизируем session для шаблона
    session["enemy_hp"] = int(f["enemy_hp"]); session["my_hp"] = int(f["my_hp"]); session["hit_count"] = int(f.get("hit_count",0))
    session["super_used"] = int(f.get("super_used",0)); session["super_hits"] = int(f.get("super_hits",0)); session["shield_active"] = bool(f.get("shield_active"))
    session["reward_g"] = int(f.get("reward_g",0)); session["reward_s"] = int(f.get("reward_s",0)); session["reward_r"] = int(f.get("reward_r",0))
    session["enemy_type"] = f.get("enemy_name"); session["enemy_img"] = f.get("enemy_img"); session["enemy_max"] = int(f.get("enemy_max",20))

    p = get_player(uid); lvl, my_max_hp, rubin, gold, silver = vals(p)
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        m = data.get("m") or request.form.get("m", "hit")
        # === ВЫХОД ИЗ БОЯ ЗАПРЕЩЁН ===
        if m == "run":
            return jsonify({"status": "blocked", "msg": "⛔ Из боя нельзя выйти! Бейся до конца!", "enemy_hp": int(f["enemy_hp"]), "my_hp": int(f["my_hp"]), "finished": False})
        cur_my = int(f["my_hp"]); cur_en = int(f["enemy_hp"]); hit_cnt = int(f.get("hit_count",0))
        super_used = int(f.get("super_used",0)); super_hits = int(f.get("super_hits",0))
        dmg = 0; edmg = 0
        def enemy_hit():
            nonlocal cur_my
            if f.get("shield_active"):
                f["shield_active"] = False
                return 0
            emin, emax = int(f.get("enemy_dmg_min",2)), int(f.get("enemy_dmg_max",4))
            d = random.randint(emin, emax)
            cur_my = max(0, cur_my - d)
            return d
        if m == "shield" and cur_my > 0 and cur_en > 0:
            f["shield_active"] = True
            edmg = enemy_hit()
        elif m == "enemy_turn" and cur_my > 0 and cur_en > 0:
            # ТОЛЬКО ход монстра, отдельно от твоего
            if f.get("shield_active"):
                edmg = 0
                f["shield_active"] = False
            else:
                edmg = random.randint(int(f.get("enemy_dmg_min",2)), int(f.get("enemy_dmg_max",4)))
                cur_my = max(0, cur_my - edmg)
            dmg = 0
        elif m == "hit" and cur_my > 0 and cur_en > 0:
            # ТОЛЬКО твой ход, монстр пока НЕ бьёт
                dmg = random.randint(3, 7); cur_en = max(0, cur_en - dmg); hit_cnt += 1; super_hits += 1
                edmg = 0
        elif m == "super" and cur_my > 0 and cur_en > 0 and super_used < 4 and super_hits >= 5:
            # ТОЛЬКО твой супер, без ответки
            dmg = random.randint(10, 18); cur_en = max(0, cur_en - dmg); super_used += 1; super_hits = 0
            edmg = 0
        f["enemy_hp"] = cur_en; f["my_hp"] = cur_my; f["hit_count"] = hit_cnt
        f["super_used"] = super_used; f["super_hits"] = super_hits; f["last_seen"] = int(time.time())
        save_fight_db(uid, f)
        session["enemy_hp"] = cur_en; session["my_hp"] = cur_my; session["hit_count"] = hit_cnt
        session["super_used"] = super_used; session["super_hits"] = super_hits; session.modified = True
        need_for_next = 0 if super_used >= 4 else (5 - super_hits)
        finished = False; is_win = False
        if cur_en <= 0:
            # победа - очищаем бой, теперь можно выйти
            session["reward_g"] = int(f.get("reward_g",0)); session["reward_s"] = int(f.get("reward_s",0)); session["reward_r"] = int(f.get("reward_r",0))
            add_win(uid); session["rewarded"] = True; finished = True; is_win = True
        elif cur_my <= 0:
            add_loss(uid); session["rewarded"] = True; finished = True; is_win = False
        return jsonify({"enemy_hp": cur_en, "enemy_max": int(f.get("enemy_max",20)), "my_hp": cur_my, "my_max": my_max_hp, "hit_cnt": hit_cnt, "last_dmg": dmg, "edmg": edmg, "finished": finished, "is_win": is_win, "reward_g": int(f.get("reward_g",0)), "reward_s": int(f.get("reward_s",0)), "reward_r": int(f.get("reward_r",0)), "super_used": super_used, "need_for_next": need_for_next})
    cur_enemy_hp = int(f["enemy_hp"]); enemy_max_hp = int(f.get("enemy_max",20)); cur_my_hp = int(f["my_hp"]); hit_cnt = int(f.get("hit_count",0))
    enemy_name = f.get("enemy_name", "Древний Воин"); enemy_img = f.get("enemy_img", "ancient_warrior.png")
    super_used = int(f.get("super_used",0)); super_hits = int(f.get("super_hits",0))
    need_for_next = 0 if super_used >= 4 else (5 - super_hits)
    my_per = int(cur_my_hp * 100 / my_max_hp) if my_max_hp else 0; enemy_per = int(cur_enemy_hp * 100 / enemy_max_hp) if enemy_max_hp else 0
    return render_template("battle.html",
        lvl=lvl, enemy_type=enemy_name, player_img="barbarian_game_size.png",
        enemy_img=enemy_img, my_hp=cur_my_hp, my_max_hp=my_max_hp, my_per=my_per,
        enemy_hp=cur_enemy_hp, enemy_max=enemy_max_hp, enemy_per=enemy_per,
        hit_cnt=hit_cnt, super_used=super_used, need_for_next=need_for_next)

BAD_WORDS = ["бля", "хуй", "пизд", "сука", "ебан", "нахуй", "fuck", "shit"]
CHAT_SPAM = {}
def chat_check(uid, text):
    if "http://" in text or "https://" in text or "t.me/" in text or "www." in text:
        return False, "Ссылки в чате запрещены! Мут 10 мин"
    low = text.lower()
    for w in BAD_WORDS:
        if w in low: return False, "Мат в чате запрещён!"
    now = time.time()
    lst = CHAT_SPAM.get(uid, [])
    lst = [t for t in lst if now - t < 10]
    lst.append(now); CHAT_SPAM[uid] = lst
    if len(lst) >= 5: return False, "Спам! Мут 10 мин"
    return True, "ok"

@app.route("/chat")
def chat_page():
    if "uid" not in session: return redirect("/")
    p = get_player(session["uid"])
    nick = p.get("name","Воин") if isinstance(p, dict) else "Воин"
    html = f'''
    <style>
    .chat-wrap{{max-width:480px;margin:0 auto;min-height:100dvh;background:#0a1e35;padding:10px;box-sizing:border-box;display:flex;flex-direction:column}}
    .chat-tabs{{display:flex;gap:6px;margin-bottom:8px}}
    .chat-tab{{flex:1;text-align:center;padding:10px;background:#122c4d;color:#fff;border:2px solid #4a7ba6;border-radius:8px;font-weight:900;cursor:pointer}}
    .chat-tab.active{{background:#e8c268;color:#000;border-color:#e8c268}}
    #chatBox{{flex:1;background:#fdf6c8;border:2px solid #8a6a3d;border-radius:10px;padding:10px;overflow-y:auto;min-height:320px;max-height:420px}}
    .msg{{margin-bottom:8px;background:#fff;padding:6px 8px;border-radius:8px;border:1px solid #e8d6a8}}
    .msg b{{color:#0a1e35}} .msg small{{color:#888}}
    </style>
    <div class="chat-wrap">
      <div style="background:rgba(8,30,55,.92);border:2px solid #4a7ba6;padding:10px;text-align:center;color:#fff;font-weight:900;border-radius:8px">💬 ЧАТ — {nick}</div>
      <div class="chat-tabs">
        <div class="chat-tab active" onclick="setTab('all',this)">🌍 Общий</div>
        <div class="chat-tab" onclick="setTab('trade',this)">💰 Торговля</div>
        <div class="chat-tab" onclick="setTab('clan',this)">🛡️ Клан</div>
      </div>
      <div id="chatBox">Загрузка...</div>
      <div style="display:flex;gap:6px;margin-top:8px">
        <input id="chatInput" placeholder="Написать..." style="flex:1;padding:12px;border-radius:8px;border:2px solid #8a6a3d;background:#fdf6c8">
        <button onclick="sendChat()" style="padding:12px 16px;background:#e8c268;border:2px solid #5a3e22;border-radius:8px;font-weight:900">➤</button>
      </div>
      <a href="/game" style="display:block;text-align:center;color:#fff;margin-top:10px;text-decoration:none;font-weight:bold">← На главную</a>
    </div>
    <script>
    let curTab='all';
    function setTab(t,el){{curTab=t; document.querySelectorAll('.chat-tab').forEach(x=>x.classList.remove('active')); el.classList.add('active'); loadChat();}}
    async function loadChat(){{
      let res = await fetch('/api/chat?tab='+curTab); let data = await res.json();
      let box = document.getElementById('chatBox');
      if(!data.length){{ box.innerHTML='<p style="text-align:center;color:#888">Пока пусто. Напиши первым!</p>'; return; }}
      box.innerHTML = data.map(m=>`<div class="msg"><b>${{m.name}}</b> <small>${{m.time}} • ${{m.lvl}} ур.</small><br>${{m.text}}</div>`).join('');
      box.scrollTop = box.scrollHeight;
    }}
    async function sendChat(){{
      let inp = document.getElementById('chatInput'); let txt = inp.value.trim(); if(!txt) return;
      let res = await fetch('/api/chat',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{tab:curTab,text:txt}})}});
      let d = await res.json();
      if(!d.ok){{ alert(d.msg); return; }}
      inp.value=''; loadChat();
    }}
    document.getElementById('chatInput').addEventListener('keydown',e=>{{if(e.key==='Enter') sendChat();}});
    setInterval(loadChat, 3000); loadChat();
    </script>
    '''
    return render_page(html, False)

@app.route("/api/chat", methods=["GET","POST"])
def api_chat():
    if "uid" not in session: return jsonify([])
    if request.method == "GET":
        tab = request.args.get("tab","all")
        try:
            conn=get_db(); cur=conn.cursor()
            q = "SELECT c.text, c.created_at, p.name, p.level FROM chat_messages c JOIN players p ON p.id=c.uid WHERE c.tab=%s ORDER BY c.id DESC LIMIT 50" if DATABASE_URL else "SELECT c.text, c.created_at, p.name, p.level FROM chat_messages c JOIN players p ON p.id=c.uid WHERE c.tab=? ORDER BY c.id DESC LIMIT 50"
            cur.execute(q,(tab,)); rows=cur.fetchall(); cur.close(); conn.close()
            out=[]
            for row in reversed(rows):
                txt = row["text"] if isinstance(row,dict) else row[0]
                tm = str(row["created_at"] if isinstance(row,dict) else row[1])[:16]
                nm = row["name"] if isinstance(row,dict) else row[2]
                lvl = row["level"] if isinstance(row,dict) else row[3]
                out.append({"text":txt,"time":tm,"name":nm,"lvl":lvl})
            return jsonify(out)
        except: return jsonify([])
    data = request.get_json(silent=True) or {}
    text = str(data.get("text","")).strip()[:200]
    tab = data.get("tab","all")
    if not text: return jsonify({"ok":False,"msg":"Пустое сообщение"})
    ok, msg = chat_check(session["uid"], text)
    if not ok: return jsonify({"ok":False,"msg":msg})
    try:
        conn=get_db(); cur=conn.cursor()
        if DATABASE_URL: cur.execute("INSERT INTO chat_messages (uid, tab, text) VALUES (%s,%s,%s)",(session["uid"],tab,text))
        else: cur.execute("INSERT INTO chat_messages (uid, tab, text) VALUES (?,?,?)",(session["uid"],tab,text))
        conn.commit(); cur.close(); conn.close()
        return jsonify({"ok":True})
    except Exception as e: return jsonify({"ok":False,"msg":str(e)})

# ===== МАГАЗИН ИЗ data/shop.json - НОВЫЙ =====
@app.route("/shop")
def shop():
    if "uid" not in session: return redirect("/")
    p = get_player(session["uid"]); l, h, r, g, s = vals(p)
    cur_loc = session.get("current_loc", "lager")
    cur_loc_name = LOCATIONS.get(cur_loc, {}).get("name", "Лагерь")
    html = f'''
    <style>
    .shop-wrap{{max-width:480px;margin:0 auto;min-height:100dvh;background:linear-gradient(180deg,#0a1e35 0%,#122c4d 40%,#1a0e0a 100%);padding:12px;box-sizing:border-box}}
    .shop-top{{background:rgba(8,30,55,.92);border:2px solid #4a7ba6;border-radius:10px;padding:10px;text-align:center;color:#fff;font-weight:900;font-size:20px}}
    .shop-balance{{display:flex;justify-content:space-around;background:rgba(8,30,55,.88);border:2px solid #4a7ba6;border-radius:10px;padding:8px;margin:10px 0;color:#fff;font-weight:900}}
    .shop-btn{{display:flex;align-items:center;justify-content:center;gap:10px;width:100%;text-decoration:none;color:#fff;font-weight:900;font-size:22px;padding:20px 10px;margin-bottom:8px;border-radius:10px;border:2px solid #000;box-shadow:0 4px 0 rgba(0,0,0,.5);text-shadow:0 2px 4px rgba(0,0,0,.7)}}
    .c-weapon{{background:linear-gradient(180deg,#3a1a1a,#7a1f1f);border-color:#ffb84d}}
    .c-armor{{background:linear-gradient(180deg,#1a2a3a,#2f5a7a);border-color:#7ab8ff}}
    .c-potion{{background:linear-gradient(180deg,#1a3a1a,#2a7a2a);border-color:#7aff8a}}
    .c-amulet{{background:linear-gradient(180deg,#3a2a4a,#7a3ab8);border-color:#d8a7ff}}
    .c-misc{{background:linear-gradient(180deg,#3a331a,#8a7a2a);border-color:#ffe97a}}
    .c-auction{{background:linear-gradient(180deg,#3a1a2a,#a62a5a);border-color:#ff7ab8}}
    .c-sell{{background:linear-gradient(180deg,#222,#555);border-color:#ccc}}
    .c-char{{background:linear-gradient(180deg,#4a2a0a,#c98a2a);border-color:#ffcc00}}
    </style>
    <div class="shop-wrap">
      <div class="shop-top">🛒 МАГАЗИН — {cur_loc_name}</div>
      <div class="shop-balance"><span>💎 {r}</span><span>🪙 {g}</span><span>⚪ {s}</span></div>
      <a href="/shop/weapon" class="shop-btn c-weapon">🗡️ Оружие</a>
      <a href="/shop/armor" class="shop-btn c-armor">🛡️ Броня</a>
      <a href="/shop/potion" class="shop-btn c-potion">🧪 Зелья и Свитки</a>
      <a href="/shop/amulet" class="shop-btn c-amulet">🔮 Амулеты</a>
      <a href="/shop/misc" class="shop-btn c-misc">📦 Разное</a>
      <a href="/shop/auction" class="shop-btn c-auction">🏆 Аукцион</a>
      <a href="/shop/sell" class="shop-btn c-sell">💰 Продать</a>
      <a href="/shop/chars" class="shop-btn c-char">🧝 Персонажи</a>
      <a href="/game" style="display:block;background:#0a1e35;border:2px solid #e8c268;color:#f5e6b0;text-align:center;padding:14px;text-decoration:none;font-weight:900;border-radius:10px;margin-top:6px">← На главную</a>
    </div>'''
    return render_page(html, False)

@app.route("/shop/<cat>")
def shop_cat(cat):
    if "uid" not in session: return redirect("/")
    names={"weapon":"🗡️ Оружие","armor":"🛡️ Броня","potion":"🧪 Зелья и Свитки","amulet":"🔮 Амулеты","misc":"📦 Разное","auction":"🏆 Аукцион","sell":"💰 Продать","chars":"🧝 Персонажи"}
    title=names.get(cat,"Магазин")
    sort = request.args.get("sort","none")
    cur_loc = session.get("current_loc","lager")
    shop_data = load_json("shop")
    items = shop_data.get(cat, [])

    # 1. ФИЛЬТР ПО ЛОКАЦИИ - в каждой локации свой товар
    filtered = []
    for it in items:
        loc = it.get("location")
        if loc and loc != cur_loc:
            continue
        filtered.append(it)
    items = filtered

    # 2. СОРТИРОВКА
    if sort == "damage":
        items = sorted(items, key=lambda x: -int(x.get("damage",0)))
    elif sort == "armor":
        items = sorted(items, key=lambda x: -int(x.get("armor",0)))
    elif sort == "dodge":
        items = sorted(items, key=lambda x: -int(x.get("dodge",0)))
    elif sort == "price":
        items = sorted(items, key=lambda x: int(x.get("gold",0))*100 + int(x.get("silver",0)))

    if not items:
        cards = '<div style="background:#fdf6c8;border:2px solid #8a6a3d;border-radius:10px;padding:20px">В этой локации пока нет товаров этой категории.<br>Сходи в другую локацию или добавь товар в shop.json с location = '+cur_loc+'</div>'
    else:
        cards = '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px">'
        for it in items:
            price = ""
            if it.get("gold"): price += f'{it["gold"]}🪙 '
            if it.get("silver"): price += f'{it["silver"]}⚪ '
            if it.get("rubin"): price += f'{it["rubin"]}💎 '
            stats = ""
            if it.get("damage"): stats += f'⚔️{it["damage"]} '
            if it.get("armor"): stats += f'🛡️{it["armor"]} '
            if it.get("dodge"): stats += f'💨{it["dodge"]} '
            lvl = it.get("level",1)
            icon = it.get("icon","📦")
            cards += f'''
            <div style="background:linear-gradient(#e8d6a8,#d9be85);border:2px solid #5a3e22;border-radius:10px;padding:8px;text-align:center;position:relative;color:#3d2817">
                <div style="position:absolute;top:4px;left:6px;font-size:12px">⭐{lvl}</div>
                <div style="font-size:38px;margin:14px 0 4px">{icon}</div>
                <div style="font-size:12px;font-weight:bold;min-height:28px">{it.get("name","Товар")}</div>
                <div style="font-size:11px;color:#5a3e22;min-height:16px">{stats if stats else it.get("desc","")}</div>
                <div style="font-weight:bold;margin:4px 0;font-size:12px">{price or "Бесплатно"}</div>
                <form method="post" action="/shop/buy/{cat}/{it.get("id","")}"><button style="width:100%;background:#ff9c00;color:#fff;padding:6px;border:0;border-radius:6px;font-weight:bold">Купить</button></form>
            </div>'''
        cards += '</div>'

    sorts_html = f'''
    <div style="display:flex;gap:6px;flex-wrap:wrap;justify-content:center;margin:10px 0">
      <a href="/shop/{cat}?sort=none" style="padding:7px 10px;background:{'#ff9c00' if sort=='none' else '#5a3e22'};color:#fff;border-radius:8px;text-decoration:none;font-size:13px">Нет</a>
      <a href="/shop/{cat}?sort=damage" style="padding:7px 10px;background:{'#ff9c00' if sort=='damage' else '#5a3e22'};color:#fff;border-radius:8px;text-decoration:none;font-size:13px">⚔️ Урон</a>
      <a href="/shop/{cat}?sort=dodge" style="padding:7px 10px;background:{'#ff9c00' if sort=='dodge' else '#5a3e22'};color:#fff;border-radius:8px;text-decoration:none;font-size:13px">💨 Уворот</a>
      <a href="/shop/{cat}?sort=armor" style="padding:7px 10px;background:{'#ff9c00' if sort=='armor' else '#5a3e22'};color:#fff;border-radius:8px;text-decoration:none;font-size:13px">🛡️ Броня</a>
      <a href="/shop/{cat}?sort=price" style="padding:7px 10px;background:{'#ff9c00' if sort=='price' else '#5a3e22'};color:#fff;border-radius:8px;text-decoration:none;font-size:13px">🪙 Цена</a>
    </div>'''
    msg = request.args.get("msg","")
    msg_html = f'<p style="color:green;font-weight:bold">{msg}</p>' if msg else ""
    loc_name = LOCATIONS.get(cur_loc,{}).get("name",cur_loc)
    return render_page(f'<div class="wrap" style="padding:15px;text-align:center"><h2>{title}</h2><p style="font-size:13px;color:#666">📍 {loc_name} — только товар этой локации</p>{msg_html}{sorts_html}{cards}<a href="/shop" class="btn-orange">← К магазину</a></div>', True)

@app.route("/shop/buy/<cat>/<item_id>", methods=["POST"])
def shop_buy(cat, item_id):
    if "uid" not in session: return redirect("/")
    shop_data = load_json("shop")
    items = shop_data.get(cat, [])
    item = next((x for x in items if str(x.get("id")) == str(item_id)), None)
    if not item: return redirect(f"/shop/{cat}?msg=Товар не найден")
    # Проверка локации - нельзя купить чужой товар через прямую ссылку
    cur_loc = session.get("current_loc","lager")
    if item.get("location") and item.get("location") != cur_loc:
        return redirect(f"/shop/{cat}?msg=Этот товар не продается в этой локации!")
    p = get_player(session["uid"]); l, h, r, g, s = vals(p)
    need_g = int(item.get("gold") or 0); need_s = int(item.get("silver") or 0); need_r = int(item.get("rubin") or 0)
    if g < need_g or s < need_s or r < need_r:
        return redirect(f"/shop/{cat}?msg=Не хватает денег!")
    try:
        conn=get_db(); cur=conn.cursor()
        if DATABASE_URL: cur.execute("UPDATE players SET gold=gold-%s, silver=silver-%s, rubin=rubin-%s WHERE id=%s",(need_g, need_s, need_r, session["uid"]))
        else: cur.execute("UPDATE players SET gold=gold-?, silver=silver-?, rubin=rubin-? WHERE id=?",(need_g, need_s, need_r, session["uid"]))
        conn.commit(); cur.close(); conn.close()
    except Exception as e: return redirect(f"/shop/{cat}?msg=Ошибка: {e}")
    return redirect(f"/shop/{cat}?msg=✅ Куплено: {item.get('name','')}")

@app.route("/hero")
def hero():
    if "uid" not in session: return redirect("/")
    p=get_player(session["uid"]); l,hr,r,g,s=vals(p)
    nick = p.get("name","Воин") if isinstance(p,dict) or hasattr(p,'get') else "Воин"
    exp = int(p.get("exp",0)) if isinstance(p,dict) or hasattr(p,'get') else 0
    wins = int(p.get("wins",0)) if isinstance(p,dict) or hasattr(p,'get') else 0
    losses = int(p.get("losses",0)) if isinstance(p,dict) or hasattr(p,'get') else 0
    admin_tag = " 👑 ADMIN" if is_admin() else ""
    hp = l*10; st = l; exp_need = l*100
    return render_page(f'''<div class="wrap" style="padding:15px">
    <h2 style="text-align:center">🧝 Герой {nick}{admin_tag}</h2>
    <p style="text-align:center">Уровень {l} / 21 | Опыт {exp} / {exp_need} | Победы {wins} / Поражения {losses}</p>
    <div style="background:#e8d5a3;color:#000;padding:15px;border-radius:10px;font-size:18px;line-height:2">
      <div style="display:flex;justify-content:space-between"><span>Жизнь:</span><span>❤️ {hp}</span></div>
      <div style="display:flex;justify-content:space-between"><span>Урон:</span><span>🗡️ {st}...{st}</span></div>
      <div style="display:flex;justify-content:space-between"><span>Точность:</span><span>🎯 {st}...{st}</span></div>
      <div style="display:flex;justify-content:space-between"><span>Броня:</span><span>🛡️ {st}</span></div>
      <div style="display:flex;justify-content:space-between"><span>Уворот:</span><span>💨 {st}...{st}</span></div>
      <div style="display:flex;justify-content:space-between"><span>Оглушение:</span><span>🥢 {st}...{st}</span></div>
      <div style="display:flex;justify-content:space-between"><span>Блок:</span><span>🔰 {st}</span></div>
    </div>
    <p style="text-align:center;color:#aaa;font-size:13px">Слава и Звания — скоро</p>
    <br><div style="text-align:center"><a href="/game"><button>⬅ Назад</button></a></div>
    </div>''')

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
        cur.execute("SELECT * FROM players ORDER BY wins DESC, level DESC LIMIT 50")
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
        cur.execute("SELECT * FROM players ORDER BY level DESC, wins DESC")
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
    if request.method=="POST":
        try: amount=int(request.form.get("amount",0))
        except: amount=0
        action=request.form.get("action")
        if amount>0:
            conn=get_db(); cur=conn.cursor()
            if action=="exchange" and r>=amount:
                q = "UPDATE players SET rubin=rubin-%s, gold=gold+%s WHERE id=%s" if DATABASE_URL else "UPDATE players SET rubin=rubin-?, gold=gold+? WHERE id=?"
                cur.execute(q,(amount, amount*500, session["uid"]))
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
    try:
        conn=get_db(); cur=conn.cursor()
        q = "SELECT * FROM players WHERE id!=%s ORDER BY level DESC" if DATABASE_URL else "SELECT * FROM players WHERE id!=? ORDER BY level DESC"
        cur.execute(q,(session["uid"],))
        rows=cur.fetchall(); cur.close(); conn.close()
    except: rows=[]
    items=""
    for r in rows:
        nm = r["name"] if isinstance(r,dict) else r[1]
        lvl = r["level"] if isinstance(r,dict) else r[8]
        gold = r["gold"] if isinstance(r,dict) else r[4]
        items+=f'<div style="border:1px solid #444;padding:10px;margin:8px;border-radius:10px">{nm} — Ур. {lvl} | 🪙 {gold}<br><a href="/game"><button>⚔️ Атаковать (скоро)</button></a></div>'
    if not items: items='<p>Пока никого нет</p>'
    return render_page(f'<div class="wrap" style="padding:15px;text-align:center"><h2>⚔️ PVP — Выбери соперника</h2>{items}<br><a href="/game"><button>⬅ Назад</button></a></div>')

@app.route("/quests")
def quests():
    if "uid" not in session: return redirect("/")
    return render_page('<div class="wrap" style="padding:15px"><h2 style="text-align:center">📜 Задания</h2><div style="background:#fdf6c8;border:2px solid #8a6a3d;border-radius:10px;padding:14px;margin:10px 0">⚔️ Победи 3 монстра - Награда: 10🪙</div><div style="background:#fdf6c8;border:2px solid #8a6a3d;border-radius:10px;padding:14px;margin:10px 0">🏆 Дойди до 5 уровня - Награда: 5💎</div><a href="/game" class="btn-orange">← На главную</a></div>', True)

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
                    save_monster(key, m); msg = f"✅ Монстр {m['name']} обновлён! (сохранено в data/monsters.json)"
            elif action == "add_monster":
                key = request.form.get("m_key","").strip().lower().replace(" ","_")
                monsters = get_monsters()
                if key and key not in monsters:
                    new_m = {
                        "name": request.form.get("m_name","Новый монстр"),
                        "img": request.form.get("m_img","ancient_warrior.png"),
                        "hp": int(request.form.get("m_hp") or 50),
                        "dmg": [int(request.form.get("m_dmg_min") or 2), int(request.form.get("m_dmg_max") or 5)],
                        "gold": int(request.form.get("m_gold") or 2),
                        "silver": int(request.form.get("m_silver") or 10),
                        "rubin": int(request.form.get("m_rubin") or 0),
                        "location": request.form.get("m_location","promysel")
                    }
                    save_monster(key, new_m)
                    msg = f"✅ Монстр {new_m['name']} добавлен в {LOCATIONS.get(new_m['location'],{}).get('name', new_m['location'])}"
                else: msg = "❌ Такой ключ уже есть или пустой"
            elif action == "delete_monster":
                key = request.form.get("mkey")
                delete_monster(key); msg = f"✅ Монстр {key} удалён из файла"
            elif action == "move_monster":
                key = request.form.get("mkey")
                monsters = get_monsters()
                if key in monsters:
                    monsters[key]["location"] = request.form.get("new_location","promysel")
                    save_monster(key, monsters[key]); msg = f"✅ {monsters[key]['name']} перемещён в {monsters[key]['location']}"
        except Exception as e: msg = f"❌ Ошибка: {e}"
        cur.close(); conn.close()
    conn=get_db(); cur=conn.cursor()
    cur.execute("SELECT * FROM players ORDER BY id")
    players = cur.fetchall(); cur.close(); conn.close()
    monsters = get_monsters()
    loc_options = "".join([f'<option value="{k}">{v["name"]}</option>' for k,v in LOCATIONS.items()])
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
        loc_sel = "".join([f'<option value="{k}" {"selected" if m.get("location","promysel")==k else ""}>{v["name"]}</option>' for k,v in LOCATIONS.items()])
        monsters_html += f'''
        <form method="post" style="background:#fff3cd;border:2px solid #c9a45c;border-radius:10px;padding:12px;margin:10px 0">
          <b>👹 {m["name"]} ({key}) — 📍 {LOCATIONS.get(m.get("location","promysel"),dict()).get("name","?")}</b><br>
          <input type="hidden" name="action" value="edit_monster">
          <input type="hidden" name="mkey" value="{key}">
          HP монстра: <input name="m_hp" type="number" value="{m["hp"]}">
          Награда Золото 🪙: <input name="m_gold" type="number" value="{m["gold"]}">
          Награда Серебро ⚪: <input name="m_silver" type="number" value="{m["silver"]}">
          Награда Рубины 💎: <input name="m_rubin" type="number" value="{m["rubin"]}">
          Урон мин: <input name="m_dmg_min" type="number" value="{m["dmg"][0]}">
          Урон макс: <input name="m_dmg_max" type="number" value="{m["dmg"][1]}">
          <button class="btn-orange" style="margin:5px auto">💾 Сохранить монстра</button>
        </form>
        <form method="post" style="background:#e8f5ff;border:2px solid #4a7ba6;border-radius:10px;padding:10px;margin:-5px 0 10px">
          <input type="hidden" name="action" value="move_monster">
          <input type="hidden" name="mkey" value="{key}">
          Переместить в: <select name="new_location">{loc_sel}</select>
          <button class="btn-orange" style="margin:5px auto">📍 Переместить</button>
        </form>
        <form method="post" onsubmit="return confirm('Удалить монстра?')" style="margin:-5px 0 10px">
          <input type="hidden" name="action" value="delete_monster">
          <input type="hidden" name="mkey" value="{key}">
          <button style="width:100%;padding:8px;background:#c92a2a;color:#fff;border:0;border-radius:8px;font-weight:bold">🗑️ Удалить монстра</button>
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
      <h3>👹 Добавить монстра в локацию</h3>
      <form method="post" style="background:#fff3cd;border:2px solid #c9a45c;border-radius:10px;padding:12px">
        <input type="hidden" name="action" value="add_monster">
        Ключ (англ, без пробелов): <input name="m_key" placeholder="naprimer: volk" required>
        Имя: <input name="m_name" placeholder="Волк" required>
        Картинка: <input name="m_img" value="ancient_warrior.png">
        HP: <input name="m_hp" type="number" value="50">
        Урон мин: <input name="m_dmg_min" type="number" value="2">
        Урон макс: <input name="m_dmg_max" type="number" value="5">
        Золото: <input name="m_gold" type="number" value="2">
        Серебро: <input name="m_silver" type="number" value="10">
        Рубины: <input name="m_rubin" type="number" value="0">
        Локация: <select name="m_location">{loc_options}</select>
        <button class="btn-orange">➕ СОЗДАТЬ МОНСТРА</button>
      </form>
      <h3>👹 Монстры по локациям</h3>
      {monsters_html}
      <h3>👥 Все игроки</h3>
      {players_html}
      <a href="/game" class="btn-orange">← На главную</a>
    </div>'''
    return render_page(html, False)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)