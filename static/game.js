let isAnimating = false;

function playHitAndThenSubmit(form) {
    if (isAnimating) return;
    isAnimating = true;
    
    // Ищем твоего героя - правая картинка с warrior
    let hero = null;
    const allImgs = document.querySelectorAll('img');
    allImgs.forEach(img => {
        if (img.src.includes('warrior') || img.src.includes('ancient')) {
            hero = img;
        }
    });
    // Если не нашли по имени - берем вторую картинку (ты справа)
    if (!hero && allImgs.length >= 2) {
        hero = allImgs[allImgs.length - 1];
    }

    if (!hero) {
        // Если героя не нашли - просто отправляем форму
        form.submit();
        return;
    }

    console.log('Бью палкой!');
    hero.style.transition = 'all 0.12s ease-out';
    hero.src = '/static/anim_raise.png'; // ЗАМАХ
    hero.style.transform = 'translateX(-15px) scale(1.05)';

    setTimeout(() => {
        hero.src = '/static/anim_hit.png'; // УДАР ПО ГОЛОВЕ
        hero.style.transform = 'translateX(-35px) translateY(10px) scale(1.15) rotate(-8deg)';

        // Ждем 500мс чтобы увидеть удар, потом отправляем на сервер
        setTimeout(() => {
            hero.src = '/static/ancient_warrior.png'; // возвращаем обратно
            hero.style.transform = 'translateX(0) scale(1)';
            isAnimating = false;
            form.submit();
        }, 500);
    }, 150);
}

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', (e) => {
            const btn = e.submitter || form.querySelector('button');
            const mInput = form.querySelector('input[name="m"]');
            const mValue = mInput ? mInput.value : (btn ? btn.value : '');

            // Только для удара
            if (mValue === 'hit' || (btn && btn.textContent.toLowerCase().includes('удар'))) {
                e.preventDefault();
                playHitAndThenSubmit(form);
            }
        });
    });
    console.log('Удар с анимацией подключен!');
});