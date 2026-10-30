let isAnimating = false;

function playHitAnimation(callback) {
    if(isAnimating) return;
    isAnimating = true;
    
    const hero = document.getElementById('hero-img');
    const enemy = document.getElementById('enemy-img');
    const dmgText = document.getElementById('dmg-float');
    
    // ПЛАВНОСТЬ - добавляем transition
    hero.style.transition = 'all 0.12s ease-out';
    
    // 1. Замах - плавно назад
    hero.src = '/static/anim_raise.png';
    hero.style.transform = 'translateX(-15px) scale(1.05)';
    
    setTimeout(() => {
        // 2. Удар - плавно вперед
        hero.src = '/static/anim_hit.png';
        hero.style.transform = 'translateX(35px) scale(1.1)';
        
        // Враг получает - трясется и смотрит на тебя
        enemy.style.animation = 'shake 0.4s ease-out';
        enemy.style.transform = 'scaleX(-1)'; // ВОТ ЭТО - смотрит влево на тебя!
        
        dmgText.innerText = '-' + (Math.floor(Math.random()*5)+3);
        dmgText.classList.add('show');
        
        setTimeout(() => {
            // 3. Плавный возврат на место
            hero.style.transition = 'all 0.25s ease-in';
            hero.src = '/static/barbarian_game_size.png';
            hero.style.transform = 'translateX(0) scale(1)';
            
            dmgText.classList.remove('show');
            enemy.style.animation = '';
            // Оставляем врага перевернутым чтобы всегда смотрел на тебя
            enemy.style.transform = 'scaleX(-1)'; 
            
            isAnimating = false;
            if(callback) callback();
        }, 350);
    }, 130);
}

function doHit() {
    playHitAnimation(() => {
        document.getElementById('hit-form').submit();
    });
}

const style = document.createElement('style');
style.innerHTML = `
@keyframes shake {
  0% { transform: scaleX(-1) translateX(0); }
  20% { transform: scaleX(-1) translateX(-10px) translateY(-3px); }
  40% { transform: scaleX(-1) translateX(10px) translateY(3px); }
  60% { transform: scaleX(-1) translateX(-6px); }
  80% { transform: scaleX(-1) translateX(6px); }
  100% { transform: scaleX(-1) translateX(0); }
}
#hero-img {
  transition: all 0.15s ease-out;
  will-change: transform;
}
#enemy-img {
  transform: scaleX(-1); /* СРАЗУ смотрит на тебя! */
  transition: transform 0.2s;
  will-change: transform;
  filter: drop-shadow(0 0 8px black);
}
#dmg-float {
  position:absolute; top:40%; left:20%; 
  font-size:36px; font-weight:bold; color:#ff2222;
  text-shadow: 2px 2px 0 #000, -1px -1px 0 #000;
  opacity:0; 
  transform: translateY(20px) scale(0.5);
  transition: all 0.35s cubic-bezier(0.175, 0.885, 0.32, 1.275);
  pointer-events:none;
}
#dmg-float.show {
  opacity:1;
  transform: translateY(-50px) scale(1.2);
}
`;
document.head.appendChild(style);

// Сразу при загрузке переворачиваем врага чтобы смотрел на тебя
document.addEventListener('DOMContentLoaded', () => {
    const enemy = document.getElementById('enemy-img');
    if(enemy) enemy.style.transform = 'scaleX(-1)';
});
