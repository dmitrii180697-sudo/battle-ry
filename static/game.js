// === BATTLE ANIMATION A ===
let isAnimating = false;

function playHitAnimation(callback) {
    if(isAnimating) return;
    isAnimating = true;
    
    const hero = document.getElementById('hero-img');
    const enemy = document.getElementById('enemy-img');
    const dmgText = document.getElementById('dmg-float');
    
    // 1. Замах
    hero.src = '/static/anim_raise.png';
    hero.style.transform = 'translateX(-20px) scale(1.1)';
    hero.style.transition = '0.15s';
    
    setTimeout(() => {
        // 2. Удар
        hero.src = '/static/anim_hit.png';
        hero.style.transform = 'translateX(40px) scale(1.15)';
        
        // Тряска врага + цифра
        enemy.style.animation = 'shake 0.3s';
        let dmg = Math.floor(Math.random()*5)+3; // для вида, реальный урон с сервера
        dmgText.innerText = '-' + dmg;
        dmgText.style.opacity = '1';
        dmgText.style.transform = 'translateY(-60px)';
        
        setTimeout(() => {
            // 3. Возврат
            hero.src = '/static/barbarian_game_size.png';
            hero.style.transform = 'translateX(0) scale(1)';
            dmgText.style.opacity = '0';
            dmgText.style.transform = 'translateY(0)';
            enemy.style.animation = '';
            isAnimating = false;
            if(callback) callback();
        }, 300);
    }, 150);
}

function doHit() {
    playHitAnimation(() => {
        // После анимации отправляем на сервер
        document.getElementById('hit-form').submit();
    });
}

// CSS для тряски
const style = document.createElement('style');
style.innerHTML = `
@keyframes shake {
  0% { transform: translateX(0); }
  25% { transform: translateX(-8px) rotate(-2deg); }
  50% { transform: translateX(8px) rotate(2deg); }
  75% { transform: translateX(-5px); }
  100% { transform: translateX(0); }
}
#dmg-float {
  position:absolute; top:50%; left:60%; 
  font-size:32px; font-weight:bold; color:#ff2222;
  text-shadow: 2px 2px 0 #000;
  opacity:0; transition: all 0.4s ease-out;
  pointer-events:none;
}
`;
document.head.appendChild(style);
