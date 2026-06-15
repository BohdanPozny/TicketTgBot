/**
 * cinema_customer.js
 * Клієнтський інтерфейс кінозалу (вибір місця)
 */

const tg = window.Telegram?.WebApp;
const API_BASE = document.querySelector('meta[name="api-base"]')?.content || '';

let eventId = null;
let layoutConfig = {};
let occupiedSeats = new Set();
let selectedSeat = null;
let basePrice = 0;

// ─── Init ────────────────────────────────────────────────────

async function init() {
  tg?.ready();
  tg?.expand();

  const params = new URLSearchParams(window.location.search);
  eventId = parseInt(params.get('event_id'));

  if (!eventId) {
    showError('Невірні параметри запиту');
    return;
  }

  showLoading(true);
  try {
    const data = await fetchLayout(eventId);
    layoutConfig = data.layout_config || {};
    basePrice = data.base_price || 0;
    occupiedSeats = new Set(data.occupied_seats || []);

    document.getElementById('event-title').textContent = data.title || 'Кіносеанс';
    document.getElementById('event-datetime').textContent = formatDatetime(data.datetime);

    renderCinemaLayout();
  } catch (e) {
    showError('Не вдалося завантажити схему залу');
  } finally {
    showLoading(false);
  }
}

async function fetchLayout(eventId) {
  const res = await fetch(`${API_BASE}/api/events/${eventId}/layout`);
  if (!res.ok) throw new Error('API error');
  return res.json();
}

// ─── Render ──────────────────────────────────────────────────

function renderCinemaLayout() {
  const rows = layoutConfig.rows || 8;
  const seatsPerRow = layoutConfig.seats_per_row || 10;
  const blockedSeats = new Set(layoutConfig.blocked_seats || []);

  const grid = document.getElementById('seat-grid');
  grid.innerHTML = '';

  for (let r = 1; r <= rows; r++) {
    const rowEl = document.createElement('div');
    rowEl.className = 'seat-row';

    // Row label
    const labelEl = document.createElement('div');
    labelEl.className = 'row-label';
    labelEl.textContent = r;
    rowEl.appendChild(labelEl);

    for (let s = 1; s <= seatsPerRow; s++) {
      const key = `${r}_${s}`;
      const btn = document.createElement('button');
      btn.className = 'seat';
      btn.dataset.row = r;
      btn.dataset.seat = s;
      btn.dataset.key = key;
      btn.textContent = s;

      if (blockedSeats.has(key)) {
        btn.classList.add('seat--blocked');
        btn.disabled = true;
      } else if (occupiedSeats.has(key)) {
        btn.classList.add('seat--occupied');
        btn.disabled = true;
        btn.title = 'Зайнято';
      } else {
        btn.classList.add('seat--free');
        btn.addEventListener('click', () => selectSeat(btn, r, s, key));
      }

      rowEl.appendChild(btn);
    }
    grid.appendChild(rowEl);
  }
}

// ─── Seat Selection ───────────────────────────────────────────

function selectSeat(btn, row, seat, key) {
  // Знімаємо виділення з попереднього
  if (selectedSeat) {
    const prev = document.querySelector(`.seat--selected`);
    if (prev) {
      prev.classList.remove('seat--selected');
      prev.classList.add('seat--free');
    }
  }

  if (selectedSeat?.key === key) {
    // Повторний клік — скасовуємо вибір
    selectedSeat = null;
    updateOrderBar(null);
    return;
  }

  btn.classList.remove('seat--free');
  btn.classList.add('seat--selected');

  selectedSeat = { row, seat, key, price: basePrice };
  updateOrderBar(selectedSeat);
}

function updateOrderBar(seat) {
  const info = document.getElementById('order-info');
  const priceEl = document.getElementById('order-price');
  const confirmBtn = document.getElementById('btn-confirm');

  if (seat) {
    info.textContent = `Ряд ${seat.row}, Місце ${seat.seat}`;
    priceEl.textContent = `${seat.price.toFixed(2)} грн`;
    confirmBtn.disabled = false;
  } else {
    info.textContent = 'Оберіть місце';
    priceEl.textContent = '—';
    confirmBtn.disabled = true;
  }
}

// ─── Confirm ─────────────────────────────────────────────────

function confirmSelection() {
  if (!selectedSeat) return;

  const data = {
    category: 'cinema',
    event_id: eventId,
    row: selectedSeat.row,
    seat: selectedSeat.seat,
    seat_key: selectedSeat.key,
    price: selectedSeat.price,
  };

  tg?.sendData(JSON.stringify(data));
  tg?.close();
}

// ─── Utils ───────────────────────────────────────────────────

function showLoading(visible) {
  document.getElementById('loading').style.display = visible ? 'flex' : 'none';
  document.getElementById('seat-section').style.display = visible ? 'none' : 'block';
}

function showError(msg) {
  const el = document.getElementById('error-state');
  if (el) {
    el.style.display = 'block';
    el.querySelector('.error-state__text').textContent = msg;
  }
  showLoading(false);
}

function formatDatetime(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleString('uk-UA', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
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
document.getElementById('btn-confirm')?.addEventListener('click', confirmSelection);
