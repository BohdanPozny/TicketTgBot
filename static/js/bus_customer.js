/**
 * bus_customer.js
 * Клієнтський інтерфейс автобуса (вибір місця)
 */

const tg = window.Telegram?.WebApp;
const API_BASE = document.querySelector('meta[name="api-base"]')?.content || '';

let eventId = null;
let layoutConfig = {};
let occupiedSeats = new Set();
let selectedSeat = null;
let basePrice = 0;

async function init() {
  tg?.ready();
  tg?.expand();

  const params = new URLSearchParams(window.location.search);
  eventId = parseInt(params.get('event_id'));

  if (!eventId) {
    showError('Невірні параметри');
    return;
  }

  showLoading(true);
  try {
    const data = await fetch(`${API_BASE}/api/events/${eventId}/layout`).then(r => r.json());
    layoutConfig = data.layout_config || {};
    basePrice = data.base_price || 0;
    occupiedSeats = new Set(data.occupied_seats || []);

    document.getElementById('event-title').textContent = data.title || 'Рейс';
    document.getElementById('event-datetime').textContent = formatDatetime(data.datetime);

    const dep = layoutConfig.departure_city || '';
    const arr = layoutConfig.arrival_city || '';
    if (dep && arr) {
      document.getElementById('route-label').textContent = `${dep} → ${arr}`;
    }

    renderBusLayout();
  } catch (e) {
    showError('Не вдалося завантажити схему автобуса');
  } finally {
    showLoading(false);
  }
}

// ─── Render Bus Layout ────────────────────────────────────────

function renderBusLayout() {
  const totalSeats = layoutConfig.total_seats || 40;
  const seatsPerRow = layoutConfig.seats_per_row || 4; // 2+2
  const blockedSeats = new Set(layoutConfig.blocked_seats || []);
  const hasDriverSeat = layoutConfig.has_driver_seat !== false;

  const busEl = document.getElementById('bus-layout');
  busEl.innerHTML = '';

  // Front row (driver)
  if (hasDriverSeat) {
    const frontRow = document.createElement('div');
    frontRow.className = 'bus-row bus-front';

    const driverBtn = document.createElement('button');
    driverBtn.className = 'seat seat--driver';
    driverBtn.disabled = true;
    driverBtn.title = 'Місце водія';
    driverBtn.textContent = '🚗';
    frontRow.appendChild(driverBtn);

    busEl.appendChild(frontRow);
  }

  // Passenger rows (2+aisle+2)
  const leftSeats = Math.floor(seatsPerRow / 2);
  const rightSeats = seatsPerRow - leftSeats;
  let seatNum = 1;

  while (seatNum <= totalSeats) {
    const rowEl = document.createElement('div');
    rowEl.className = 'bus-row';

    // Left seats
    for (let i = 0; i < leftSeats && seatNum <= totalSeats; i++, seatNum++) {
      rowEl.appendChild(createSeatBtn(seatNum, blockedSeats));
    }

    // Aisle
    const aisle = document.createElement('div');
    aisle.className = 'bus-aisle';
    rowEl.appendChild(aisle);

    // Right seats
    for (let i = 0; i < rightSeats && seatNum <= totalSeats; i++, seatNum++) {
      rowEl.appendChild(createSeatBtn(seatNum, blockedSeats));
    }

    busEl.appendChild(rowEl);
  }
}

function createSeatBtn(seatNum, blockedSeats) {
  const key = `seat_${seatNum}`;
  const btn = document.createElement('button');
  btn.className = 'seat';
  btn.dataset.seatNumber = seatNum;
  btn.dataset.key = key;
  btn.textContent = seatNum;

  if (blockedSeats.has(key)) {
    btn.classList.add('seat--blocked');
    btn.disabled = true;
  } else if (occupiedSeats.has(key)) {
    btn.classList.add('seat--occupied');
    btn.disabled = true;
    btn.title = 'Зайнято';
  } else {
    btn.classList.add('seat--free');
    btn.addEventListener('click', () => selectSeat(btn, seatNum, key));
  }

  return btn;
}

function selectSeat(btn, seatNum, key) {
  if (selectedSeat) {
    const prev = document.querySelector('.seat--selected');
    if (prev) {
      prev.classList.remove('seat--selected');
      prev.classList.add('seat--free');
    }
  }

  if (selectedSeat?.key === key) {
    selectedSeat = null;
    updateOrderBar(null);
    return;
  }

  btn.classList.remove('seat--free');
  btn.classList.add('seat--selected');

  selectedSeat = { seat_number: seatNum, key, price: basePrice };
  updateOrderBar(selectedSeat);
}

function updateOrderBar(seat) {
  const info = document.getElementById('order-info');
  const priceEl = document.getElementById('order-price');
  const confirmBtn = document.getElementById('btn-confirm');

  if (seat) {
    info.textContent = `Місце ${seat.seat_number}`;
    priceEl.textContent = `${seat.price.toFixed(2)} грн`;
    confirmBtn.disabled = false;
  } else {
    info.textContent = 'Оберіть місце';
    priceEl.textContent = '—';
    confirmBtn.disabled = true;
  }
}

function confirmSelection() {
  if (!selectedSeat) return;

  const data = {
    category: 'bus',
    event_id: eventId,
    seat_number: selectedSeat.seat_number,
    seat_key: selectedSeat.key,
    price: selectedSeat.price,
  };

  tg?.sendData(JSON.stringify(data));
  tg?.close();
}

function showLoading(visible) {
  document.getElementById('loading').style.display = visible ? 'flex' : 'none';
  document.getElementById('bus-section').style.display = visible ? 'none' : 'block';
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

document.addEventListener('DOMContentLoaded', init);
document.getElementById('btn-confirm')?.addEventListener('click', confirmSelection);
