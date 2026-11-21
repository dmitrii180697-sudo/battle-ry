let canAttack = true;
let timeLeft = 20;
let timerInt = null;

// === ИНТЕРВАЛ МЕЖДУ УДАРАМИ ===
// 1100 = 1.1 секунды между ударами. Поставь 1500 если хочешь еще медленнее
const ATTACK_COOLDOWN = 1100;
let lastAttackTime = 0;

function startTimer(){
  clearInterval(timerInt);
  timeLeft = 20;
  updateTimerUI();
  timerInt = setInterval(()=>{
    timeLeft--;
    updateTimerUI();
    if(timeLeft <= 0){
      clearInterval(timerInt);
      let txt = document.getElementById('turnText');
      if(txt) txt.innerText = 'Ты замешкался! Враг бьёт!';
      makeAction('enemy_auto');
    }
  }, 1000);
}

function updateTimerUI(){
  let bar = document.getElementById('timerBar');
  let txt = document.getElementById('turnText');
  let big = document.getElementById('battle-timer');
  if(bar) bar.style.width = Math.max(0, timeLeft*5) + '%';
  if(bar) bar.style.background = timeLeft <= 5 ? '#ff4444' : '#ffcc00';
  if(txt && timeLeft > 0) txt.innerText = 'Твой ход! ' + timeLeft + ' сек';
  if(big) big.innerText = Math.max(0, timeLeft);
}

function resetTimer(){ startTimer(); }

function shakeScreen(){
  let w = document.getElementById('fightWrap');
  if(!w) return;
  w.style.animation = 'none'; void w.offsetWidth;
  w.style.animation = 'shakeScreen .35s ease';
}

async function makeAction(type){
  if(type !== 'enemy_auto' && !canAttack) return;
  // === ЗАЩИТА ОТ СПАМА: не даем бить чаще чем раз в ATTACK_COOLDOWN ===
  if(type === 'hit'){
    let now = Date.now();
    if(now - lastAttackTime < ATTACK_COOLDOWN) return;
    lastAttackTime = now;
  }
  if(type !== 'run') canAttack = false;
  clearInterval(timerInt);

  const hero = document.getElementById('heroImg');
  const enemy = document.getElementById('enemyImg');
  const hitBtn = document.getElementById('hitBtn');
  if(hitBtn) { hitBtn.disabled = true; hitBtn.classList.add('cooldown'); }

  if(hero && type === 'hit'){
    hero.style.animation = 'none'; void hero.offsetWidth;
    hero.style.animation = 'attackLeft 0.45s ease';
  }
  if(enemy && type === 'hit'){
    setTimeout(()=>{
      enemy.style.animation = 'none'; void enemy.offsetWidth;
      enemy.style.animation = 'shakeRight 0.45s ease';
    }, 220);
  }

  try{
    let resp = await fetch('/fight_battle', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({m: type})
    });
    let data = await resp.json();
    if(data.status === 'redirect'){ window.location.href = data.url; return; }

    if(document.getElementById('enHp')) document.getElementById('enHp').innerText = data.enemy_hp;
    if(document.getElementById('enBar')) document.getElementById('enBar').style.width = Math.max(0, (data.enemy_hp*100/data.enemy_max)) + '%';
    if(document.getElementById('myHp')) document.getElementById('myHp').innerText = data.my_hp;
    if(document.getElementById('myBar')) document.getElementById('myBar').style.width = Math.max(0, (data.my_hp*100/data.my_max)) + '%';
    if(document.getElementById('hitCnt')) document.getElementById('hitCnt').innerText = data.hit_cnt;

    let isCrit = data.last_dmg >= 7;
    if(data.last_dmg > 0) showDamage('-' + data.last_dmg, 'enemy', isCrit);
    if(data.edmg > 0) showDamage('-' + data.edmg, 'hero', false);

    if(data.finished){
      clearInterval(timerInt);
      document.getElementById('endOverlay').style.display = 'flex';
      if(data.is_win){
        document.getElementById('endTitle').innerText = '🏆 ПОБЕДА!';
        document.getElementById('endTitle').style.color = 'gold';
        document.getElementById('trophyBox').innerHTML = `<b>Получено:</b><br>🪙 Золото:+${data.reward_g}<br>⚪ Серебро:+${data.reward_s}<br>💎 Рубины:+${data.reward_r}`;
      } else {
        document.getElementById('endTitle').innerText = '💀 ПОРАЖЕНИЕ!';
        document.getElementById('endTitle').style.color = '#ff4d4d';
        document.getElementById('trophyBox').innerHTML = 'Вы пали в бою...';
      }
      return;
    }

    resetTimer();
  } catch(e){ console.error(e); }
  finally {
    // === ПАУЗА ПЕРЕД СЛЕДУЮЩИМ УДАРОМ ===
    setTimeout(()=>{
      canAttack = true;
      if(hitBtn){ hitBtn.disabled = false; hitBtn.classList.remove('cooldown'); }
    }, ATTACK_COOLDOWN);
  }
}

function showDamage(text, who, isCrit){
  const target = who === 'enemy' ? document.getElementById('enemyImg') : document.getElementById('heroImg');
  if(!target) return;
  const el = document.createElement('div');
  el.innerText = text;
  el.style.cssText = `position:absolute;top:20px;left:50%;transform:translateX(-50%);color:${isCrit ? '#ffd700' : '#ff3b30'};font-size:${isCrit ? '38px' : '28px'};font-weight:900;text-shadow:2px 2px 0 #000;z-index:99;pointer-events:none;`;
  target.parentElement.style.position = 'relative';
  target.parentElement.appendChild(el);
  let y = 20, op = 1;
  let timer = setInterval(()=>{
    y -= 3; op -= 0.05;
    el.style.top = y + 'px'; el.style.opacity = op;
    if(op <= 0){ clearInterval(timer); el.remove(); }
  }, 20);
}

document.addEventListener("DOMContentLoaded", ()=>{ startTimer(); });