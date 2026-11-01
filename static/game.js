let isAnimating = false;

// Предзагружаем кадры чтобы не было белого мигания
const HERO_FRAMES = {
  idle: '/static/barbarian_idle.webp',
  raise: '/static/anim_raise.png',
  hit: '/static/anim_hit.png'
};
Object.values(HERO_FRAMES).forEach(src => {
  const img = new Image();
  img.src = src;
});

function findHeroImg(){
    // Ищем по id, потом по классу, в конце уже по src
    let hero = document.getElementById('hero') || document.querySelector('.hero-img');
    if(hero) return hero;
    
    let found = null;
    document.querySelectorAll('img').forEach(img=>{
        if(img.src.includes('barbarian') || img.src.includes('anim_')) found = img;
    });
    return found;
}

function playHitAndThenSubmit(form, move){
    if(isAnimating) return; // было rleturn
    const hero = findHeroImg();
    if(!hero){
        form.submit();
        return;
    }
    isAnimating = true;
    
    // подкладываем m, чтобы app.py увидел удар
    let mInput = form.querySelector('input[name="m"]');
    if(!mInput){
        mInput = document.createElement('input');
        mInput.type='hidden';
        mInput.name='m';
        form.appendChild(mInput);
    }
    mInput.value = move;

    // Убираем все CSS анимации которые давали дергание
    hero.style.animation = 'none';
    hero.style.transform = 'none';

    hero.src = HERO_FRAMES.raise;
    setTimeout(()=>{
        hero.src = HERO_FRAMES.hit;
        setTimeout(()=>{
            isAnimating = false;
            form.submit();
        }, 450);
    }, 200);
}

document.addEventListener('DOMContentLoaded', ()=>{
    document.querySelectorAll('form').forEach(form=>{
        form.addEventListener('submit', (e)=>{
            let mInput = form.querySelector('input[name="m"]');
            let move = mInput ? mInput.value : (e.submitter ? e.submitter.value : '');
            move = (move || '').toLowerCase();
            
            if(move.includes('hit') || move.includes('удар') || move.includes('super')){
                e.preventDefault();
                let finalMove = move.includes('super') ? 'super' : 'hit';
                playHitAndThenSubmit(form, finalMove);
            }
        });
    });
});