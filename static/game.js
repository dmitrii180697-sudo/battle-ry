let isAnimating = false;

function findHeroImg() {
    // Ищем твоего героя всеми способами
    let hero = document.getElementById('hero-img');
    if (hero) return hero;
    // Если id нет - ищем по картинкам боя
    const imgs = document.querySelectorAll('img');
    for (let img of imgs) {
        if (img.src.includes('warrior') || img.src.includes('anim_') || img.src.includes('ancient')) {
            return img;
        }
    }
    // Если не нашли - берем правую картинку (твой герой справа)
    const battleImgs = document.querySelectorAll('div img, .battle img, img');
    if (battleImgs.length >= 2) return battleImgs[1]; // правый - это ты
    return battleImgs[0];
}

function findEnemyImg() {
    let enemy = document.getElementById('enemy-img');
    if (enemy) return enemy;
    const imgs = document.querySelectorAll('img');
    // Враг слева
    for (let img of imgs) {
        if (img.src.includes('barbarian') || img.src.includes('enemy')) return img;
    }
    const battleImgs = document.querySelectorAll('div img, .battle img, img');
    if (battleImgs.length >= 2) return battleImgs[0];
    return null;
}

function playHitAnimation(isSuper, callback){
    if(isAnimating) return;
    isAnimating=true;
    const hero = findHeroImg();
    const enemy = findEnemyImg();
    console.log('Бью! Герой:', hero?.src);

    if(!hero) { isAnimating=false; return; }
    
    hero.style.transition='all 0.12s ease-out';
    hero.src='/static/anim_raise.png'; // ЗАМАХ
    hero.style.transform='translateX(-15px) scale(1.05)';
    
    setTimeout(()=>{
        hero.src='/static/anim_hit.png'; // УДАР ПАЛКОЙ ПО ГОЛОВЕ
        if(isSuper){
            hero.style.transform='translateX(-50px) translateY(15px) scale(1.25) rotate(-15deg)';
        } else {
            hero.style.transform='translateX(-35px) translateY(10px) scale(1.15) rotate(-10deg)';
        }
        if(enemy) {
            enemy.style.transition='all 0.1s';
            enemy.style.animation='shake 0.5s ease-out';
            enemy.style.transform='translateX(10px)';
            setTimeout(()=>{ enemy.style.transform='translateX(0)'; }, 100);
        }
        setTimeout(()=>{
            hero.style.transition='all 0.25s ease-in';
            hero.style.transform='translateX(0) scale(1)';
            hero.src='/static/ancient_warrior.png'; // возвращаем обратно
            if(enemy) enemy.style.animation='';
            isAnimating = false;
            if(callback) callback();
        }, 500);
    }, 150);
}

const style=document.createElement('style');
style.innerHTML=`
@keyframes shake{
  0%,100%{transform:translateX(0)}
  25%{transform:translateX(-10px) rotate(-2deg)}
  75%{transform:translateX(10px) rotate(2deg)}
}
`;
document.head.appendChild(style);

// Вешаем на кнопки боя
document.addEventListener('DOMContentLoaded', ()=>{
    // Находим кнопки УДАР по тексту
    const checkBtn = setInterval(()=>{
        const btns = document.querySelectorAll('button, div[onclick], img[onclick]');
        btns.forEach(b=>{
            const txt = (b.textContent || b.innerText || '').toLowerCase();
            if(txt.includes('удар') || b.id?.toLowerCase().includes('attack')){
                if(!b.dataset.hitBound){
                    b.dataset.hitBound='1';
                    b.addEventListener('click', ()=>{ playHitAnimation(false); });
                }
            }
        });
    }, 500);
    
    // Также ловим клик по всему документу на кнопку с иконкой мечей
    document.addEventListener('click', (e)=>{
        const t = e.target;
        if(t.closest && t.closest('button')){
            const btn = t.closest('button');
            if(btn.textContent.includes('⚔') || btn.innerHTML.includes('attack') || btn.textContent.toLowerCase().includes('удар')){
                playHitAnimation(false);
            }
        }
    });
    
    console.log('Удар палкой подключен! Версия 2');
});