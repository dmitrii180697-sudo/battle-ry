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
    if "hit_count" not in session:
        session["hit_count"]=0

    if request.method=="POST":
        m=request.form.get("m")
        if m=="run":
            return redirect("/promysel")
        if m=="hit" and session["my_hp"]>0 and session["enemy_hp"]>0:
            dmg=random.randint(3,7)
            session["enemy_hp"]-=dmg
            session["hit_count"]=session.get("hit_count",0)+1
            session["last_dmg"]=dmg
            session["last_who"]="enemy"
        if m=="super" and session.get("hit_count",0)>=5:
            dmg=random.randint(10,18)
            session["enemy_hp"]-=dmg
            session["hit_count"]=0
            session["last_dmg"]=dmg
            session["last_who"]="enemy"
        if session["enemy_hp"]>0 and session["my_hp"]>0 and m in ["hit","super"]:
            try:
                emin,emax=session.get("enemy_dmg",[2,5])
                ed=random.randint(int(emin),int(emax))
            except:
                ed=random.randint(2,5)
            session["my_hp"]-=ed
            session["last_edmg"]=ed
        if session["my_hp"]<=0 and not session.get("rewarded"):
            add_loss(session["uid"])
            session["rewarded"]=True
        if session["enemy_hp"]<=0 and not session.get("rewarded"):
            add_win(session["uid"])
            add_reward(session["uid"], session.get("reward_g",0), session.get("reward_s",0), session.get("reward_r",0))
            session["rewarded"]=True
        return redirect("/fight_battle")

    cur_enemy_hp=max(0, session.get("enemy_hp",0))
    cur_my_hp=max(0, session.get("my_hp",0))
    enemy_max_hp=session.get("enemy_max",20)
    enemy_per=int(cur_enemy_hp*100/enemy_max_hp) if enemy_max_hp else 0
    my_per=int(cur_my_hp*100/20) if cur_my_hp else 0
    enemy_img=session.get("enemy_img","ancient_warrior.png")
    enemy_name=session.get("enemy_name","Древний воин")
    hit_cnt=session.get("hit_count",0)
    is_super=hit_cnt>=5
    camp_bg="camp.jpg"
    super_label="x5 ГОТОВ!" if is_super else f"{hit_cnt}/5"
    opac=1 if is_super else 0.4
    last_dmg=session.get("last_dmg",0)

    if cur_enemy_hp<=0 or cur_my_hp<=0:
        is_win=cur_enemy_hp<=0
        title="ПОБЕДА!" if is_win else "ПОРАЖЕНИЕ!"
        col="#00ff66" if is_win else "#ff3333"
        reward_text=""
        if is_win:
            reward_text=f"<p style='font-weight:900'>+{session.get('reward_g',0)} 🪙 +{session.get('reward_s',0)} ⚪ +{session.get('reward_r',0)} 💎</p>"
        html=f'<div style="min-height:100vh;background:#1a0e0a;display:flex;align-items:center;justify-content:center"><div style="background:#f5e6c0;border:3px solid #5a3e22;border-radius:16px;padding:20px;text-align:center"><h1 style="color:{col}">{title}</h1>{reward_text}<a href="/game" style="display:inline-block;background:#8b5a2b;color:#fff;padding:10px 20px;border-radius:10px;text-decoration:none;font-weight:900;margin-top:10px">В ЛАГЕРЬ</a></div></div>'
        return render_template_string(html)

    html=f'''
    <style>
    @keyframes attackLeft {{0%{{transform:translateX(0)}} 35%{{transform:translateX(40px)}} 100%{{transform:translateX(0)}} }}
    @keyframes shakeRight {{0%,100%{{transform:translateX(0)}} 20%{{transform:translateX(-7px)}} 40%{{transform:translateX(7px)}} 60%{{transform:translateX(-4px)}} 80%{{transform:translateX(4px)}} }}
    @keyframes dmgPop {{0%{{transform:translate(-50%,-50%) scale(0); opacity:0}} 20%{{transform:translate(-50%,-90%) scale(1.5); opacity:1}} 100%{{transform:translate(-50%,-140%) scale(1); opacity:0}} }}
    .anim-attack {{animation:attackLeft 0.32s ease}}
    .anim-shake {{animation:shakeRight 0.32s ease}}
    .dmg {{position:absolute;top:45%;left:50%;z-index:10;color:#ffeb00;font-weight:900;font-size:40px;text-shadow:2px 2px 0 #000;opacity:0;pointer-events:none}}
    .dmg.show {{animation:dmgPop 0.7s ease forwards}}
    </style>

    <div style="max-width:420px;margin:0 auto;padding:10px">
      <div style="background:rgba(245,230,200,0.95);border:2px solid #8b5a2b;border-radius:10px;padding:5px 10px;margin-bottom:6px">
        <div style="display:flex;justify-content:space-between;font-weight:900"><span>{enemy_name}</span><span>{cur_enemy_hp}/{enemy_max_hp}</span></div>
        <div style="height:8px;background:#3a2a1a;border-radius:4px;overflow:hidden"><div style="width:{enemy_per}%;height:100%;background:#ff3b30"></div></div>
      </div>

      <div style="background:url(/static/{camp_bg}) center/cover no-repeat;border-radius:16px;border:3px solid #c89b5e;height:300px;display:flex;align-items:flex-end;justify-content:space-between;padding:10px;position:relative;overflow:hidden">
        <div style="position:absolute;inset:0;background:rgba(255,248,220,0.18);border-radius:13px"></div>
        
        <!-- СЛЕВА ТЫ - без scaleX, смотрит вправо -->
        <div style="flex:1;text-align:center;z-index:2;display:flex;align-items:flex-end;justify-content:center">
          <img id="heroImg" src="/static/barbarian_game_size.png?v=5" style="height:190px;max-width:100%;object-fit:contain;filter:drop-shadow(0 4px 12px black);background:transparent">
        </div>
        
        <!-- СПРАВА ВРАГ - без scaleX, смотрит влево -->
        <div style="flex:1;text-align:center;z-index:2;display:flex;align-items:flex-end;justify-content:center">
          <img id="enemyImg" src="/static/{enemy_img}?v=5" style="height:190px;max-width:100%;object-fit:contain;filter:drop-shadow(0 4px 12px black);background:transparent">
        </div>

        <div id="dmgText" class="dmg">-{last_dmg}</div>
      </div>

      <div style="background:rgba(245,230,200,0.95);border:2px solid #8b5a2b;border-radius:10px;padding:5px 10px;margin:8px 0">
        <div style="display:flex;justify-content:space-between;font-weight:900"><span>ТЫ</span><span>{cur_my_hp}/20</span></div>
        <div style="height:10px;background:#3a2a1a;border-radius:4px;overflow:hidden"><div style="width:{my_per}%;height:100%;background:#2ecc40"></div></div>
      </div>

      <form id="fightForm" method="post" style="display:flex;gap:8px">
        <button type="button" onclick="doHit('hit')" style="flex:1;background:#2b1a0e;border:3px solid #ff8c00;border-radius:14px;padding:8px"><img src="/static/sword_normal.png" style="width:60px;height:60px;object-fit:contain"><div style="color:#ffb84d;font-weight:900;font-size:11px">УДАР [{hit_cnt}]</div></button>
        <button type="button" onclick="doHit('super')" style="flex:1;background:#2b1a0e;border:3px solid #ffcc00;border-radius:14px;padding:8px;opacity:{opac}"><img src="/static/sword_super.png" style="width:60px;height:60px;object-fit:contain"><div style="color:#ff0;font-weight:900;font-size:11px">{super_label}</div></button>
        <button name="m" value="run" style="background:#3a2a1a;border:2px solid #777;border-radius:10px;color:#ccc;padding:8px 14px;font-weight:900">БЕГ</button>
        <input type="hidden" name="m" id="mInput">
      </form>
    </div>

    <script>
    function doHit(type){{
      if(type=='super' && {hit_cnt} < 5) return;
      const hero = document.getElementById('heroImg');
      const enemy = document.getElementById('enemyImg');
      const dmg = document.getElementById('dmgText');
      const form = document.getElementById('fightForm');
      
      hero.classList.remove('anim-attack'); void hero.offsetWidth; hero.classList.add('anim-attack');
      enemy.classList.remove('anim-shake'); void enemy.offsetWidth; enemy.classList.add('anim-shake');
      dmg.classList.remove('show'); void dmg.offsetWidth; dmg.classList.add('show');

      setTimeout(()=>{{
        document.getElementById('mInput').value = type;
        form.submit();
      }}, 320);
    }}
    </script>
    '''
    return render_template_string(html)

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

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)))
