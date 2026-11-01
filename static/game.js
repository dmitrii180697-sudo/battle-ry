async function makeAction(type){
  if(window.isAnimating) return;
  window.isAnimating = true;
  
  const hero = document.getElementById('heroImg') || document.getElementById('hero');
  const enemy = document.getElementById('enemyImg') || document.getElementById('enemy');
  
  if(hero){ hero.style.animation='none'; void hero.offsetWidth; hero.style.animation='attackLeft 0.32s ease'; }
  if(enemy){ setTimeout(()=>{ enemy.style.animation='none'; void enemy.offsetWidth; enemy.style.animation='shakeRight 0.32s ease'; },180); }

  let resp = await fetch('/fight_battle', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({m: type})
  });
  let data = await resp.json();
  
  if(data.status === 'redirect'){ window.location.href = data.url; return; }

  // ТУТ ОТНИМАЕТ УРОН НА ЭКРАНЕ
  document.getElementById('enHp').innerText = data.enemy_hp;
  document.getElementById('enBar').style.width = (data.enemy_hp*100/data.enemy_max)+'%';
  document.getElementById('myHp').innerText = data.my_hp;
  document.getElementById('myBar').style.width = (data.my_hp*100/data.my_max)+'%';
  document.getElementById('hitCnt').innerText = data.hit_cnt;

  window.isAnimating = false;
  if(data.finished){ setTimeout(()=>{ window.location.reload(); }, 600); }
}