async function makeAction(type) {
    if (window.isAnimating) return;
    window.isAnimating = true;
  
    const hero = document.getElementById('heroImg') || document.getElementById('hero');
    const enemy = document.getElementById('enemyImg') || document.getElementById('enemy');
  
    if (hero) { 
        hero.style.animation = 'none'; 
        void hero.offsetWidth; 
        hero.style.animation = 'attackLeft 0.32s ease'; 
    }
    if (enemy) { 
        setTimeout(() => { 
            enemy.style.animation = 'none'; 
            void enemy.offsetWidth; 
            enemy.style.animation = 'shakeRight 0.32s ease'; 
        }, 180); 
    }

    let resp = await fetch('/fight_battle', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({m: type})
    });
    let data = await resp.json();
  
    if (data.status === 'redirect') { 
        window.location.href = data.url; 
        return; 
    }

    // Обновляем показатели
    document.getElementById('enHp').innerText = data.enemy_hp;
    document.getElementById('enBar').style.width = Math.max(0, (data.enemy_hp * 100 / data.enemy_max)) + '%';
    document.getElementById('myHp').innerText = data.my_hp;
    document.getElementById('myBar').style.width = Math.max(0, (data.my_hp * 100 / data.my_max)) + '%';
    document.getElementById('hitCnt').innerText = data.hit_cnt;

    // 1. Вылетающая цифра урона как в видео
    if (data.last_dmg > 0) showDamage('-' + data.last_dmg, 'enemy');
    if (data.edmg > 0) showDamage('-' + data.edmg, 'hero');

    // 2. Лог боя списком
    addLog(`Ты ударил на -${data.last_dmg} | Враг ответил на -${data.edmg}`);

    window.isAnimating = false;

    if (data.finished) { 
        setTimeout(() => { 
            window.location.reload(); 
        }, 600); 
    }
}

function showDamage(text, who) {
    const target = who === 'enemy' ? document.getElementById('enemyImg') : document.getElementById('heroImg');
    if (!target) return;
    const el = document.createElement('div');
    el.innerText = text;
    el.style.cssText = 'position:absolute;top:20px;left:50%;transform:translateX(-50%);color:#ff3b30;font-size:28px;font-weight:900;text-shadow:2px 2px 0 #000;z-index:99;pointer-events:none;';
    target.parentElement.style.position = 'relative';
    target.parentElement.appendChild(el);
    // анимация вверх + исчезновение
    let y = 20;
    let op = 1;
    let timer = setInterval(() => {
        y -= 2; op -= 0.05;
        el.style.top = y + 'px';
        el.style.opacity = op;
        if (op <= 0) { clearInterval(timer); el.remove(); }
    }, 20);
}

function addLog(text) {
    const logBox = document.getElementById('battleLog');
    if (!logBox) return;
    const div = document.createElement('div');
    div.innerText = text;
    div.style.cssText = 'padding:4px 8px;border-bottom:1px solid #444;font-size:13px;color:#fff;';
    logBox.prepend(div);
}

// --- МЕНЯЕМ НАЗВАНИЕ ЛОКАЦИИ ---
document.addEventListener("DOMContentLoaded", () => {
    const LOCS = {lager: "Лагерь", zastava: "Застава", oboz: "Обоз", promysel: "Промысел", camp: "Лагерь"};
    const p = new URLSearchParams(location.search);
    const cur = p.get("loc") || "lager";
    const el = document.getElementById("locName");
    if (el) el.textContent = LOCS[cur] || "Лагерь";
});