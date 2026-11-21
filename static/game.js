let canAttack = true;
let timeLeft = 20;
let timerInt = null;

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
  if(type !== 'run') canAttack = false;
  clearInterval(timerInt);

  const hero = document.getElementById('heroImg');
  const enemy = document.getElementById('enemyImg');
  if(hero && (type === 'hit' || type === 'super')){
    hero.style.animation = 'none'; void hero.offsetWidth;
    hero.style.animation = 'attackLeft 0.32s ease';
  }
  if(enemy && (type === 'hit' || type === 'super')){
    setTimeout(()=>{
      enemy.style.animation = 'none'; void enemy.offsetWidth;
      enemy.style.animation = 'shakeRight 0.32s ease';
    }, 180);
  }
  if(type === 'super') shakeScreen();

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

    if(data.super_used !== undefined){
      if(document.getElementById('superCnt')) document.getElementById('superCnt').innerText = data.super_used + '/4';
      if(document.getElementById('superInfo')) document.getElementById('superInfo').innerText = 'Супер ' + data.super_used + '/4 • Нужно ударов для следующего: ' + (data.need_for_next ?? '');
      if(document.getElementById('superNeed')) document.getElementById('superNeed').innerText = data.super_used >= 4 ? 'всё!' : 'нужно ' + (data.need_for_next ?? '');
    }

    let isCrit = data.last_dmg >= 7;
    if(data.last_dmg > 0) showDamage('-' + data.last_dmg, 'enemy', isCrit);
    if(data.edmg > 0) showDamage('-' + data.edmg, 'hero', false);

    let logEl = document.getElementById('log');
    if(type === 'hit' && logEl) logEl.innerHTML = isCrit ? `💥 <b>КРИТ!</b> -${data.last_dmg} HP! Враг ответил -${data.edmg}` : `Вы нанесли <span style="color:#ff4d4d">-${data.last_dmg}</span> HP! Враг ответил -${data.edmg}`;
    if(type === 'super' && logEl) logEl.innerHTML = `🔥 СУПЕРУДАР! -${data.last_dmg} HP!`;
    if(type === 'enemy_auto') addLog(`Ты замешкался! Враг ударил на -${data.edmg}`);
    else if(data.last_dmg > 0 || data.edmg > 0) addLog(`Ты ударил на -${data.last_dmg} | Враг ответил на -${data.edmg}`);

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
  finally { canAttack = true; }
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

function addLog(text){
  const b = document.getElementById('battleLog');
  if(!b) return;
  const d = document.createElement('div');
  d.innerText = text;
  d.style.cssText = 'padding:4px 8px;border-bottom:1px solid #444;font-size:13px;color:#fff;';
  b.prepend(d);
}

document.addEventListener("DOMContentLoaded", ()=>{ startTimer(); });