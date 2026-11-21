let canAttack = true;
let timeLeft = 20;
let timerInt = null;

// Интервал между ударами - 1.1 сек. Хочешь медленнее - поставь 1500
const ATTACK_COOLDOWN = 1100;
let lastAttackTime = 0;
let shieldActive = false;

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

function usePotion(n){
  let slots = document.querySelectorAll('.potion-slot');
  if(slots[n-1]){ slots[n-1].style.background = '#2e7d32'; setTimeout(()=>{ slots[n-1].style.background=''; }, 300); }
}
function useScroll(n){
  let slots = document.querySelectorAll('.scroll-slot');
  if(slots[n-1]){ slots[n-1].style.background = '#3a3a7a'; setTimeout(()=>{ slots[n-1].style.background=''; }, 300); }
}

async function makeAction(type){
  if(type == 'enemy_auto') type = 'enemy_turn';
  if(type === 'hit' || type === 'super' || type === 'shield'){
    let now = Date.now();
    if(now - lastAttackTime < ATTACK_COOLDOWN) return;
    lastAttackTime = now;
  }
  if(type === 'shield' && shieldActive) return;
  if(type !== 'run') canAttack = false;
  clearInterval(timerInt);

  const hero = document.getElementById('heroImg');
  const enemy = document.getElementById('enemyImg');
  const hitBtn = document.getElementById('hitBtn');
  const superBtn = document.getElementById('superBtn');
  const shieldBtn = document.getElementById('shieldBtn');
  if(hitBtn) { hitBtn.disabled = true; hitBtn.classList.add('cooldown'); }
  if(superBtn) { superBtn.disabled = true; superBtn.classList.add('cooldown'); }
  if(shieldBtn) { shieldBtn.disabled = true; shieldBtn.classList.add('cooldown'); }

  if(hero && (type === 'hit' || type === 'super')){
    hero.style.animation = 'none'; void hero.offsetWidth;
    hero.style.animation = 'attackLeft 0.45s ease';
  }
  if(enemy && (type === 'hit' || type === 'super')){
    setTimeout(()=>{
      enemy.style.animation = 'none'; void enemy.offsetWidth;
      enemy.style.animation = 'shakeRight 0.45s ease';
    }, 220);
  }
  if(type === 'super') shakeScreen();

  if(type === 'shield'){
    shieldActive = true;
    let st = document.getElementById('shieldState');
    if(st) st.innerText = 'активен!';
    if(hero) hero.style.filter = 'drop-shadow(0 0 12px #7ab8ff) brightness(1.2)';
  }

  try{
    let resp = await fetch('/fight_battle', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({m: type})
    });
    let data = await resp.json();
    if(data.status === 'redirect'){ window.location.href = data.url; return; }

    if((type == 'hit' || type == 'super' || type == 'shield') && !data.finished){
  setTimeout(() => makeAction('enemy_turn'), 800);
}
    if(document.getElementById('enHp')) document.getElementById('enHp').innerText = data.enemy_hp;
    if(document.getElementById('enBar')) document.getElementById('enBar').style.width = Math.max(0, (data.enemy_hp*100/data.enemy_max)) + '%';
    if(document.getElementById('myHp')) document.getElementById('myHp').innerText = data.my_hp;
    if(document.getElementById('myBar')) document.getElementById('myBar').style.width = Math.max(0, (data.my_hp*100/data.my_max)) + '%';
    if(document.getElementById('hitCnt')) document.getElementById('hitCnt').innerText = data.hit_cnt;

    if(data.super_used !== undefined){
      if(document.getElementById('superCnt')) document.getElementById('superCnt').innerText = data.super_used + '/4';
      if(document.getElementById('superInfo')) document.getElementById('superInfo').innerText = 'Супер ' + data.super_used + '/4 • Нужно ударов для следующего: ' + (data.need_for_next ?? '');
      if(document.getElementById('superNeed')) document.getElementById('superNeed').innerText = data.super_used >= 4 ? 'всё!' : 'нужно ' + (data.need_for_next ?? '');
    }

    // Щит сработал - враг ударил на 0
    if(shieldActive && data.edmg === 0){
      shieldActive = false;
      let st = document.getElementById('shieldState');
      if(st) st.innerText = 'готов';
      if(hero) hero.style.filter = 'drop-shadow(0 6px 10px rgba(0,0,0,.8))';
    }

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
    setTimeout(()=>{
      canAttack = true;
      if(hitBtn){ hitBtn.disabled = false; hitBtn.classList.remove('cooldown'); }
      if(superBtn){ superBtn.disabled = false; superBtn.classList.remove('cooldown'); }
      if(shieldBtn){ shieldBtn.disabled = false; shieldBtn.classList.remove('cooldown'); }
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