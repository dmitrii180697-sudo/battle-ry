import os, json
from flask import request, session, redirect, render_template_string
from . import admin_bp

# --- свои helpers, чтобы не импортировать из app.py и не было круга ---
def _load_json(name):
    p = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", f"{name}.json")
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def _save_json(name, data):
    p = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", f"{name}.json")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _get_db():
    import psycopg2
    from psycopg2.extras import RealDictCursor
    DATABASE_URL = os.environ.get("DATABASE_URL")
    if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    if DATABASE_URL:
        return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor), True
    else:
        import sqlite3
        conn = sqlite3.connect('/tmp/battle.db')
        conn.row_factory = sqlite3.Row
        return conn, False

def _is_admin():
    if "uid" not in session:
        return False
    try:
        conn, is_pg = _get_db(); cur = conn.cursor()
        q = "SELECT login FROM players WHERE id=%s" if is_pg else "SELECT login FROM players WHERE id=?"
        cur.execute(q, (session["uid"],))
        row = cur.fetchone(); cur.close(); conn.close()
        if not row: return False
        login = row["login"] if isinstance(row, dict) else row[0]
        return login == "admin"
    except:
        return False

def _get_player_by_login(login):
    conn, is_pg = _get_db(); cur = conn.cursor()
    q = "SELECT * FROM players WHERE login=%s" if is_pg else "SELECT * FROM players WHERE login=?"
    cur.execute(q, (login,))
    row = cur.fetchone(); cur.close(); conn.close()
    if not row: return None
    return dict(row) if isinstance(row, dict) else dict(row)

@admin_bp.route("/items", methods=["GET", "POST"])
def admin_items():
    if not _is_admin():
        return "⛔ Нет доступа! <a href='/game'>На главную</a>"
    msg = ""
    shop = _load_json("shop")
    if not isinstance(shop, dict):
        shop = {}
    if request.method == "POST":
        action = request.form.get("action")
        # --- создать вещь ---
        if action == "create":
            cat = request.form.get("cat", "weapon")
            new_item = {
                "id": request.form.get("item_id", "").strip() or f"item_{len(shop.get(cat, []))+1}",
                "name": request.form.get("name", "Новая вещь"),
                "icon": request.form.get("icon", "📦"),
                "damage": int(request.form.get("damage") or 0),
                "armor": int(request.form.get("armor") or 0),
                "dodge": int(request.form.get("dodge") or 0),
                "gold": int(request.form.get("gold") or 0),
                "silver": int(request.form.get("silver") or 0),
                "rubin": int(request.form.get("rubin") or 0),
                "level": int(request.form.get("level") or 1),
                "location": request.form.get("location") or None,
                "desc": request.form.get("desc", ""),
            }
            if cat not in shop: shop[cat] = []
            shop[cat].append(new_item)
            _save_json("shop", shop)
            msg = f"✅ Создано: {new_item['name']}"
        # --- выдать вещь ---
        elif action == "give":
            login = request.form.get("target_login", "").strip()
            cat = request.form.get("cat")
            item_id = request.form.get("item_id")
            p = _get_player_by_login(login)
            if not p:
                msg = "❌ Игрок не найден"
            else:
                try:
                    conn, is_pg = _get_db(); cur = conn.cursor()
                    # читаем инвентарь
                    q = "SELECT inventory, equipped FROM players WHERE id=%s" if is_pg else "SELECT inventory, equipped FROM players WHERE id=?"
                    cur.execute(q, (p["id"],))
                    r = cur.fetchone()
                    inv = json.loads(r["inventory"] or "[]") if r and r["inventory"] else []
                    eq = json.loads(r["equipped"] or "{}") if r and r["equipped"] else {}
                    inv.append({"id": item_id, "cat": cat})
                    q2 = "UPDATE players SET inventory=%s, equipped=%s WHERE id=%s" if is_pg else "UPDATE players SET inventory=?, equipped=? WHERE id=?"
                    cur.execute(q2, (json.dumps(inv), json.dumps(eq), p["id"]))
                    conn.commit(); cur.close(); conn.close()
                    msg = f"✅ Выдано {login}: вещь {item_id}"
                except Exception as e:
                    msg = f"❌ Ошибка: {e}"
        # --- удалить вещь ---
        elif action == "delete":
            cat = request.form.get("cat"); item_id = request.form.get("item_id")
            if cat in shop:
                shop[cat] = [x for x in shop[cat] if str(x.get("id")) != str(item_id)]
                _save_json("shop", shop)
                msg = f"🗑️ Удалено {item_id}"
        shop = _load_json("shop")

    # --- HTML ---
    items_html = ""
    for cat, lst in shop.items():
        items_html += f"<h3 style='margin-top:20px'>📦 {cat} ({len(lst)})</h3>"
        for it in lst:
            items_html += f"""
            <div style="background:#fdf6c8;border:2px solid #8a6a3d;border-radius:10px;padding:10px;margin:6px 0;display:flex;gap:8px;align-items:center">
              <span style="font-size:28px">{it.get('icon','📦')}</span>
              <div style="flex:1;text-align:left"><b>{it.get('name')}</b><br><small>ID: {it.get('id')} | ⚔️{it.get('damage',0)} 🛡️{it.get('armor',0)} 💨{it.get('dodge',0)} | {it.get('gold',0)}🪙 {it.get('silver',0)}⚪ {it.get('rubin',0)}💎</small></div>
              <form method="post" style="display:flex;gap:4px"><input type="hidden" name="action" value="delete"><input type="hidden" name="cat" value="{cat}"><input type="hidden" name="item_id" value="{it.get('id')}"><button style="background:#c92a2a;color:#fff;border:0;padding:6px 10px;border-radius:6px">🗑️</button></form>
            </div>
            <form method="post" style="background:#e8ffd6;border:2px solid green;border-radius:10px;padding:8px;margin:-2px 0 8px;display:flex;gap:6px"><input type="hidden" name="action" value="give"><input type="hidden" name="cat" value="{cat}"><input type="hidden" name="item_id" value="{it.get('id')}"><input name="target_login" placeholder="Логин игрока" required style="flex:1"><button style="background:green;color:#fff;border:0;padding:8px 12px;border-radius:6px;font-weight:bold">🎁 ВЫДАТЬ</button></form>
            """
    html = f"""
    <div style="max-width:480px;margin:0 auto;background:#e8d6a8;min-height:100vh;padding:15px">
      <h2 style="text-align:center">🛒 АДМИН: ВЕЩИ</h2>
      <p style="text-align:center;color:green;font-weight:bold">{msg}</p>
      <a href="/admin" style="display:block;text-align:center;margin-bottom:10px">← Назад в админку</a>
      <h3>➕ Создать вещь</h3>
      <form method="post" style="background:#fff;border:2px solid #8a6a3d;border-radius:10px;padding:12px">
        <input type="hidden" name="action" value="create">
        Категория: <select name="cat"><option value="weapon">weapon - Оружие</option><option value="armor">armor - Броня</option><option value="potion">potion - Зелья</option><option value="amulet">amulet - Амулеты</option><option value="misc">misc - Разное</option></select>
        ID (англ, без пробелов): <input name="item_id" placeholder="naprimer: mech_topor" required>
        Название: <input name="name" placeholder="Меч Топор" required>
        Иконка (эмодзи): <input name="icon" value="🗡️">
        Урон: <input name="damage" type="number" value="0">
        Броня: <input name="armor" type="number" value="0">
        Уворот: <input name="dodge" type="number" value="0">
        Цена золото: <input name="gold" type="number" value="0">
        Цена серебро: <input name="silver" type="number" value="0">
        Цена рубины: <input name="rubin" type="number" value="0">
        Треб. уровень: <input name="level" type="number" value="1">
        Локация (пусто = везде): <input name="location" placeholder="lager / zostava / пусто">
        Описание: <input name="desc" placeholder="Крутой меч">
        <button style="width:100%;background:#ff8c00;color:#fff;padding:12px;border:0;border-radius:8px;font-weight:900;margin-top:8px">➕ СОЗДАТЬ ВЕЩЬ</button>
      </form>
      <h3 style="margin-top:20px">📦 Все вещи в магазине</h3>
      {items_html if items_html else "<p>Пока пусто</p>"}
      <a href="/game" style="display:block;text-align:center;margin-top:15px">← На главную</a>
    </div>
    """
    return render_template_string(html)