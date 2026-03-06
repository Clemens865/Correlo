/**
 * charts.js — Canvas chart rendering for the Correlation Explorer.
 * All charts use raw Canvas 2D — no dependencies.
 */

const COLORS = {
  a: '#818cf8',   // indigo
  b: '#34d399',   // green
  reg: '#f87171', // red regression line
  grid: '#1e1e2e',
  label: '#606078',
  bg: '#0a0a0f',
};

/** Set up a canvas for HiDPI rendering. Returns { ctx, w, h }. */
function setupCanvas(canvas) {
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.parentElement.getBoundingClientRect();
  canvas.width = rect.width * dpr;
  canvas.height = rect.height * dpr;
  const ctx = canvas.getContext('2d');
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, rect.width, rect.height);
  return { ctx, w: rect.width, h: rect.height };
}

/** Draw normalized overlay chart (two series scaled 0-1). */
export function drawOverlay(canvasId, labels, normA, normB, nameA, nameB) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || normA.length < 2) return;
  const { ctx, w, h } = setupCanvas(canvas);

  const pad = { top: 20, right: 16, bottom: 32, left: 44 };
  const pw = w - pad.left - pad.right;
  const ph = h - pad.top - pad.bottom;
  const n = normA.length;
  const xStep = pw / (n - 1);

  // Grid
  ctx.strokeStyle = COLORS.grid;
  ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const y = pad.top + (ph * i / 4);
    ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(w - pad.right, y); ctx.stroke();
    ctx.fillStyle = COLORS.label;
    ctx.font = '10px -apple-system, sans-serif';
    ctx.textAlign = 'right';
    ctx.fillText((1 - i / 4).toFixed(1), pad.left - 6, y + 3);
  }

  // Series A
  drawLine(ctx, normA, pad, pw, ph, xStep, COLORS.a, 2);
  // Series B
  drawLine(ctx, normB, pad, pw, ph, xStep, COLORS.b, 2);

  // X labels
  drawXLabels(ctx, labels, pad, pw, h, xStep);

  // Legend
  drawLegend(ctx, w, [
    { color: COLORS.a, label: nameA },
    { color: COLORS.b, label: nameB },
  ]);
}

/** Draw scatter plot with optional regression line. */
export function drawScatter(canvasId, dataA, dataB, regLine, nameA, nameB) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || dataA.length < 2) return;
  const { ctx, w, h } = setupCanvas(canvas);

  const pad = { top: 16, right: 16, bottom: 36, left: 50 };
  const pw = w - pad.left - pad.right;
  const ph = h - pad.top - pad.bottom;

  const minX = Math.min(...dataA), maxX = Math.max(...dataA);
  const minY = Math.min(...dataB), maxY = Math.max(...dataB);
  const rangeX = maxX - minX || 1;
  const rangeY = maxY - minY || 1;

  const toX = v => pad.left + ((v - minX) / rangeX) * pw;
  const toY = v => pad.top + ph - ((v - minY) / rangeY) * ph;

  // Grid
  ctx.strokeStyle = COLORS.grid;
  ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const y = pad.top + (ph * i / 4);
    ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(w - pad.right, y); ctx.stroke();
    ctx.fillStyle = COLORS.label;
    ctx.font = '10px -apple-system, sans-serif';
    ctx.textAlign = 'right';
    const val = maxY - (i / 4) * rangeY;
    ctx.fillText(formatNum(val), pad.left - 6, y + 3);
  }
  for (let i = 0; i <= 4; i++) {
    const x = pad.left + (pw * i / 4);
    ctx.beginPath(); ctx.moveTo(x, pad.top); ctx.lineTo(x, pad.top + ph); ctx.stroke();
  }

  // Regression line
  if (regLine && regLine.length === dataA.length) {
    ctx.strokeStyle = COLORS.reg;
    ctx.lineWidth = 1.5;
    ctx.setLineDash([6, 4]);
    ctx.beginPath();
    const sorted = dataA.map((v, i) => [v, regLine[i]]).sort((a, b) => a[0] - b[0]);
    ctx.moveTo(toX(sorted[0][0]), toY(sorted[0][1]));
    ctx.lineTo(toX(sorted[sorted.length - 1][0]), toY(sorted[sorted.length - 1][1]));
    ctx.stroke();
    ctx.setLineDash([]);
  }

  // Points
  ctx.fillStyle = COLORS.a + 'cc';
  for (let i = 0; i < dataA.length; i++) {
    const x = toX(dataA[i]);
    const y = toY(dataB[i]);
    ctx.beginPath();
    ctx.arc(x, y, 3.5, 0, Math.PI * 2);
    ctx.fill();
  }

  // Axis labels
  ctx.fillStyle = COLORS.label;
  ctx.font = '10px -apple-system, sans-serif';
  ctx.textAlign = 'center';
  ctx.fillText(nameA, pad.left + pw / 2, h - 4);
  ctx.save();
  ctx.translate(12, pad.top + ph / 2);
  ctx.rotate(-Math.PI / 2);
  ctx.fillText(nameB, 0, 0);
  ctx.restore();
}

/** Draw dual-axis chart (two series with their own Y scales). */
export function drawDualAxis(canvasId, labels, dataA, dataB, nameA, nameB, unitA, unitB) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || dataA.length < 2) return;
  const { ctx, w, h } = setupCanvas(canvas);

  const pad = { top: 20, right: 50, bottom: 32, left: 50 };
  const pw = w - pad.left - pad.right;
  const ph = h - pad.top - pad.bottom;
  const n = dataA.length;
  const xStep = pw / (n - 1);

  const minA = Math.min(...dataA), maxA = Math.max(...dataA);
  const minB = Math.min(...dataB), maxB = Math.max(...dataB);
  const rangeA = maxA - minA || 1;
  const rangeB = maxB - minB || 1;

  // Grid
  ctx.strokeStyle = COLORS.grid;
  ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const y = pad.top + (ph * i / 4);
    ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(w - pad.right, y); ctx.stroke();
  }

  // Left Y axis (A)
  ctx.fillStyle = COLORS.a;
  ctx.font = '10px -apple-system, sans-serif';
  ctx.textAlign = 'right';
  for (let i = 0; i <= 4; i++) {
    const y = pad.top + (ph * i / 4);
    const val = maxA - (i / 4) * rangeA;
    ctx.fillText(formatNum(val), pad.left - 6, y + 3);
  }

  // Right Y axis (B)
  ctx.fillStyle = COLORS.b;
  ctx.textAlign = 'left';
  for (let i = 0; i <= 4; i++) {
    const y = pad.top + (ph * i / 4);
    const val = maxB - (i / 4) * rangeB;
    ctx.fillText(formatNum(val), w - pad.right + 6, y + 3);
  }

  // Series A (left axis)
  const normA = dataA.map(v => (v - minA) / rangeA);
  drawLine(ctx, normA, pad, pw, ph, xStep, COLORS.a, 2);

  // Series B (right axis)
  const normB = dataB.map(v => (v - minB) / rangeB);
  drawLine(ctx, normB, pad, pw, ph, xStep, COLORS.b, 2);

  // X labels
  drawXLabels(ctx, labels, pad, pw, h, xStep);

  // Legend with units
  drawLegend(ctx, w, [
    { color: COLORS.a, label: `${nameA} (${unitA})` },
    { color: COLORS.b, label: `${nameB} (${unitB})` },
  ]);
}

/** Draw a heatmap-style correlation matrix. Returns HTML string. */
export function renderMatrixHTML(result) {
  const { ids, pearson, n_points } = result;
  const n = ids.length;

  let html = '<table class="matrix-table"><thead><tr><th></th>';
  for (const id of ids) {
    html += `<th title="${id}">${id.split('-').pop()}</th>`;
  }
  html += '</tr></thead><tbody>';

  for (let i = 0; i < n; i++) {
    html += `<tr><th title="${ids[i]}">${ids[i].split('-').pop()}</th>`;
    for (let j = 0; j < n; j++) {
      const r = pearson[i][j];
      const color = corrColor(r);
      const text = i === j ? '1.00' : r.toFixed(2);
      html += `<td class="matrix-cell" style="background:${color};color:${Math.abs(r) > 0.5 ? '#fff' : '#e0e0ec'}" data-i="${i}" data-j="${j}" title="${ids[i]} vs ${ids[j]}: r=${r.toFixed(3)}, n=${n_points[i][j]}">${text}</td>`;
    }
    html += '</tr>';
  }
  html += '</tbody></table>';
  return html;
}


// --- Helpers ----------------------------------------------------------------

function drawLine(ctx, normalized, pad, pw, ph, xStep, color, lineWidth) {
  ctx.strokeStyle = color;
  ctx.lineWidth = lineWidth;
  ctx.beginPath();
  for (let i = 0; i < normalized.length; i++) {
    const x = pad.left + i * xStep;
    const y = pad.top + ph * (1 - normalized[i]);
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  }
  ctx.stroke();

  // Fill under
  const lastX = pad.left + (normalized.length - 1) * xStep;
  ctx.lineTo(lastX, pad.top + ph);
  ctx.lineTo(pad.left, pad.top + ph);
  ctx.closePath();
  ctx.fillStyle = color + '10';
  ctx.fill();
}

function drawXLabels(ctx, labels, pad, pw, h, xStep) {
  if (!labels || labels.length === 0) return;
  ctx.fillStyle = COLORS.label;
  ctx.font = '9px -apple-system, sans-serif';
  ctx.textAlign = 'center';
  const step = Math.max(1, Math.floor(labels.length / 6));
  for (let i = 0; i < labels.length; i += step) {
    const x = pad.left + i * xStep;
    const label = typeof labels[i] === 'string' ? labels[i].slice(5) : labels[i];
    ctx.fillText(label, x, h - 6);
  }
}

function drawLegend(ctx, w, items) {
  const y = 12;
  let x = w - 16;
  ctx.font = '10px -apple-system, sans-serif';
  ctx.textAlign = 'right';
  for (let i = items.length - 1; i >= 0; i--) {
    const item = items[i];
    const textW = ctx.measureText(item.label).width;
    ctx.fillStyle = '#e0e0ec';
    ctx.fillText(item.label, x, y);
    x -= textW + 4;
    ctx.fillStyle = item.color;
    ctx.fillRect(x - 12, y - 4, 10, 3);
    x -= 20;
  }
}

function corrColor(r) {
  const abs = Math.abs(r);
  if (abs < 0.05) return '#252535';
  const intensity = Math.floor(abs * 200);
  if (r > 0) return `rgba(52,211,153,${abs * 0.7})`;
  return `rgba(248,113,113,${abs * 0.7})`;
}

function formatNum(v) {
  if (Math.abs(v) >= 10000) return (v / 1000).toFixed(0) + 'k';
  if (Math.abs(v) >= 100) return v.toFixed(0);
  if (Math.abs(v) >= 1) return v.toFixed(1);
  return v.toFixed(2);
}
