let isAnimating = false;

const HERO_FRAMES = {
  idle: '/static/barbarian_idle.webp',
  raise: '/static/anim_raise.png',
  hit: '/static/anim_hit.png'
};
Object.values(HERO_FRAMES).forEach(src => {
  const img = new Image(); img.src = src;
});

function findHeroImg(){
  return document.getElementById('hero') || document.getElementById('heroImg') || document.querySelector('.hero-img');
}

function playHitAndThenSubmit(form, move){
  if(isAnimating) return;
  const hero = findHeroImg();
  const enemy = document.getElementById('enemy') || document.getElementById('enemyImg');
  isAnimating = true;

  let mInput = form.querySelector('input[name="m"]');
  if(!mInput){
    mInput = document.createElement('input');
    mInput.type='hidden'; mInput.name='m';
    form.appendChild(mInput);
  }
  mInput.value = move;

  if(hero){
    hero.style.animation='none'; void hero.offsetWidth;
    hero.style.animation='attackLeft 0.35s ease';
  }
  if(enemy){
    setTimeout(()=>{
      enemy.style.animation='none'; void enemy.offsetWidth;
      enemy.style.animation='shakeRight 0.35s ease';
    },180);
  }

  setTimeout(()=>{
    isAnimating=false;
    form.submit();
  },500);
}

document.addEventListener('DOMContentLoaded', ()=>{
  document.querySelectorAll('form').forEach(form=>{
    form.addEventListener('submit', (e)=>{
      const btn = document.activeElement;
      let move = btn && btn.value ? btn.value : 'hit';
      if(move !== 'hit' && move !== 'super' && !move.includes('super')) move = 'hit';
      let finalMove = move.includes('super') ? 'super' : 'hit';
      e.preventDefault();
      playHitAndThenSubmit(form, finalMove);
    });
  });
});