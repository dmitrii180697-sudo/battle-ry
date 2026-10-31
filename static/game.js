let isAnimating = false;

function findHeroImg() {
    // 1. пробуем по id
    let hero = document.getElementById('hero-img') || document.getElementById('my-img');
    if (hero) return hero;

    // 2. ищем по названию файла - теперь ищем и barbarian
    const all = document.querySelectorAll('img');
    for (let img of all) {
        const s = img.src.toLowerCase();
        if (s.includes('barbarian') || s.includes('warrior') || s.includes('ancient') || s.includes('anim_')) {
            hero = img; // берем последнего подходящего - это ты (справа)
        }
    }
    if (hero) return hero;

    // 3. fallback - правая картинка из 2х
    if (all.length >= 2) return all[1];
    if (all.length >= 1) return all[0];
    return null;
}

function playHitAndThenSubmit(form) {
    if (isAnimating) return;
    const hero = findHeroImg();
    
    if (!hero) {
        console.log('Героя не нашел, отправляю сразу');
        form.submit();
        return;
    }

    isAnimating = true;
    console.log('БЬЮ ПАЛКОЙ! Нашел:', hero.src);
    
    // чтобы было видно что сработало
    hero.style.transition = 'all 0.12s ease-out';
    hero.style.outline = '3px solid yellow';
    
    hero.src = '/static/anim_raise.png';
    hero.style.transform = 'translateX(-15px) scale(1.05)';

    setTimeout(() => {
        hero.src = '/static/anim_hit.png';
        hero.style.transform = 'translateX(-35px) translateY(10px) scale(1.2) rotate(-8deg)';
        hero.style.outline = '3px solid red';

        setTimeout(() => {
            hero.style.transform = 'translateX(0) scale(1)';
            hero.style.outline = 'none';
            hero.src = '/static/barbarian_game_size.png'; // возвращаем ТВОЕГО рыжего, а не седого
            isAnimating = false;
            form.submit();
        }, 550);
    }, 180);
}

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', (e) => {
            const mInput = form.querySelector('input[name="m"]');
            const btn = e.submitter;
            const val = (mInput ? mInput.value : '') || (btn ? btn.value : '') || btn?.textContent || '';
            
            if (val.toLowerCase().includes('hit') || val.toLowerCase().includes('удар') || val.includes('⚔')) {
                e.preventDefault();
                playHitAndThenSubmit(form);
            }
        });
    });
    console.log('Удар v3 - под рыжего бородача подключен');
});