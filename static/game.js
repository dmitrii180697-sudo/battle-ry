let isAnimating = false;

function findHeroImg(){
    let hero = null;
    document.querySelectorAll('img').forEach(img=>{
        if(img.src.includes('barbarian') || img.src.includes('anim_')) hero = img;
    });
    if(hero) return hero;
    let all = document.querySelectorAll('img');
    return all.length ? all[all.length-1] : null;
}

function playHitAndThenSubmit(form, move){
    if(isAnimating) return;
    const hero = findHeroImg();
    if(!hero){
        form.submit();
        return;
    }
    isAnimating = true;
    
    // ВАЖНО: подкладываем m, чтобы app.py увидел удар
    let mInput = form.querySelector('input[name="m"]');
    if(!mInput){
        mInput = document.createElement('input');
        mInput.type='hidden';
        mInput.name='m';
        form.appendChild(mInput);
    }
    mInput.value = move;

    hero.src = '/static/anim_raise.png';
    setTimeout(()=>{
        hero.src = '/static/anim_hit.png';
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
            
            if(move.includes('hit') || move.includes('удар')){
                e.preventDefault();
                playHitAndThenSubmit(form, 'hit');
            }
            if(move.includes('super')){
                e.preventDefault();
                playHitAndThenSubmit(form, 'super');
            }
        });
    });
});