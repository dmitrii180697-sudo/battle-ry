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
        } else {
            hero.style.transform='translateX(35px) translateY(10px) scale(1.15) rotate(10deg)';
        }
        if(enemy) enemy.style.animation='shake 0.5s ease-out';
        if(dmg) {
            dmg.innerText='-5';
            dmg.classList.add('show');
        }
        setTimeout(()=>{
            hero.style.transition='all 0.25s ease-in';
            hero.style.transform='translateX(0) scale(1)';
            hero.style.filter='';
            hero.src='/static/ancient_warrior.png';
            if(enemy) enemy.style.animation='';
            if(dmg) {
                setTimeout(()=>{ dmg.classList.remove('show'); }, 600);
            }
            isAnimating = false;
            if(callback) callback();
        }, 500);
    }, 120);
}

// Тряска врага и вылет -5
const style=document.createElement('style');
style.innerHTML=`
@keyframes shake{
  0%,100%{transform:translateX(0)}
  25%{transform:translateX(-10px) rotate(-2deg)}
  75%{transform:translateX(10px) rotate(2deg)}
}
#dmg-float-enemy{position:absolute; top:40%; left:55%; font-size:42px; color:yellow; font-weight:bold; opacity:0; pointer-events:none;}
#dmg-float-enemy.show{animation:flyUp 0.7s forwards;}
@keyframes flyUp{
  0%{transform:translateY(0); opacity:1}
  100%{transform:translateY(-70px); opacity:0}
}
`;
document.head.appendChild(style);

// Вешаем удар на все кнопки удара
document.addEventListener('DOMContentLoaded', ()=>{
    const btns = document.querySelectorAll('button, .btn-attack, #attack-btn');
    btns.forEach(b=>{
        b.addEventListener('click', ()=>{
            playHitAnimation(false);
        });
    });
    console.log('Удар палкой подключен!');
});