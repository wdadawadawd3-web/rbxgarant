// ==========================================
// ROBLOX GUARANTOR TG WEBAPP LOGIC
// ==========================================

// Global App State
const state = {
  activeCurrency: 'stars', // 'stars' or 'robux'
  balances: {
    stars: 850,
    robux: 2500
  },
  depositAmount: 0,
  deals: [
    // Pre-populate with one completed deal for demonstration
    {
      id: "DX-8492",
      title: "FR Frost Dragon (Adopt Me)",
      amount: "1,200 R$",
      type: "robux",
      status: "completed",
      statusText: "Завершена",
      partner: "RobloxTrader_99"
    }
  ]
};

// Initialize Telegram WebApp
const tg = window.Telegram?.WebApp;

document.addEventListener("DOMContentLoaded", () => {
  if (tg) {
    tg.ready();
    tg.expand();
    // Set header color to match our header dark theme
    if (tg.setHeaderColor) {
      tg.setHeaderColor('#151718');
    }
    
    // Fetch Telegram User Info
    const user = tg.initDataUnsafe?.user;
    if (user) {
      if (user.photo_url) {
        document.getElementById('user-avatar').src = user.photo_url;
        document.getElementById('profile-avatar-img').src = user.photo_url;
      }
      const displayUsername = user.username ? `@${user.username}` : `${user.first_name} ${user.last_name || ''}`;
      document.getElementById('username').textContent = displayUsername;
      document.getElementById('profile-username').textContent = displayUsername;
    }
  }

  // Initialize UI
  updateBalanceDisplay();
  renderDeals();
  attachGlobalClickSounds();
});

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
    
    // Quick Roblox-style cartoonish UI click/pop
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
    console.warn("Audio Context blocked or not supported yet: ", e);
  }
}

// Play a success sound
function playSuccessSound() {
  const soundEnabled = document.getElementById('sound-toggle')?.checked;
  if (soundEnabled === false) return;

  try {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!AudioContext) return;
    
    const ctx = new AudioContext();
    
    // Sound 1 (Low note)
    const osc1 = ctx.createOscillator();
    const gain1 = ctx.createGain();
    osc1.type = 'sine';
    osc1.frequency.setValueAtTime(330, ctx.currentTime); // E4
    osc1.frequency.setValueAtTime(440, ctx.currentTime + 0.08); // A4
    gain1.gain.setValueAtTime(0.1, ctx.currentTime);
    gain1.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.25);
    osc1.connect(gain1);
    gain1.connect(ctx.destination);
    osc1.start();
    osc1.stop(ctx.currentTime + 0.25);
    
    // Sound 2 (High note, slightly delayed)
    setTimeout(() => {
      const osc2 = ctx.createOscillator();
      const gain2 = ctx.createGain();
      osc2.type = 'sine';
      osc2.frequency.setValueAtTime(554, ctx.currentTime); // C#5
      osc2.frequency.setValueAtTime(659, ctx.currentTime + 0.08); // E5
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

// Attach sound to all buttons and tabs
function attachGlobalClickSounds() {
  document.querySelectorAll('button, .nav-item, .currency-tab, .faq-question').forEach(el => {
    el.addEventListener('click', () => {
      playClickSound();
    });
  });
}

// ==========================================
// NAVIGATION & SCREENS
// ==========================================
function switchTab(tabId) {
  // Hide all screens
  document.querySelectorAll('.app-screen').forEach(screen => {
    screen.classList.remove('active');
  });
  
  // Deactivate all nav items
  document.querySelectorAll('.nav-item').forEach(item => {
    item.classList.remove('active');
  });
  
  // Show target screen
  const targetScreen = document.getElementById(`screen-${tabId}`);
  if (targetScreen) {
    targetScreen.classList.add('active');
  }
  
  // Activate target nav item
  const targetNav = document.getElementById(`nav-${tabId}`);
  if (targetNav) {
    targetNav.classList.add('active');
  }

  // Auto-scroll to top of screen
  document.querySelector('.content-area').scrollTop = 0;
}

// ==========================================
// CURRENCY MANAGEMENT
// ==========================================
function switchCurrency(currency) {
  state.activeCurrency = currency;
  
  // Toggle tab active states
  document.getElementById('tab-stars').classList.toggle('active', currency === 'stars');
  document.getElementById('tab-robux').classList.toggle('active', currency === 'robux');
  
  updateBalanceDisplay();
}

function updateBalanceDisplay() {
  const balanceEl = document.getElementById('balance-value');
  
  // Simple fade-out, change, fade-in animation
  balanceEl.style.transform = 'scale(0.8)';
  balanceEl.style.opacity = '0';
  
  setTimeout(() => {
    if (state.activeCurrency === 'stars') {
      balanceEl.textContent = `${formatNumber(state.balances.stars)} ⭐️`;
      balanceEl.classList.remove('robux-style');
    } else {
      balanceEl.textContent = `${formatNumber(state.balances.robux)} R$`;
      balanceEl.classList.add('robux-style');
    }
    balanceEl.style.transform = 'scale(1)';
    balanceEl.style.opacity = '1';
  }, 150);
}

function formatNumber(num) {
  return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

// ==========================================
// FAQ ACCORDION
// ==========================================
function toggleFaq(questionEl) {
  const item = questionEl.parentElement;
  const isOpen = item.classList.contains('open');
  
  // Close all other items
  document.querySelectorAll('.faq-item').forEach(otherItem => {
    if (otherItem !== item) {
      otherItem.classList.remove('open');
    }
  });
  
  // Toggle current item
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
    const isStars = state.activeCurrency === 'stars';
    const currencyName = isStars ? 'Telegram Stars ⭐️' : 'Robux R$';
    const symbol = isStars ? '⭐️' : 'R$';
    
    html = `
      <div class="modal-title">
        <span>Пополнить баланс</span>
      </div>
      <div class="modal-body">
        Введите сумму для пополнения вашего счета в <strong>${currencyName}</strong>. Пополнение моментальное.
      </div>
      <div class="modal-input-group">
        <label class="modal-label">Сумма пополнения</label>
        <div class="modal-input-wrapper">
          <input type="number" id="input-deposit-amount" class="modal-input" placeholder="0" min="1">
          <span class="modal-input-badge">${symbol}</span>
        </div>
      </div>
      <div class="modal-buttons">
        <button class="roblox-btn btn-grey" onclick="closeModal()">Отмена</button>
        <button class="roblox-btn btn-green" onclick="handleDepositSubmit()"><span class="btn-inner">Пополнить</span></button>
      </div>
    `;
  } 
  else if (type === 'withdraw') {
    const isStars = state.activeCurrency === 'stars';
    const currencyName = isStars ? 'Telegram Stars ⭐️' : 'Robux R$';
    const maxVal = isStars ? state.balances.stars : state.balances.robux;
    const symbol = isStars ? '⭐️' : 'R$';
    
    html = `
      <div class="modal-title">
        <span>Вывести средства</span>
      </div>
      <div class="modal-body">
        Укажите сумму для вывода. Доступный баланс: <strong>${formatNumber(maxVal)} ${symbol}</strong>.
      </div>
      <div class="modal-input-group">
        <label class="modal-label">Сумма вывода</label>
        <div class="modal-input-wrapper">
          <input type="number" id="input-withdraw-amount" class="modal-input" placeholder="0" max="${maxVal}" min="1">
          <span class="modal-input-badge">${symbol}</span>
        </div>
      </div>
      <div class="modal-input-group">
        <label class="modal-label">Реквизиты получателя</label>
        <input type="text" id="input-withdraw-destination" class="modal-input" placeholder="${isStars ? '@telegram_username' : 'Roblox Username / Gamepass ID'}">
      </div>
      <div class="modal-buttons">
        <button class="roblox-btn btn-grey" onclick="closeModal()">Отмена</button>
        <button class="roblox-btn btn-blue" onclick="handleWithdrawSubmit()"><span class="btn-inner">Вывести</span></button>
      </div>
    `;
  } 
  else if (type === 'new-deal') {
    const isStars = state.activeCurrency === 'stars';
    const symbol = isStars ? '⭐️' : 'R$';
    
    html = `
      <div class="modal-title">
        <svg class="briefcase-icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style="width:24px;height:24px;">
          <rect x="3" y="6" width="18" height="14" rx="3" fill="#FFA502" stroke="#111" stroke-width="2"/>
          <path d="M9 6V4a2 2 0 012-2h2a2 2 0 012 2v2" stroke="#111" stroke-width="2"/>
          <path d="M3 11h18" stroke="#111" stroke-width="2"/>
        </svg>
        <span>Новая сделка</span>
      </div>
      <div class="modal-body">
        Создайте безопасную сделку. Бот выступит гарантом безопасности.
      </div>
      
      <div class="modal-input-group">
        <label class="modal-label">Моя роль в сделке</label>
        <div class="currency-tabs" style="margin-bottom:0;">
          <button id="role-buyer" class="currency-tab active" onclick="setDealRole('buyer')">
            <span class="tab-content" style="font-size:12px;">Я Покупатель</span>
          </button>
          <button id="role-seller" class="currency-tab" onclick="setDealRole('seller')">
            <span class="tab-content" style="font-size:12px;">Я Продавец</span>
          </button>
        </div>
      </div>
      
      <div class="modal-input-group">
        <label class="modal-label">Никнейм второго участника</label>
        <input type="text" id="deal-partner" class="modal-input" placeholder="@username или ник Roblox">
      </div>
      
      <div class="modal-input-group">
        <label class="modal-label">Описание товара (Pet, Fruit, Item)</label>
        <input type="text" id="deal-item" class="modal-input" placeholder="Например: FR Frost Dragon">
      </div>

      <div class="modal-input-group">
        <label class="modal-label">Сумма сделки</label>
        <div class="modal-input-wrapper">
          <input type="number" id="deal-amount" class="modal-input" placeholder="0">
          <span class="modal-input-badge">${symbol}</span>
        </div>
      </div>

      <div class="modal-buttons">
        <button class="roblox-btn btn-grey" onclick="closeModal()">Отмена</button>
        <button class="roblox-btn btn-green" onclick="handleCreateDeal()"><span class="btn-inner">Начать</span></button>
      </div>
    `;
  }
  else if (type === 'deposit-info') {
    html = `
      <div class="modal-title">
        <span>Информация о депозитах</span>
      </div>
      <div class="modal-body" style="font-size: 13px;">
        <p style="margin-bottom: 10px;"><strong>Депозит</strong> — это сумма обеспечения, которую вы вносите в систему для подтверждения своей надежности как продавца или покупателя.</p>
        <p>Чем выше ваш депозит, тем больше доверия от других пользователей и тем более крупные сделки вы можете проводить без дополнительных проверок.</p>
      </div>
      <div class="modal-buttons">
        <button class="roblox-btn btn-green" style="width:100%;" onclick="closeModal()"><span class="btn-inner">Понятно!</span></button>
      </div>
    `;
  }
  else if (type === 'promo') {
    html = `
      <div class="modal-title">
        <span>Безопасные сделки 24/7</span>
      </div>
      <div class="modal-body" style="font-size:13px; text-align:left;">
        <p style="margin-bottom: 8px;">🛡️ <strong>Полная защита от мошенничества:</strong> Средства покупателя блокируются на балансе гаранта и переводятся продавцу только после обоюдного подтверждения выполнения условий сделки.</p>
        <p style="margin-bottom: 8px;">⚡ <strong>Быстрые выплаты:</strong> Вывод Robux и Telegram Stars производится в автоматическом или полуавтоматическом режиме.</p>
        <p>⭐ <strong>Рейтинговая система:</strong> Получайте отзывы после каждой успешной сделки и повышайте свой авторитет в сообществе Roblox.</p>
      </div>
      <div class="modal-buttons">
        <button class="roblox-btn btn-green" style="width:100%;" onclick="closeModal()"><span class="btn-inner">Отлично</span></button>
      </div>
    `;
  }

  modalPlaceholder.innerHTML = html;
  modalContainer.classList.add('active');
  
  // Re-attach sounds to newly created modal buttons
  attachGlobalClickSounds();
}

function closeModal() {
  modalContainer.classList.remove('active');
}

// Close modal when clicking on overlay background
modalContainer.addEventListener('click', (e) => {
  if (e.target === modalContainer) {
    closeModal();
  }
});

// ==========================================
// TRANSACTION FORM SUBMISSIONS (Simulated)
// ==========================================

function handleDepositSubmit() {
  const amountInput = document.getElementById('input-deposit-amount');
  const amount = parseInt(amountInput?.value || '0', 10);
  
  if (amount <= 0 || isNaN(amount)) {
    alert("Пожалуйста, введите корректную сумму.");
    return;
  }
  
  // Update state
  state.balances[state.activeCurrency] += amount;
  updateBalanceDisplay();
  closeModal();
  playSuccessSound();
  
  // Show TG Alert if available
  if (tg) {
    tg.showAlert(`Баланс успешно пополнен на ${amount} ${state.activeCurrency === 'stars' ? 'Stars' : 'Robux'}!`);
  } else {
    alert(`Баланс успешно пополнен на ${amount} ${state.activeCurrency === 'stars' ? 'Stars' : 'Robux'}!`);
  }
}

function handleWithdrawSubmit() {
  const amountInput = document.getElementById('input-withdraw-amount');
  const destInput = document.getElementById('input-withdraw-destination');
  const amount = parseInt(amountInput?.value || '0', 10);
  const destination = destInput?.value.trim();
  const maxVal = state.balances[state.activeCurrency];
  
  if (amount <= 0 || isNaN(amount)) {
    alert("Пожалуйста, введите корректную сумму.");
    return;
  }
  if (amount > maxVal) {
    alert("Недостаточно средств на балансе.");
    return;
  }
  if (!destination) {
    alert("Пожалуйста, введите реквизиты вывода.");
    return;
  }
  
  // Update state
  state.balances[state.activeCurrency] -= amount;
  updateBalanceDisplay();
  closeModal();
  playSuccessSound();
  
  const currencySymbol = state.activeCurrency === 'stars' ? '⭐️' : 'R$';
  
  if (tg) {
    tg.showAlert(`Заявка на вывод ${amount} ${currencySymbol} на реквизиты ${destination} успешно создана!`);
  } else {
    alert(`Заявка на вывод ${amount} ${currencySymbol} на реквизиты ${destination} успешно создана!`);
  }
}

// Modal helper to toggle role inside create deal modal
let currentDealRole = 'buyer';
function setDealRole(role) {
  currentDealRole = role;
  document.getElementById('role-buyer').classList.toggle('active', role === 'buyer');
  document.getElementById('role-seller').classList.toggle('active', role === 'seller');
}

function handleCreateDeal() {
  const partner = document.getElementById('deal-partner')?.value.trim();
  const item = document.getElementById('deal-item')?.value.trim();
  const amount = parseInt(document.getElementById('deal-amount')?.value || '0', 10);
  
  if (!partner) {
    alert("Введите никнейм второго участника сделки.");
    return;
  }
  if (!item) {
    alert("Введите описание передаваемого товара.");
    return;
  }
  if (amount <= 0 || isNaN(amount)) {
    alert("Введите корректную сумму сделки.");
    return;
  }

  const currencySymbol = state.activeCurrency === 'stars' ? '⭐️' : 'R$';
  
  // Create new deal object
  const newDeal = {
    id: `DX-${Math.floor(1000 + Math.random() * 9000)}`,
    title: item,
    amount: `${formatNumber(amount)} ${currencySymbol}`,
    type: state.activeCurrency,
    status: "active",
    statusText: "Ожидает оплаты",
    partner: partner
  };

  // Add to state
  state.deals.unshift(newDeal);
  
  // Render and switch to deals tab
  renderDeals();
  closeModal();
  playSuccessSound();
  switchTab('deals');
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
        <button class="roblox-btn btn-green btn-small" onclick="switchTab('main')">
          <span class="btn-inner">Создать сделку</span>
        </button>
      </div>
    `;
    return;
  }
  
  let html = '';
  state.deals.forEach(deal => {
    const badgeClass = deal.status === 'active' ? 'status-active' : 'status-completed';
    const currencyIcon = deal.type === 'stars' 
      ? `<span style="color:#FFD700">⭐️</span>` 
      : `<span style="color:#C1C5C9; font-weight:bold">R$</span>`;

    html += `
      <div class="roblox-panel deal-card">
        <div class="deal-info">
          <span class="deal-id">${deal.id} • С кем: ${deal.partner}</span>
          <span class="deal-title">${deal.title}</span>
          <span class="deal-amount-val" style="font-weight:700; font-size:16px;">
            ${deal.amount}
          </span>
        </div>
        <div>
          <span class="deal-status-badge ${badgeClass}">${deal.statusText}</span>
        </div>
      </div>
    `;
  });
  
  container.innerHTML = html;
  
  // Attach sound trigger to newly rendered buttons in this screen if any
  attachGlobalClickSounds();
}
