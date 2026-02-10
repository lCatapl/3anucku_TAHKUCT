// ⚔️ БЫСТРЫЙ БОЙ
async function quickBattle() {
    const btn = event.target;
    btn.disabled = true;
    btn.textContent = '⚔️ БОЕМ...';
    btn.classList.add('tank-shake');
    
    try {
        const response = await fetch('/battle', { method: 'POST' });
        const data = await response.json();
        
        if (data.win) {
            alert(`🎉 ПОБЕДА!\n💰 Золото: +${data.reward_gold}\n🪙 Серебро: +${data.reward_silver}\n⭐ Очки: +${data.reward_points}\n\nВаш танк: ${data.player_tank}\nВраг: ${data.enemy_tank}`);
        } else {
            alert(`💥 ПОРАЖЕНИЕ!\n💰 Золото: +${data.reward_gold}\n🪙 Серебро: +${data.reward_silver}\n⭐ Очки: +${data.reward_points}`);
        }
        location.reload();
    } catch (error) {
        alert('❌ Ошибка боя!');
    } finally {
        btn.disabled = false;
        btn.textContent = '⚔️ Быстрый бой';
        btn.classList.remove('tank-shake');
    }
}

// 🎁 ЕЖЕДНЕВКА
async function claimDaily() {
    try {
        const response = await fetch('/daily');
        const data = await response.json();
        alert(data.message);
        location.reload();
    } catch (error) {
        alert('❌ Ошибка получения награды!');
    }
}

// 🔄 АВТООБНОВЛЕНИЕ
setInterval(() => location.reload(), 30000); // каждые 30 сек
