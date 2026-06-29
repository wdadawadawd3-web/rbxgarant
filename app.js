// ==========================================
// ROBLOX GUARANTOR TG WEBAPP LOGIC (REAL BACKEND INTEGRATION)
// ==========================================

// Укажи здесь свой настоящий URL бэкенда на PythonAnywhere!
const BACKEND_URL = "https://robopo1.pythonanywhere.com"; 

// Global App State
const state = {
  activeCurrency: 'stars', // Строго Telegram Stars
  balances: {
    stars: 0
  },
  depositAmount: 0,
  deals: []
};

// Initialize Telegram WebApp
const tg = window.Telegram?.WebApp;

document.addEventListener("DOMContentLoaded", () => {
  if (tg) {
    tg.ready();
    tg.expand();
    if (tg.setHeaderColor) {
      tg.setHeaderColor('#151718');
    }
    
    // Получаем реальные данные пользователя Telegram
    const user = tg.initDataUnsafe?.user;
    if (user) {
      if (user.photo_url) {
        document.getElementById('user-avatar').src = user.photo_url;
        document.getElementById('profile-avatar-img').src = user.photo_url;
      }
      const displayUsername = user.username ? `@${user.username}` : `${user.first_name} ${user.last_name || ''}`;
      document.getElementById('username').textContent = displayUsername;
      document.getElementById('profile-username').textContent = displayUsername;
      
      // Загружаем реальный баланс и сделки с сервера для этого юзера
      loadUserDataFromServer(user.id);
    }
  }

  // Initialize UI
  updateBalanceDisplay();
  attachGlobalClickSounds();
});

// Функция загрузки данных с твоего сервера PythonAnywhere
async funсtion loadUserDataFromServer(userId) {
  try {
    const response = await fetch(`${BACKEND_URL}/api/user/${userId}`);
    if (response.ok) {
      const data = await response.json();
      state.balances.stars = data.balance || 0;
      state.deals = data.deals || [];
      updateBalanceDisplay();
      renderDeals();
    }
  } catch (error) {
    console.error("Ошибка загрузки данных с сервера:", error);
  }
}

// ==========================================
// AUDIO SYNTHESIS (Gaming Sound Effects)
// ==========================================
function playClickSound() {
  const soundEnabled = document.getElementById('sound-toggle')?.checked;
  if (soundEnabled === false) return;

  try {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!AudioContext) return;
    
    const ctx = new AudioContext();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    
    osc.type = 'sine';
    osc.frequency.setValueAtTime(580, ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(180, ctx.currentTime + 0.08);
    
    gain.gain.setValueAtTime(0.12, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.08);
    
    osc.connect(gain);
    gain.connect(ctx.destination);
    
    osc.start();
    osc.stop(ctx.currentTime + 0.08);
  } catch (e) {
    console.warn("Audio Context blocked: ", e);
  }
}

function playSuccessSound() {
  const soundEnabled = document.getElementById('sound-toggle')?.checked;
  if (soundEnabled === false) return;

  try {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!AudioContext) return;
    const ctx = new AudioContext();
    
    const osc1 = ctx.createOscillator();
    const gain1 = ctx.createGain();
    osc1.type = 'sine';
    osc1.frequency.setValueAtTime(330, ctx.currentTime);
    osc1.frequency.setValueAtTime(440, ctx.currentTime + 0.08);
    gain1.gain.setValueAtTime(0.1, ctx.currentTime);
    gain1.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.25);
    osc1.connect(gain1);
    gain1.connect(ctx.destination);
    osc1.start();
    osc1.stop(ctx.currentTime + 0.25);
    
    setTimeout(() => {
      const osc2 = ctx.createOscillator();
      const gain2 = ctx.createGain();
      osc2.type = 'sine';
      osc2.frequency.setValueAtTime(554, ctx.currentTime);
      osc2.frequency.setValueAtTime(659, ctx.currentTime + 0.08);
      gain2.gain.setValueAtTime(0.1, ctx.currentTime);
      gain2.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.25);
      osc2.connect(gain2);
      gain2.connect(ctx.destination);
      osc2.start();
      osc2.stop(ctx.currentTime + 0.25);
    }, 80);
  } catch (e) {
    console.warn(e);
  }
}

function attachGlobalClickSounds() {
  document.querySelectorAll('button, .nav-item, .currency-tab, .faq-question').forEach(el => {
    el.addEventListener('click', () => { playClickSound(); });
  });
}

// ==========================================
// NAVIGATION & SCREENS
// ==========================================
function switchTab(tabId) {
  document.querySelectorAll('.app-screen').forEach(screen => {
    screen.classList.remove('active');
  });
  document.querySelectorAll('.nav-item').forEach(item => {
    item.classList.remove('active');
  });
  const targetScreen = document.getElementById(`screen-${tabId}`);
  if (targetScreen) targetScreen.classList.add('active');
  
  const targetNav = document.getElementById(`nav-${tabId}`);
  if (targetNav) targetNav.classList.add('active');

  document.querySelector('.content-area').scrollTop = 0;
}

function updateBalanceDisplay() {
  const balanceEl = document.getElementById('balance-value');
  if (!balanceEl) return;
  balanceEl.style.transform = 'scale(0.8)';
  balanceEl.style.opacity = '0';
  
  setTimeout(() => {
    balanceEl.textContent = `${formatNumber(state.balances.stars)} ⭐️`;
    balanceEl.classList.remove('robux-style');
    balanceEl.style.transform = 'scale(1)';
    balanceEl.style.opacity = '1';
  }, 150);
}

function formatNumber(num) {
  return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

function toggleFaq(questionEl) {
  const item = questionEl.parentElement;
  const isOpen = item.classList.contains('open');
  document.querySelectorAll('.faq-item').forEach(otherItem => {
    if (otherItem !== item) otherItem.classList.remove('open');
  });
  item.classList.toggle('open', !isOpen);
}

// ==========================================
// MODAL MANAGEMENT
// ==========================================
const modalContainer = document.getElementById('modal-container');
const modalPlaceholder = document.getElementById('modal-content-placeholder');

function openModal(type) {
  let html = '';
  
  if (type === 'deposit') {
    html = `
      <div class="modal-title"><span>Пополнить баланс</span></div>
      <div class="modal-body">Введите количество Telegram Stars для покупки через официальный инвойс.</div>
      <div class="modal-input-group">
        <label class="modal-label">Сумма в Stars</label>
        <div class="modal-input-wrapper">
          <input type="number" id="input-deposit-amount" class="modal-input" placeholder="0" min="1">
          <span class="modal-input-badge">⭐️</span>
        </div>
      </div>
      <div class="modal-buttons">
        <button class="roblox-btn btn-grey" onclick="closeModal()">Отмена</button>
        <button class="roblox-btn btn-green" onclick="handleDepositSubmit()"><span class="btn-inner">Оплатить</span></button>
      </div>
    `;
  } 
  else if (type === 'withdraw') {
    const maxVal = state.balances.stars;
    html = `
      <div class="modal-title"><span>Вывести звезды</span></div>
      <div class="modal-body">Укажите сумму вывода Stars. Доступно: <strong>${formatNumber(maxVal)} ⭐️</strong>.</div>
      <div class="modal-input-group">
        <label class="modal-label">Сумма вывода</label>
        <div class="modal-input-wrapper">
          <input type="number" id="input-withdraw-amount" class="modal-input" placeholder="0" max="${maxVal}" min="1">
          <span class="modal-input-badge">⭐️</span>
        </div>
      </div>
      <div class="modal-input-group">
        <label class="modal-label">Ваш Telegram Юзернейм</label>
        <input type="text" id="input-withdraw-destination" class="modal-input" placeholder="@username">
      </div>
      <div class="modal-buttons">
        <button class="roblox-btn btn-grey" onclick="closeModal()">Отмена</button>
        <button class="roblox-btn btn-blue" onclick="handleWithdrawSubmit()"><span class="btn-inner">Вывести</span></button>
      </div>
    `;
  } 
  else if (type === 'new-deal') {
    html = `
      <div class="modal-title"><span>Новая сделка Roblox</span></div>
      <div class="modal-body">Создайте безопасную сделку. Бот заблокирует Звезды до подтверждения.</div>
      <div class="modal-input-group">
        <label class="modal-label">Никнейм второго участника (ТГ)</label>
        <input type="text" id="deal-partner" class="modal-input" placeholder="@username продавца">
      </div>
      <div class="modal-input-group">
        <label class="modal-label">Что покупаете (Предмет в Roblox)</label>
        <input type="text" id="deal-item" class="modal-input" placeholder="Например: FR Frost Dragon">
      </div>
      <div class="modal-input-group">
        <label class="modal-label">Стоимость сделки</label>
        <div class="modal-input-wrapper">
          <input type="number" id="deal-amount" class="modal-input" placeholder="0">
          <span class="modal-input-badge">⭐️</span>
        </div>
      </div>
      <div class="modal-buttons">
        <button class="roblox-btn btn-grey" onclick="closeModal()">Отмена</button>
        <button class="roblox-btn btn-green" onclick="handleCreateDeal()"><span class="btn-inner">Создать</span></button>
      </div>
    `;
  }

  modalPlaceholder.innerHTML = html;
  modalContainer.classList.add('active');
  attachGlobalClickSounds();
}

function closeModal() {
  modalContainer.classList.remove('active');
}

modalContainer.addEventListener('click', (e) => {
  if (e.target === modalContainer) closeModal();
});

// ==========================================
// REAL TRANSACTION SUBMISSIONS (API CALLS)
// ==========================================

async funсtion handleDepositSubmit() {
  const amountInput = document.getElementById('input-deposit-amount');
  const amount = parseInt(amountInput?.value || '0', 10);
  
  if (amount <= 0 || isNaN(amount)) {
    alert("Введите корректную сумму.");
    return;
  }
  
  const userId = tg.initDataUnsafe?.user?.id;
  
  try {
    // Отправляем запрос на бэкенд для генерации инвойса Telegram Stars
    const response = await fetch(`${BACKEND_URL}/api/deposit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId, amount: amount })
    });
    
    if (response.ok) {
      closeModal();
      // Закрываем WebApp и отправляем инвойс прямо в чат бота
      if (tg) tg.close(); 
    } else {
      alert("Ошибка при создании счета на оплату.");
    }
  } catch (err) {
    alert("Не удалось связаться с сервером.");
  }
}

async funсtion handleCreateDeal() {
  const partner = document.getElementById('deal-partner')?.value.trim();
  const item = document.getElementById('deal-item')?.value.trim();
  const amount = parseInt(document.getElementById('deal-amount')?.value || '0', 10);
  const userId = tg.initDataUnsafe?.user?.id;
  
  if (!partner || !item || amount <= 0 || isNaN(amount)) {
    alert("Заполните все поля корректно.");
    return;
  }

  if (amount > state.balances.stars) {
    alert("Недостаточно Telegram Stars на балансе для открытия сделки.");
    return;
  }

  try {
    // Отправляем запрос на создание реальной сделки в БД PythonAnywhere
    const response = await fetch(`${BACKEND_URL}/api/deals/create`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: userId,
        partner: partner,
        item: item,
        amount: amount
      })
    });

    if (response.ok) {
      // Обновляем данные на фронте
      loadUserDataFromServer(userId);
      closeModal();
      playSuccessSound();
      switchTab('deals');
    } else {
      const errData = await response.json();
      alert(errData.detail || "Ошибка при создании сделки.");
    }
  } catch (err) {
    alert("Ошибка сети при создании сделки.");
  }
}

// ==========================================
// RENDER DEALS LIST
// ==========================================
function renderDeals() {
  const container = document.querySelector('.deals-list');
  if (!container) return;
  
  if (state.deals.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">📁</div>
        <div class="empty-text">У вас пока нет активных сделок</div>
      </div>
    `;
    return;
  }
  
  let html = '';
  state.deals.forEach(deal => {
    const badgeClass = deal.status === 'active' ? 'status-active' : 'status-completed';
    html += `
      <div class="roblox-panel deal-card">
        <div class="deal-info">
          <span class="deal-id">ID: ${deal.id} • Участник: ${deal.partner}</span>
          <span class="deal-title">${deal.title}</span>
          <span class="deal-amount-val" style="font-weight:700; font-size:16px;">
            ${deal.amount} ⭐️
          </span>
        </div>
        <div>
          <span class="deal-status-badge ${badgeClass}">${deal.status_text}</span>
        </div>
      </div>
    `;
  });
  
  container.innerHTML = html;
  attachGlobalClickSounds();
}
