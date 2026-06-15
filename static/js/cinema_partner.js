/**
 * cinema_partner.js
 * Конструктор схеми кінозалу для партнера
 */

const tg = window.Telegram?.WebApp;
const API_BASE = document.querySelector('meta[name="api-base"]')?.content || '';

let eventId = null;
let rows = 8;
let seatsPerRow = 10;
let blockedSeats = new Set();
let activeTool = 'block'; // 'free' | 'block'

// ─── Init ────────────────────────────────────────────────────

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
    rows = cfg.rows || 8;
    seatsPerRow = cfg.seats_per_row || 10;
    blockedSeats = new Set(cfg.blocked_seats || []);

    document.getElementById('input-rows').value = rows;
    document.getElementById('input-seats').value = seatsPerRow;
    document.getElementById('event-title').textContent = data.title || 'Кінозал';
  } catch (e) {
    // Нова подія — використовуємо значення за замовчуванням
  }

  renderGrid();
}

// ─── Render ──────────────────────────────────────────────────

function renderGrid() {
  const grid = document.getElementById('seat-grid');
  grid.innerHTML = '';

  for (let r = 1; r <= rows; r++) {
    const rowEl = document.createElement('div');
    rowEl.className = 'seat-row';

    const labelEl = document.createElement('div');
    labelEl.className = 'row-label';
    labelEl.textContent = r;
    rowEl.appendChild(labelEl);

    for (let s = 1; s <= seatsPerRow; s++) {
      const key = `${r}_${s}`;
      const btn = document.createElement('button');
      btn.className = 'seat';
      btn.dataset.key = key;
      btn.textContent = s;

      if (blockedSeats.has(key)) {
        btn.classList.add('seat--blocked');
      } else {
        btn.classList.add('seat--free');
      }

      btn.addEventListener('click', () => toggleSeat(btn, key));
      rowEl.appendChild(btn);
    }
    grid.appendChild(rowEl);
  }

  updateStats();
}

function toggleSeat(btn, key) {
  if (activeTool === 'block') {
    if (blockedSeats.has(key)) {
      blockedSeats.delete(key);
      btn.classList.remove('seat--blocked');
      btn.classList.add('seat--free');
    } else {
      blockedSeats.add(key);
      btn.classList.remove('seat--free');
      btn.classList.add('seat--blocked');
    }
  }
  updateStats();
}

function updateStats() {
  const total = rows * seatsPerRow;
  const blocked = blockedSeats.size;
  const available = total - blocked;
  document.getElementById('stats-text').textContent =
    `Всього: ${total} | Доступних: ${available} | Заблоковано: ${blocked}`;
}

// ─── Apply Config ─────────────────────────────────────────────

function applyConfig() {
  const newRows = parseInt(document.getElementById('input-rows').value) || 8;
  const newSeats = parseInt(document.getElementById('input-seats').value) || 10;

  rows = Math.min(Math.max(newRows, 1), 30);
  seatsPerRow = Math.min(Math.max(newSeats, 1), 30);

  // Чистимо блокування для місць, яких більше не існує
  for (const key of [...blockedSeats]) {
    const [r, s] = key.split('_').map(Number);
    if (r > rows || s > seatsPerRow) blockedSeats.delete(key);
  }

  renderGrid();
  showToast('Схему оновлено');
}

// ─── Tool Selection ───────────────────────────────────────────

function setTool(tool) {
  activeTool = tool;
  document.querySelectorAll('.tool-btn').forEach(b => b.classList.remove('active'));
  document.getElementById(`tool-${tool}`)?.classList.add('active');
}

// ─── Save ─────────────────────────────────────────────────────

async function saveLayout() {
  const partnerTelegramId = tg?.initDataUnsafe?.user?.id;
  if (!partnerTelegramId) {
    showToast('❌ Не вдалося отримати ID партнера');
    return;
  }

  const layoutConfig = {
    category: 'cinema',
    rows,
    seats_per_row: seatsPerRow,
    blocked_seats: [...blockedSeats],
    screen_label: 'ЕКРАН',
  };

  try {
    const res = await fetch(`${API_BASE}/api/events/${eventId}/layout`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        layout_config: layoutConfig,
        partner_telegram_id: partnerTelegramId,
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

// ─── Utils ───────────────────────────────────────────────────

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
