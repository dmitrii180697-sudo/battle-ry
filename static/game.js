let isAnimating = false;
function playHitAnimation(isSuper, callback){
    if(isAnimating) return;
    isAnimating=true;
    const hero=document.getElementById('hero-img');
    const enemy=document.getElementById('enemy-img');
    const dmg=document.getElementById('dmg-float-enemy');
    if(!hero || !enemy) { isAnimating=false; return; }
    
    hero.style.transition='all 0.12s ease-out';
    hero.src='/static/anim_raise.png';
    hero.style.transform='translateX(-15px) scale(1.05)';
    setTimeout(()=>{
        hero.src='/static/anim_hit.png';
        if(isSuper){
            hero.style.transform='translateX(50px) translateY(15px) scale(1.25) rotate(15deg)';
            hero.style.filter='drop-shadow(0 0 15px #ff0) brightness(1.3)';
            if(dmg) {
                dmg.style.fontSize='58px';
                dmg.style.color='#ffff00';
            }
        } else {
            hero.style.transform='translateX(35px) translateY(10px) scale(1.15) rotate(10deg)';
        }
        if(enemy) enemy.style.animation='shake 0.5s ease-out';
        if(dmg) {
            dmg.innerText='-' + (typeof lastDmg !== 'undefined' ? lastDmg : '5');
            dmg.classList.add('show');
            if(isSuper) dmg.classList.add('super');
        }
        setTimeout(()=>{
            hero.style.transition='all 0.25s ease-in';
            hero.style.transform='translateX(0) scale(1)';
            hero.style.filter='';
            if(hero) hero.src='/static/ancient_warrior.png'; // возвращаем в обычную стойку, у тебя файл так называется
            if(dmg) {
                setTimeout(()=>{
                    dmg.classList.remove('show','super');
                }, 600);
            }
            isAnimating = false; // ВОТ ЭТОГО У ТЕБЯ НЕ БЫЛО - из-за этого не бил второй раз
            if(callback) callback();
        }, 500);
    }, 120);
}
    },130);
}
function doHit(isSuper){
    if(isSuper){
        const btn=document.getElementById('super-btn');
        if(btn.disabled) return;
        document.getElementById('action-input').value='super';
    } else {
        document.getElementById('action-input').value='hit';
    }
    playHitAnimation(isSuper, ()=>{ document.getElementById('hit-form').submit(); });
}
const style=document.createElement('style');
style.innerHTML=`@keyframes shake{0%{transform:scaleX(-1) translateX(0)}20%{transform:scaleX(-1) translateX(-15px)}40%{transform:scaleX(-1) translateX(15px) translateY(-5px)}60%{transform:scaleX(-1) translateX(-10px)}80%{transform:scaleX(-1) translateX(10px)}100%{transform:scaleX(-1) translateX(0)}} #enemy-img{transform:scaleX(-1)!important} .dmg{position:absolute;top:40%;left:20%;font-size:38px;font-weight:900;color:#ff2222;text-shadow:2px 2px 0 #000;opacity:0;transform:translateY(20px) scale(0.5);transition:all 0.35s cubic-bezier(0.175,0.885,0.32,1.275);pointer-events:none} .dmg.show{opacity:1;transform:translateY(-60px) scale(1.2)} .dmg.super{color:#ffff00!important;text-shadow:0 0 10px #ff0,2px 2px 0 #000!important}`;
document.head.appendChild(style);
// ПРИНУДИТЕЛЬНО ВЕШАЕМ УДАР НА КНОПКУ
document.addEventListener('DOMContentLoaded', ()=>{
    const btns = document.querySelectorAll('button');
    btns.forEach(b=>{
        if(b.textContent.toLowerCase().includes('удар') || b.textContent.toLowerCase().includes('attack') || b.textContent.toLowerCase().includes('бит')){
            b.addEventListener('click', ()=>{ playHitAnimation(false); });
        }
    });
    console.log('Удар палкой подключен!');
});