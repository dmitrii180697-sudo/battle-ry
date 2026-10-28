import os, random
from flask import Flask, request, redirect, session, render_template_string, send_from_directory
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "battle2026")
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
        conn=get_db(); cur=conn.cursor()
        if DATABASE_URL:
            cur.execute("CREATE TABLE IF NOT EXISTS players (id SERIAL PRIMARY KEY, name TEXT, login TEXT UNIQUE, password TEXT, gold INT DEFAULT 15, silver INT DEFAULT 50, rubin INT DEFAULT 0, exp INT DEFAULT 0, level INT DEFAULT 1, hp INT DEFAULT 20)")
        else:
            cur.execute("CREATE TABLE IF NOT EXISTS players (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, login TEXT UNIQUE, password TEXT, gold INT DEFAULT 15, silver INT DEFAULT 50, rubin INT DEFAULT 0, exp INT DEFAULT 0, level INT DEFAULT 1, hp INT DEFAULT 20)")
        conn.commit()
    except: pass
    try: cur.close(); conn.close()
    except: pass
init_db()

def get_player(uid):
    try:
        conn=get_db(); cur=conn.cursor()
        if DATABASE_URL: cur.execute("SELECT * FROM players WHERE id=%s",(uid,))
        else: cur.execute("SELECT * FROM players WHERE id=?",(uid,))
        p=cur.fetchone(); cur.close(); conn.close()
        return p
    except: return None

def vals(p):
    if not p: return (1,20,0,15,50)
    try:
        if hasattr(p,'get'):
            l = p.get("level",1); h = p.get("hp",20); r = p.get("rubin",0); g = p.get("gold",15); s = p.get("silver",50)
        else:
            l = p["level"]; h = p["hp"]; g = p["gold"]; s = p["silver"]; r = p["rubin"]
    except: l,h,r,g,s = 1,20,0,15,50
    return l,h,r,g,s

CSS = "<style>body{margin:0;background:#2b2218;font-family:Arial}.wrap{max-width:480px;margin:0 auto;min-height:100vh;background:#e8d6a8;position:relative}.btn-orange{display:block;width:90%;margin:10px auto;background:linear-gradient(#ffb84d,#ff8c00);border:2px solid #5a3e22;border-radius:6px;padding:12px;text-align:center;font-weight:bold;font-size:18px;color:#3d2817;text-decoration:none}.bottom{position:fixed;bottom:0;left:0;right:0;max-width:480px;margin:0 auto;background:#5a321a;color:#f5e6c0;display:flex;justify-content:space-between;padding:12px 16px;font-size:13px}</style>"

@app.route("/camp.jpg")
def camp_img():
    try: return send_from_directory('.','camp.jpg')
    except: return redirect("https://i.imgur.com/8Km9tLL.jpg")

@app.route("/")
def root():
    if "uid" in session: return redirect("/game")
    html = CSS + '<div class="wrap" style="padding:20px"><h1 style="text-align:center">BATTLE OF WARRIORS</h1><form method="post" action="/login"><input name="login" placeholder="Login" style="width:100%;padding:12px;margin:6px 0" required><input name="password" type="password" placeholder="Pass" style="width:100%;padding:12px;margin:6px 0" required><button class="btn-orange">Enter</button></form><a href="/reg" style="display:block;text-align:center;margin-top:10px">Reg</a></div>'
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
        hpw = row["password"] if DATABASE_URL else row[3]
        uid = row["id"] if DATABASE_URL else row[0]
        if check_password_hash(hpw, pw):
            session["uid"]=uid; session["my_hp"]=20; session["dummy_hp"]=25; session["log"]="In camp"
            return redirect("/game")
    return "Wrong pass <a href='/'>back</a>"

@app.route("/reg", methods=["GET","POST"])
def reg():
    if request.method=="POST":
        name=request.form.get("name","").strip(); lg=request.form.get("login","").strip(); pw=request.form.get("password","")
        try:
            conn=get_db(); cur=conn.cursor(); h=generate_password_hash(pw)
            if DATABASE_URL: cur.execute("INSERT INTO players (name,login,password,gold,silver,rubin) VALUES (%s,%s,%s,15,50,0) RETURNING id",(name,lg,h)); uid=cur.fetchone()["id"]
            else: cur.execute("INSERT INTO players (name,login,password,gold,silver,rubin) VALUES (?,?,?,15,50,0)",(name,lg,h)); uid=cur.lastrowid
            conn.commit(); cur.close(); conn.close()
            session["uid"]=uid; session["my_hp"]=20; session["dummy_hp"]=25; session["log"]="Hi!"
            return redirect("/game")
        except Exception as e: return f"Busy {e} <a href='/reg'>back</a>"
    html = CSS + '<div class="wrap" style="padding:20px"><h2>Reg</h2><form method="post"><input name="name" placeholder="Name" style="width:100%;padding:10px;margin:5px 0" required><input name="login" placeholder="Login" style="width:100%;padding:10px;margin:5px 0" required><input name="password" type="password" placeholder="Pass" style="width:100%;padding:10px;margin:5px 0" required><button class="btn-orange">Start</button></form></div>'
    return render_template_string(html)

@app.route("/game")
def game():
    if "uid" not in session: return redirect("/")
    p=get_player(session["uid"]); l,h,r,g,s = vals(p)
    top = '<div style="background:#e8d6a8;padding:8px;display:flex;justify-content:center"><div style="background:#fdf6c8;border:2px solid #8a6a3d;border-radius:16px;padding:6px 14px;display:flex;gap:14px;font-weight:bold;font-size:15px"><span>⭐ '+str(l)+'</span><span>❤️ '+str(h)+'</span><span>💎 '+str(r)+'</span><span>🪙 '+str(g)+'</span><span>⚪ '+str(s)+'</span></div></div>'
    body = '''
<div class="wrap" style="background:#e8d6a8">
'''+top+'''
<div style="margin:8px;background:#3d2817;padding:6px;border-radius:4px">
  <div style="height:300px;overflow:hidden;border:2px solid #2b1a0e;background:#000">
    <img src="/camp.jpg" style="width:100%;height:100%;object-fit:cover;display:block">
  </div>
</div>
<div style="display:flex;gap:8px;padding:10px 10px 0 10px">
  <a href="/promysel" style="flex:1;background:linear-gradient(#ffb84d,#ff8c00);border:2px solid #5a3e22;border-radius:8px;padding:12px;text-align:center;font-weight:bold;color:#3d2817;text-decoration:none;font-size:16px">🌲 Промысел</a>
  <a href="/pvp" style="flex:1;background:linear-gradient(#ffb84d,#ff8c00);border:2px solid #5a3e22;border-radius:8px;padding:12px;text-align:center;font-weight:bold;color:#3d2817;text-decoration:none;font-size:16px">⚔️ PVP</a>
</div>
<div style="padding:10px">
  <a href="/camp" style="display:block;background:linear-gradient(#ff8c00,#ff7b00);border:2px solid #5a3e22;border-radius:8px;padding:14px;text-align:center;font-weight:bold;font-size:18px;color:#3d2817;text-decoration:none">🏕️ Лагерь</a>
</div>
<div style="height:70px"></div>
<div class="bottom"><span>Меню</span><span>warriors</span><span><a href="/logout" style="color:#f5e6c0;text-decoration:none">Выход</a></span></div>
</div>
'''
    return render_template_string(CSS+body)

@app.route("/camp")
def camp():
    if "uid" not in session: return redirect("/")
    p=get_player(session["uid"]); l,h,r,g,s = vals(p)
    top = '<div style="background:#e8d6a8;padding:8px;display:flex;justify-content:center"><div style="background:#fdf6c8;border:2px solid #8a6a3d;border-radius:16px;padding:6px 14px;display:flex;gap:14px;font-weight:bold;font-size:15px"><span>⭐ '+str(l)+'</span><span>❤️ '+str(h)+'</span><span>💎 '+str(r)+'</span><span>🪙 '+str(g)+'</span><span>⚪ '+str(s)+'</span></div></div>'
    body = top + '<div class="wrap"><div style="padding:10px"><h3>Лагерь</h3><div style="margin:8px;background:#3d2817;padding:6px;border-radius:4px"><div style="height:200px;overflow:hidden;border:2px solid #2b1a0e"><img src="/camp.jpg" style="width:100%;height:100%;object-fit:cover"></div></div><p style="background:#f5e6c0;padding:10px;border:2px solid #5a3e22">Твой лагерь.</p><a href="/school" class="btn-orange">Тренировка</a><a href="/game" class="btn-orange" style="background:#d2b87e">На карту</a></div></div>'
    return render_template_string(CSS+body)

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
            dmg=random.randint(3,6); session["dummy_hp"]-=dmg; session["log"]=f"Ты бьешь {dmg}<br>"+session["log"]
            if session["dummy_hp"]<=0:
                conn=get_db(); cur=conn.cursor()
                if DATABASE_URL: cur.execute("UPDATE players SET gold=gold+2, silver=silver+5 WHERE id=%s",(session["uid"],))
                else: cur.execute("UPDATE players SET gold=gold+2, silver=silver+5 WHERE id=?",(session["uid"],))
                conn.commit(); cur.close(); conn.close()
                session["log"]="<b style='color:green'>Победа +2 +5</b><br>"+session["log"]
            else:
                ed=random.randint(1,3); session["my_hp"]-=ed; session["log"]=f"Манекен {ed} в ответ<br>"+session["log"]
    p=get_player(session["uid"]); l,h,r,g,s = vals(p)
    top = '<div style="background:#e8d6a8;padding:8px;display:flex;justify-content:center"><div style="background:#fdf6c8;border:2px solid #8a6a3d;border-radius:16px;padding:6px 14px;display:flex;gap:14px;font-weight:bold;font-size:15px"><span>⭐ '+str(l)+'</span><span>❤️ '+str(h)+'</span><span>💎 '+str(r)+'</span><span>🪙 '+str(g)+'</span><span>⚪ '+str(s)+'</span></div></div>'
    log = session["log"]
    body = top + f'<div class="wrap"><div style="padding:10px"><div style="background:#fff8dc;border:1px dashed #5a3e22;padding:8px;height:100px;overflow:auto">{log}</div><form method="post"><button name="m" value="1" class="btn-orange">Удар</button><button name="m" value="reset" class="btn-orange" style="background:#d2b87e">Новый манекен</button></form><a href="/camp" class="btn-orange" style="background:#bcaaa4">В лагерь</a></div></div>'
    return render_template_string(CSS+body)

@app.route("/promysel")
def promysel():
    if "uid" not in session: return redirect("/")
    p=get_player(session["uid"]); l,h,r,g,s = vals(p)
    top = '<div style="background:#e8d6a8;padding:8px;display:flex;justify-content:center"><div style="background:#fdf6c8;border:2px solid #8a6a3d;border-radius:16px;padding:6px 14px;display:flex;gap:14px;font-weight:bold;font-size:15px"><span>⭐ '+str(l)+'</span><span>❤️ '+str(h)+'</span><span>💎 '+str(r)+'</span><span>🪙 '+str(g)+'</span><span>⚪ '+str(s)+'</span></div></div>'
    body = top + '<div class="wrap"><div style="padding:10px"><h3>Промысел</h3><p style="background:#f5e6c0;padding:10px;border:2px solid #5a3e22">Ищешь в лесу.</p><form method="post" action="/promysel_go"><button class="btn-orange">Искать</button></form><a href="/game" class="btn-orange" style="background:#d2b87e">На карту</a></div></div>'
    return render_template_string(CSS+body)

@app.route("/promysel_go", methods=["POST"])
def promysel_go():
    if "uid" not in session: return redirect("/")
    conn=get_db(); cur=conn.cursor()
    g=random.randint(1,3); s=random.randint(5,15)
    if DATABASE_URL: cur.execute("UPDATE players SET gold=gold+%s, silver=silver+%s WHERE id=%s",(g,s,session["uid"]))
    else: cur.execute("UPDATE players SET gold=gold+?, silver=silver+? WHERE id=?",(g,s,session["uid"]))
    conn.commit(); cur.close(); conn.close()
    return redirect("/promysel")

@app.route("/pvp")
def pvp():
    if "uid" not in session: return redirect("/")
    return redirect("/school")

@app.route("/logout")
def logout(): session.clear(); return redirect("/")

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)))
