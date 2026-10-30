let isAnimating = false;
function playHitAnimation(callback) {
    if(isAnimating) return;
    isAnimating = true;
    const hero = document.getElementById('hero-img');
    const enemy = document.getElementById('enemy-img');
    const dmgE = document.getElementById('dmg-float-enemy');
    const dmgH = document.getElementById('dmg-float-hero');
    
    hero.style.transition = 'all 0.12s ease-out';
    hero.src = '/static/anim_raise.png';
    hero.style.transform = 'translateX(-15px) scale(1.05)';
    
    setTimeout(() => {
        hero.src = '/static/anim_hit.png';
        hero.style.transform = 'translateX(35px) scale(1.1)';
        enemy.style.animation = 'shake 0.4s ease-out';
        dmgE.innerText = '-' + lastDmg;
        dmgE.classList.add('show');
        
        setTimeout(() => {
            hero.style.transition = 'all 0.25s ease-in';
            hero.src = '/static/barbarian_game_size.png';
            hero.style.transform = 'translateX(0) scale(1)';
            dmgE.classList.remove('show');
            
            if(lastHit === 'enemy'){
                setTimeout(()=>{
                    dmgH.innerText = '-' + lastEdmg;
                    dmgH.classList.add('show');
                    hero.style.animation = 'shakeHero 0.4s ease-out';
                    setTimeout(()=>{dmgH.classList.remove('show'); hero.style.animation='';}, 600);
                }, 200);
            }
            
            isAnimating = false;
            if(callback) callback();
        }, 350);
    }, 130);
}
function doHit(){ playHitAnimation(()=>{ document.getElementById('hit-form').submit(); }); }
const style = document.createElement('style');
style.innerHTML = `
@keyframes shake { 0%{transform:scaleX(-1) translateX(0)} 20%{transform:scaleX(-1) translateX(-10px) translateY(-3px)} 40%{transform:scaleX(-1) translateX(10px) translateY(3px)} 60%{transform:scaleX(-1) translateX(-6px)} 80%{transform:scaleX(-1) translateX(6px)} 100%{transform:scaleX(-1) translateX(0)} }
@keyframes shakeHero { 0%{transform:translateX(0)} 20%{transform:translateX(10px)} 40%{transform:translateX(-10px)} 60%{transform:translateX(6px)} 80%{transform:translateX(-6px)} 100%{transform:translateX(0)} }
#hero-img{transition:all 0.15s ease-out;will-change:transform}
#enemy-img{transform:scaleX(-1);transition:transform 0.2s;will-change:transform;filter:drop-shadow(0 0 10px black)}
.dmg{position:absolute; top:40%; left:20%; font-size:38px; font-weight:900; color:#ff2222; text-shadow:2px 2px 0 #000; opacity:0; transform:translateY(20px) scale(0.5); transition:all 0.35s cubic-bezier(0.175, 0.885, 0.32, 1.275); pointer-events:none}
.dmg.show{opacity:1; transform:translateY(-50px) scale(1.2)}
`;
document.head.appendChild(style);
document.addEventListener('DOMContentLoaded',()=>{const e=document.getElementById('enemy-img'); if(e) e.style.transform='scaleX(-1)'});
