    html=f"""
    <div class="wrap" style="background:#1a0e0a;padding:12px;min-height:100vh;position:relative">
        <div style="background:#f5e6c0;border:2px solid #5a3e22;border-radius:14px;padding:12px;margin-bottom:10px">
            <div style="font-weight:bold;margin-bottom:6px">{session['enemy_name']} HP: {eh}/{session['enemy_max']}</div>
            <div style="background:#300;height:14px;border-radius:7px"><div style="width:{ehp}%;height:100%;background:linear-gradient(#ff4d4d,#b30000);border-radius:7px;transition: width 0.5s"></div></div>
        </div>
        
        <div style="display:flex;justify-content:space-between;align-items:end;background:#2b1a0e;border-radius:12px;padding:10px;margin-bottom:10px;height:260px;position:relative;overflow:hidden">
            <img id="hero-img" src="/static/{HERO_IMG}" style="height:220px;object-fit:contain;filter:drop-shadow(0 0 8px black);transition:0.15s">
            <div style="position:relative">
                <img id="enemy-img" src="/static/{enemy_img}" style="height:220px;object-fit:contain;filter:drop-shadow(0 0 8px black)">
                <div id="dmg-float">-5</div>
            </div>
        </div>

        <div style="background:#f5e6c0;border:2px solid #5a3e22;border-radius:14px;padding:12px;margin-bottom:10px">
            <div style="font-weight:bold;margin-bottom:6px">Ты HP: {mh}/20</div>
            <div style="background:#300;height:14px;border-radius:7px"><div style="width:{mhp}%;height:100%;background:linear-gradient(#4dff4d,#00b300);border-radius:7px;transition: width 0.5s"></div></div>
        </div>
        <div style="background:#000;color:#0f0;padding:8px;border-radius:8px;height:120px;overflow:auto;margin-bottom:10px;font-size:13px">{session['log']}</div>
        
        <form id="hit-form" method="post" style="display:flex;gap:8px">
            <button type="button" onclick="doHit()" style="flex:1;background:linear-gradient(#ffb84d,#ff8c00);border:2px solid #5a3e22;border-radius:8px;padding:14px;font-weight:bold">🗡️ УДАР ДУБИНОЙ</button>
            <button name="m" value="run" style="flex:1;background:#ccc;border:2px solid #5a3e22;border-radius:8px;padding:14px;font-weight:bold">🏃 БЕГ</button>
        </form>
    </div>
    <script src="/static/game.js"></script>
    """
