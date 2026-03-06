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

/** Draw a single time series with filled area and Y-axis in original units. */
export function drawTimeSeries(canvasId, labels, values, name, unit, color = '#818cf8') {
  const canvas = document.getElementById(canvasId);
  if (!canvas || values.length < 2) return;
  const { ctx, w, h } = setupCanvas(canvas);

  const pad = { top: 20, right: 16, bottom: 32, left: 54 };
  const pw = w - pad.left - pad.right;
  const ph = h - pad.top - pad.bottom;
  const n = values.length;
  const xStep = pw / (n - 1);

  const minV = Math.min(...values), maxV = Math.max(...values);
  const range = maxV - minV || 1;
  const norm = values.map(v => (v - minV) / range);

  // Grid + Y labels
  ctx.strokeStyle = COLORS.grid;
  ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const y = pad.top + (ph * i / 4);
    ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(w - pad.right, y); ctx.stroke();
    ctx.fillStyle = COLORS.label;
    ctx.font = '10px -apple-system, sans-serif';
    ctx.textAlign = 'right';
    const val = maxV - (i / 4) * range;
    ctx.fillText(formatNum(val), pad.left - 6, y + 3);
  }

  // Line + fill
  drawLine(ctx, norm, pad, pw, ph, xStep, color, 2);

  // X labels
  drawXLabels(ctx, labels, pad, pw, h, xStep);

  // Legend
  drawLegend(ctx, w, [{ color, label: `${name} (${unit})` }]);
}

/** Render an interactive canvas heatmap matrix. Returns the container element. */
export function renderMatrixCanvas(container, result, onCellClick) {
  const { ids, pearson, n_points } = result;
  const n = ids.length;

  // Short display names
  const names = ids.map(id => {
    const parts = id.replace(/\s*\(.*?\)\s*/g, '').split(/[\s/]+/);
    return parts.length > 3 ? parts.slice(0, 3).join(' ') : id;
  });

  // Layout
  const cellSize = Math.max(28, Math.min(60, Math.floor(600 / n)));
  const labelSpace = 140;
  const topLabelSpace = 140;
  const totalW = labelSpace + n * cellSize + 60; // 60 for color legend
  const totalH = topLabelSpace + n * cellSize + 20;

  // Create canvas
  container.innerHTML = '';
  const wrapper = document.createElement('div');
  wrapper.style.cssText = 'position:relative;overflow-x:auto;overflow-y:auto;max-height:80vh;';
  const canvas = document.createElement('canvas');
  const dpr = window.devicePixelRatio || 1;
  canvas.width = totalW * dpr;
  canvas.height = totalH * dpr;
  canvas.style.width = totalW + 'px';
  canvas.style.height = totalH + 'px';
  const ctx = canvas.getContext('2d');
  ctx.scale(dpr, dpr);

  // Tooltip element
  const tooltip = document.createElement('div');
  tooltip.className = 'matrix-tooltip';
  wrapper.appendChild(canvas);
  wrapper.appendChild(tooltip);
  container.appendChild(wrapper);

  // Color scale: blue (negative) → dark (zero) → orange/red (positive)
  function heatColor(r) {
    const a = Math.abs(r);
    if (a < 0.02) return '#1a1a2e';
    if (r > 0) {
      const t = Math.min(a, 1);
      const red = Math.round(40 + 215 * t);
      const green = Math.round(40 + 140 * t * (1 - t * 0.5));
      const blue = Math.round(40 + 40 * (1 - t));
      return `rgb(${red},${green},${blue})`;
    } else {
      const t = Math.min(a, 1);
      const red = Math.round(40 + 40 * (1 - t));
      const green = Math.round(40 + 100 * t * (1 - t * 0.4));
      const blue = Math.round(40 + 215 * t);
      return `rgb(${red},${green},${blue})`;
    }
  }

  // Draw cells
  for (let i = 0; i < n; i++) {
    for (let j = 0; j < n; j++) {
      const r = pearson[i][j];
      const x = labelSpace + j * cellSize;
      const y = topLabelSpace + i * cellSize;

      ctx.fillStyle = heatColor(r);
      ctx.fillRect(x + 1, y + 1, cellSize - 2, cellSize - 2);

      // Round corners effect
      ctx.strokeStyle = '#0a0a0f';
      ctx.lineWidth = 1;
      ctx.strokeRect(x + 0.5, y + 0.5, cellSize - 1, cellSize - 1);

      // Value text (only if cells are big enough)
      if (cellSize >= 36) {
        const absR = Math.abs(r);
        ctx.fillStyle = absR > 0.4 ? '#fff' : '#888';
        ctx.font = `${absR > 0.7 ? 'bold ' : ''}${cellSize > 45 ? 11 : 9}px -apple-system, sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(i === j ? '' : r.toFixed(2), x + cellSize / 2, y + cellSize / 2);
      }

      // Diagonal highlight
      if (i === j) {
        ctx.fillStyle = '#818cf840';
        ctx.fillRect(x + 1, y + 1, cellSize - 2, cellSize - 2);
      }
    }
  }

  // Row labels (left side)
  ctx.textAlign = 'right';
  ctx.textBaseline = 'middle';
  ctx.font = '11px -apple-system, sans-serif';
  for (let i = 0; i < n; i++) {
    const y = topLabelSpace + i * cellSize + cellSize / 2;
    ctx.fillStyle = '#c0c0d0';
    const label = names[i].length > 20 ? names[i].slice(0, 18) + '...' : names[i];
    ctx.fillText(label, labelSpace - 8, y);
  }

  // Column labels (top, rotated 45°)
  ctx.save();
  for (let j = 0; j < n; j++) {
    const x = labelSpace + j * cellSize + cellSize / 2;
    ctx.save();
    ctx.translate(x, topLabelSpace - 8);
    ctx.rotate(-Math.PI / 4);
    ctx.fillStyle = '#c0c0d0';
    ctx.font = '11px -apple-system, sans-serif';
    ctx.textAlign = 'left';
    ctx.textBaseline = 'middle';
    const label = names[j].length > 20 ? names[j].slice(0, 18) + '...' : names[j];
    ctx.fillText(label, 0, 0);
    ctx.restore();
  }
  ctx.restore();

  // Color legend
  const legX = labelSpace + n * cellSize + 16;
  const legY = topLabelSpace;
  const legH = Math.min(n * cellSize, 200);
  const legW = 14;
  for (let i = 0; i < legH; i++) {
    const r = 1 - 2 * (i / legH); // +1 at top, -1 at bottom
    ctx.fillStyle = heatColor(r);
    ctx.fillRect(legX, legY + i, legW, 1);
  }
  ctx.strokeStyle = '#333';
  ctx.strokeRect(legX, legY, legW, legH);
  ctx.fillStyle = '#888';
  ctx.font = '9px -apple-system, sans-serif';
  ctx.textAlign = 'left';
  ctx.fillText('+1.0', legX + legW + 4, legY + 4);
  ctx.fillText(' 0.0', legX + legW + 4, legY + legH / 2 + 3);
  ctx.fillText('-1.0', legX + legW + 4, legY + legH + 3);

  // Hover + click interaction
  canvas.addEventListener('mousemove', (e) => {
    const rect = canvas.getBoundingClientRect();
    const mx = (e.clientX - rect.left);
    const my = (e.clientY - rect.top);
    const j = Math.floor((mx - labelSpace) / cellSize);
    const i = Math.floor((my - topLabelSpace) / cellSize);

    if (i >= 0 && i < n && j >= 0 && j < n && i !== j) {
      const r = pearson[i][j];
      const pts = n_points[i][j];
      tooltip.innerHTML = `<strong>${names[i]}</strong> vs <strong>${names[j]}</strong><br>
        r = <span style="color:${r > 0 ? '#f59e0b' : '#3b82f6'};font-weight:bold">${r.toFixed(4)}</span> | ${pts} points`;
      tooltip.style.display = 'block';
      tooltip.style.left = (e.clientX - rect.left + 12) + 'px';
      tooltip.style.top = (e.clientY - rect.top - 40) + 'px';
      canvas.style.cursor = 'pointer';
    } else {
      tooltip.style.display = 'none';
      canvas.style.cursor = 'default';
    }
  });

  canvas.addEventListener('mouseleave', () => {
    tooltip.style.display = 'none';
  });

  if (onCellClick) {
    canvas.addEventListener('click', (e) => {
      const rect = canvas.getBoundingClientRect();
      const j = Math.floor(((e.clientX - rect.left) - labelSpace) / cellSize);
      const i = Math.floor(((e.clientY - rect.top) - topLabelSpace) / cellSize);
      if (i >= 0 && i < n && j >= 0 && j < n && i !== j) {
        onCellClick(i, j, ids, pearson[i][j]);
      }
    });
  }
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
