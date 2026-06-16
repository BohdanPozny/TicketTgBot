/**
 * bus_partner.js
 * Конструктор схеми салону автобуса для партнера
 */

const tg = window.Telegram?.WebApp;
const API_BASE = document.querySelector('meta[name="api-base"]')?.content || '';

let eventId = null;
let totalSeats = 40;
let seatsPerRow = 4;
let blockedSeats = new Set();
let departurCity = '';
let arrivalCity = '';

async function init() {
  tg?.ready();
  tg?.expand();

  const params = new URLSearchParams(window.location.search);
  eventId = parseInt(params.get('event_id'));

  if (!eventId) {
    showError('Невірні параметри');
    return;
  }

  try {
    const data = await fetch(`${API_BASE}/api/events/${eventId}/layout`).then(r => r.json());
    const cfg = data.layout_config || {};
    totalSeats = cfg.total_seats || 40;
    seatsPerRow = cfg.seats_per_row || 4;
    blockedSeats = new Set(cfg.blocked_seats || []);
    departurCity = cfg.departure_city || '';
    arrivalCity = cfg.arrival_city || '';

    document.getElementById('input-total').value = totalSeats;
    document.getElementById('input-rows').value = seatsPerRow;
    document.getElementById('input-departure').value = departurCity;
    document.getElementById('input-arrival').value = arrivalCity;
    document.getElementById('event-title').textContent = data.title || 'Рейс';
  } catch (e) {}

  renderBus();
}

function renderBus() {
  const busEl = document.getElementById('bus-layout');
  busEl.innerHTML = '';

  // Driver
  const frontRow = document.createElement('div');
  frontRow.className = 'bus-row bus-front';
  const driverBtn = document.createElement('button');
  driverBtn.className = 'seat seat--driver';
  driverBtn.disabled = true;
  driverBtn.textContent = '🚗';
  frontRow.appendChild(driverBtn);
  busEl.appendChild(frontRow);

  const leftSeats = Math.floor(seatsPerRow / 2);
  const rightSeats = seatsPerRow - leftSeats;
  let seatNum = 1;

  while (seatNum <= totalSeats) {
    const rowEl = document.createElement('div');
    rowEl.className = 'bus-row';

    for (let i = 0; i < leftSeats && seatNum <= totalSeats; i++, seatNum++) {
      rowEl.appendChild(createSeatBtn(seatNum));
    }

    const aisle = document.createElement('div');
    aisle.className = 'bus-aisle';
    rowEl.appendChild(aisle);

    for (let i = 0; i < rightSeats && seatNum <= totalSeats; i++, seatNum++) {
      rowEl.appendChild(createSeatBtn(seatNum));
    }

    busEl.appendChild(rowEl);
  }

  updateStats();
}

function createSeatBtn(seatNum) {
  const key = `seat_${seatNum}`;
  const btn = document.createElement('button');
  btn.className = `seat ${blockedSeats.has(key) ? 'seat--blocked' : 'seat--free'}`;
  btn.dataset.key = key;
  btn.textContent = seatNum;
  btn.addEventListener('click', () => {
    if (blockedSeats.has(key)) {
      blockedSeats.delete(key);
      btn.classList.remove('seat--blocked');
      btn.classList.add('seat--free');
    } else {
      blockedSeats.add(key);
      btn.classList.remove('seat--free');
      btn.classList.add('seat--blocked');
    }
    updateStats();
  });
  return btn;
}

function updateStats() {
  const blocked = blockedSeats.size;
  const available = totalSeats - blocked;
  document.getElementById('stats-text').textContent =
    `Всього: ${totalSeats} | Доступних: ${available} | Заблоковано: ${blocked}`;
}

function applyConfig() {
  totalSeats = Math.min(Math.max(parseInt(document.getElementById('input-total').value) || 40, 1), 100);
  seatsPerRow = Math.min(Math.max(parseInt(document.getElementById('input-rows').value) || 4, 2), 8);
  departurCity = document.getElementById('input-departure').value.trim();
  arrivalCity = document.getElementById('input-arrival').value.trim();

  // Чистимо заблоковані що виходять за межі
  for (const key of [...blockedSeats]) {
    const num = parseInt(key.replace('seat_', ''));
    if (num > totalSeats) blockedSeats.delete(key);
  }

  renderBus();
  showToast('Схему оновлено');
}

async function saveLayout() {
  const initData = tg?.initData;
  if (!initData) {
    showToast('❌ Не вдалося підтвердити користувача');
    return;
  }

  const layoutConfig = {
    category: 'bus',
    total_seats: totalSeats,
    seats_per_row: seatsPerRow,
    blocked_seats: [...blockedSeats],
    departure_city: departurCity,
    arrival_city: arrivalCity,
    has_driver_seat: true,
  };

  try {
    const res = await fetch(`${API_BASE}/api/events/${eventId}/layout`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        layout_config: layoutConfig,
        init_data: initData,
      }),
    });

    if (res.ok) {
      showToast('✅ Схему збережено!');
      setTimeout(() => tg?.close(), 1500);
    } else {
      showToast('❌ Помилка збереження');
    }
  } catch (e) {
    showToast('❌ Помилка мережі');
  }
}

function showError(msg) {
  document.getElementById('error-state').style.display = 'block';
  document.getElementById('error-state').querySelector('.error-state__text').textContent = msg;
}

function showToast(msg) {
  let toast = document.querySelector('.toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.className = 'toast';
    document.body.appendChild(toast);
  }
  toast.textContent = msg;
  toast.classList.add('visible');
  setTimeout(() => toast.classList.remove('visible'), 2200);
}

document.addEventListener('DOMContentLoaded', init);
