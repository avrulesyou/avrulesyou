// The War Room: data model, flat heatmap, details panel, stats and the bridge
// to the 3D scene (scene.js is loaded lazily so the page still works without WebGL).
import { buildModel, POWER, WEEKDAYS, formatDate, formatCount, contributionText, matchesFilter, replayAt } from './model.js';

const $ = (selector, root = document) => root.querySelector(selector);
const el = (tag, className, text) => {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = text;
  return node;
};
const mqReduce = window.matchMedia('(prefers-reduced-motion: reduce)');
const mqCoarse = window.matchMedia('(pointer: coarse)');
const mqMobile = window.matchMedia('(max-width: 720px)');
const REPLAY_MS = 14000;
// ---------- dates (all YYYY-MM-DD strings are treated as UTC calendar days) ----------
const fullDate = (date) => formatDate(date, { month: 'long', day: 'numeric', year: 'numeric' });
const shortDate = (date) => formatDate(date, { month: 'short', day: 'numeric', year: 'numeric' });
const dateRange = (start, end) => start && end ? `${shortDate(start)} — ${shortDate(end)}` : 'No daily record yet';
/** GitHub's tooltip wording. */
export { contributionText };
// ---------- state + shared UI ----------
const state = {
  model: null, available: false, selectedDate: null, hoverDate: null, activeDate: null,
  filter: 'all', preset: 'front', replayProgress: 1, playing: false, replayFrame: 0,
  motion: false, interactive: !mqCoarse.matches && !mqMobile.matches, quality: 'auto',
  scene: null, sceneGeneration: 0, sceneUnavailable: false, cells: new Map(), returnFocus: null,
};
const currentTheme = () => document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light';
const tip = $('#tip');
Object.defineProperty(window, '__atlas', {
  value: Object.freeze({
    get model() { return state.model; },
    get scene() { return state.scene; },
    getState: () => Object.freeze({
      selectedDate: state.selectedDate, filter: state.filter, preset: state.preset,
      replayProgress: state.replayProgress, theme: currentTheme(), interactive: state.interactive,
    }),
  }),
  writable: false,
  configurable: false,
});

function showTip(day, x, y) {
  if (!day) return hideTip();
  tip.replaceChildren(el('strong', null, contributionText(day.count, day.date)));
  tip.hidden = false;
  // Keep the bubble on screen.
  const box = tip.getBoundingClientRect();
  const left = Math.max(12, Math.min(innerWidth - box.width - 12, x - box.width / 2));
  const top = y > box.height + 18 ? y - box.height - 12 : y + 22;
  tip.style.left = `${left}px`;
  tip.style.top = `${Math.min(innerHeight - box.height - 8, Math.max(8, top))}px`;
}
function hideTip() { tip.hidden = true; }
function sceneCall(method, ...args) {
  if (!state.scene) return;
  try {
    if (typeof state.scene[method] !== 'function') throw new Error(`Scene method unavailable: ${method}`);
    return state.scene[method](...args);
  } catch (error) {
    console.warn('Interactive landscape unavailable:', error);
    fallback3D();
  }
}
function setHover(date, source, position) {
  if (state.hoverDate) state.cells.get(state.hoverDate)?.classList.remove('is-hover');
  state.hoverDate = state.model?.byDate.has(date) ? date : null;
  if (state.hoverDate) state.cells.get(state.hoverDate)?.classList.add('is-hover');
  if (source !== 'scene') sceneCall('setHover', state.hoverDate);
  if (state.hoverDate && position) showTip(state.model.byDate.get(state.hoverDate), position.x, position.y);
  else hideTip();
}
function setSelected(date, { focus = false, toggle = false } = {}) {
  const previous = state.selectedDate;
  const next = date && state.model.byDate.has(date) && !(toggle && date === previous) ? date : null;
  if (next && !$('#details').contains(document.activeElement)) state.returnFocus = document.activeElement;
  if (previous) {
    const cell = state.cells.get(previous);
    cell?.classList.remove('is-pinned');
    cell?.setAttribute('aria-selected', 'false');
  }
  state.selectedDate = next;
  if (next) {
    const cell = state.cells.get(next);
    cell?.classList.add('is-pinned');
    cell?.setAttribute('aria-selected', 'true');
    setActiveCell(next, false);
  }
  sceneCall('setSelection', next);
  hideTip();
  renderDetails();
  $('#selection-status').textContent = next ? `${contributionText(state.model.byDate.get(next).count, next)}. Daily record pinned.` : 'Daily record unpinned.';
  if (next && focus) $('#details-title').focus({ preventScroll: true });
}
function dismissDetails() {
  const returnTo = state.returnFocus;
  setSelected(null);
  if (returnTo?.isConnected && typeof returnTo.focus === 'function') returnTo.focus({ preventScroll: true });
}
function filteredDays() { return state.model.days.filter((day) => matchesFilter(day, state.model, state.filter)); }
function setFilter(filter) {
  if (!['all', 'top', 'streak', 'weekdays', 'weekends'].includes(filter)) return;
  state.filter = filter;
  $('#filter').value = filter;
  $('#filter').dataset.filter = filter;
  sceneCall('setFilter', filter);
  syncCells();
  const labels = { all: 'all days', top: 'top contribution days', streak: 'the longest streak', weekdays: 'weekdays', weekends: 'weekends' };
  $('#filter-status').textContent = `Showing ${labels[filter]}.${filter === 'all' ? '' : ' Other dates are dimmed in the calendar.'}${filteredDays().length ? '' : ' No dates match this filter.'}`;
  $('#explore-day').disabled = !filteredDays().length;
  if (state.selectedDate) renderDetails();
}
function syncCells() {
  const at = replayAt(state.model, state.replayProgress);
  for (const day of state.model.days) {
    const cell = state.cells.get(day.date);
    if (!cell) continue;
    const visible = matchesFilter(day, state.model, state.filter);
    cell.classList.toggle('is-filtered', !visible);
    cell.classList.toggle('is-future', day.idx > at.index);
    cell.setAttribute('aria-disabled', String(!visible));
    cell.style.setProperty('--cell-color', POWER[currentTheme()][day.level]);
  }
  const current = state.model.byDate.get(state.activeDate);
  if (!current || !matchesFilter(current, state.model, state.filter)) setActiveCell(filteredDays().at(-1)?.date || null, false);
}

// ---------- details panel ----------
function renderDetails() {
  const panel = $('#details');
  const day = state.model?.byDate.get(state.selectedDate);
  panel.hidden = !day;
  if (!day) return;
  const model = state.model;
  const body = $('#details-body');
  const count = el('div', 'd-count');
  count.append(el('strong', null, formatCount(day.count)), el('span', null, day.count === 1 ? 'contribution' : 'contributions'));
  const list = el('dl', 'd-list');
  const row = (label, value) => {
    const item = el('div');
    item.append(el('dt', null, label), el('dd', null, value));
    list.append(item);
  };
  // Ties keep the model's competition rank, so tied days show the same number.
  const tied = day.rank ? (model.tieCount.get(day.count) || 1) - 1 : 0;
  row('Activity rank', day.rank ? `#${formatCount(day.rank)} of ${formatCount(model.activeCount)} active days${tied ? ` · tied with ${formatCount(tied)} other${tied === 1 ? '' : 's'}` : ''}` : day.sea ? 'Before account creation' : 'No activity');
  row('Compared with average', day.sea ? 'Not counted' : model.meanPerDay > 0 ? `${day.ratioToMean.toFixed(1)}× the daily average` : 'No activity to compare');
  row('That week', `${formatCount(model.weekTotals[day.week])} contributions`);
  row(`${formatDate(day.date, { month: 'long' })} total`, `${formatCount(model.monthly[day.date.slice(0, 7)])} contributions`);
  row('Longest streak', day.inLongestStreak ? `Part of ${formatCount(model.streak.longest)}-day streak` : 'Not in longest streak');
  body.replaceChildren(el('p', 'd-date', fullDate(day.date)), el('p', 'd-weekday', WEEKDAYS[day.weekday]), count, el('p', 'd-text', contributionText(day.count, day.date)), list);
  if (day.sea) body.append(el('p', 'd-note', 'Before the account was created. These days are not included in the daily average.'));
  if (!matchesFilter(day, model, state.filter)) body.append(el('p', 'd-note', 'This pinned day is outside the current filter.'));
  const choices = filteredDays();
  $('#day-prev').disabled = !choices.some((item) => item.date < day.date);
  $('#day-next').disabled = !choices.some((item) => item.date > day.date);
  $('#day-input').min = model.start;
  $('#day-input').max = model.end;
  $('#day-input').value = day.date;
}
function stepSelection(direction) {
  const choices = filteredDays();
  const day = direction < 0 ? choices.findLast((item) => item.date < state.selectedDate) : choices.find((item) => item.date > state.selectedDate);
  if (day) setSelected(day.date);
}

// ---------- heatmap ----------
function renderHeatmap() {
  const model = state.model;
  const grid = $('#heatmap');
  grid.replaceChildren();
  state.cells.clear();
  grid.style.setProperty('--weeks', model.nWeeks);
  grid.setAttribute('aria-rowcount', '7');
  grid.setAttribute('aria-colcount', String(model.nWeeks + 1));
  if (!model.days.length) {
    grid.removeAttribute('role');
    grid.append(el('p', 'insight__note', state.available ? 'No daily contribution records in this snapshot yet.' : 'Daily contribution records could not be loaded.'));
    return;
  }
  // Month labels: at the first week whose first day starts a new month (GitHub style).
  let previousMonth = '';
  let previousColumn = -4;
  for (const week of model.weeks) {
    const day = week[0];
    if (!day || day.date.slice(0, 7) === previousMonth) continue;
    previousMonth = day.date.slice(0, 7);
    // GitHub skips a label when the first partial column is too close to the next one.
    if (day.week === 0) {
      const nextMonth = model.weeks.find((column) => column[0] && column[0].date.slice(0, 7) !== previousMonth);
      if (nextMonth?.[0].week < 3) continue;
    }
    if (day.week - previousColumn < 3) continue;
    const label = el('span', 'hm-month', formatDate(day.date, { month: 'short' }));
    label.style.gridColumn = String(day.week + 2);
    label.setAttribute('aria-hidden', 'true');
    grid.append(label);
    previousColumn = day.week;
  }
  WEEKDAYS.forEach((weekday, weekdayIndex) => {
    const row = el('div', 'hm-row');
    row.setAttribute('role', 'row');
    row.setAttribute('aria-rowindex', String(weekdayIndex + 1));
    const label = el('span', 'hm-day', weekday.slice(0, 3));
    label.setAttribute('role', 'rowheader');
    label.style.gridRow = String(weekdayIndex + 2);
    row.append(label);
    for (const week of model.grid) {
      const index = week[weekdayIndex];
      if (index == null) continue;
      const day = model.days[index];
      const cell = el('button', `c${day.sea ? ' is-sea' : ''}`);
      cell.type = 'button';
      cell.dataset.date = day.date;
      cell.dataset.idx = day.idx;
      cell.dataset.action = 'select-day';
      cell.setAttribute('role', 'gridcell');
      cell.setAttribute('aria-colindex', String(day.week + 2));
      cell.setAttribute('aria-label', contributionText(day.count, day.date));
      cell.setAttribute('aria-selected', 'false');
      if (day.sea) cell.setAttribute('aria-description', 'Before account creation.');
      cell.tabIndex = -1;
      cell.style.gridColumn = String(day.week + 2);
      cell.style.gridRow = String(weekdayIndex + 2);
      cell.addEventListener('pointerenter', () => {
        if (!matchesFilter(day, model, state.filter)) return;
        const box = cell.getBoundingClientRect();
        setHover(day.date, 'heatmap', { x: box.left + box.width / 2, y: box.top });
      });
      cell.addEventListener('pointerleave', () => setHover(null, 'heatmap'));
      cell.addEventListener('focus', () => {
        setActiveCell(day.date, false);
        const box = cell.getBoundingClientRect();
        setHover(day.date, 'heatmap', { x: box.left + box.width / 2, y: box.top });
      });
      cell.addEventListener('blur', () => setHover(null, 'heatmap'));
      cell.addEventListener('click', () => {
        if (matchesFilter(day, model, state.filter)) setSelected(day.date, { toggle: true, focus: mqMobile.matches });
      });
      cell.addEventListener('keydown', (event) => calendarKey(event, day));
      state.cells.set(day.date, cell);
      row.append(cell);
    }
    grid.append(row);
  });
  // Roving tabindex starts on the latest day; narrow screens start scrolled to it, like GitHub.
  setActiveCell(model.end, false);
  syncCells();
  requestAnimationFrame(() => { $('#heat-scroller').scrollLeft = $('#heat-scroller').scrollWidth; });
}
function calendarKey(event, day) {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault();
    // Keyboard users land in the details dialog; Escape there returns to this cell.
    setSelected(day.date, { toggle: true, focus: true });
    return;
  }
  if (event.key === 'Escape') {
    event.preventDefault();
    dismissDetails();
    return;
  }
  const choices = filteredDays();
  let target;
  if (event.key === 'Home') target = choices[0];
  else if (event.key === 'End') target = choices.at(-1);
  else if (event.key === 'ArrowUp') target = choices.findLast((item) => item.idx < day.idx);
  else if (event.key === 'ArrowDown') target = choices.find((item) => item.idx > day.idx);
  else if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
    const direction = event.key === 'ArrowLeft' ? -1 : 1;
    target = direction < 0
      ? choices.findLast((item) => item.week < day.week && item.weekday === day.weekday)
      : choices.find((item) => item.week > day.week && item.weekday === day.weekday);
    // The last (partial) week may not have this weekday: fall back to the nearest existing day.
    if (!target) target = direction < 0 ? choices.findLast((item) => item.week < day.week) : choices.find((item) => item.week > day.week);
  } else return;
  event.preventDefault();
  if (target) setActiveCell(target.date, true);
}
function setActiveCell(date, focus) {
  if (state.activeDate) {
    const previous = state.cells.get(state.activeDate);
    if (previous) previous.tabIndex = -1;
  }
  state.activeDate = date;
  const cell = state.cells.get(date);
  if (!cell) return;
  cell.tabIndex = 0;
  if (focus) {
    cell.focus({ preventScroll: true });
    // Keep the focused cell visible inside the horizontal scroller only.
    const scroller = $('#heat-scroller');
    const box = cell.getBoundingClientRect();
    const frame = scroller.getBoundingClientRect();
    if (box.left < frame.left + 38) scroller.scrollLeft += box.left - frame.left - 42;
    if (box.right > frame.right - 6) scroller.scrollLeft += box.right - frame.right + 10;
    showTip(state.model.byDate.get(date), cell.getBoundingClientRect().left + box.width / 2, box.top);
  }
}
function renderLegend() {
  const legend = $('#legend');
  legend.replaceChildren(el('span', null, 'Less'));
  POWER[currentTheme()].forEach((color, level) => {
    const swatch = el('i');
    swatch.style.setProperty('--cell-color', color);
    swatch.setAttribute('role', 'img');
    swatch.setAttribute('aria-label', `GitHub contribution intensity level ${level} of 4`);
    legend.append(swatch);
  });
  legend.append(el('span', null, 'More'));
}

// ---------- stats ----------
function renderStats() {
  const model = state.model;
  const hasDays = model.days.length > 0;
  $('#metric-total').textContent = state.available ? formatCount(model.total) : '—';
  $('#metric-active').textContent = hasDays ? formatCount(model.activeCount) : '—';
  $('#metric-streak').replaceChildren(document.createTextNode(hasDays ? formatCount(model.streak.longest) : '—'));
  if (hasDays) $('#metric-streak').append(el('small', null, ' days'));
  $('#stage-range').textContent = dateRange(model.start, model.end);
  $('#total-line').textContent = hasDays
    ? `${formatCount(model.total)} contributions · ${formatCount(model.privateCount)} private · ${dateRange(model.start, model.end)}`
    : state.available ? 'No daily contribution records in this snapshot yet.' : 'Contribution data is unavailable right now.';
  const generated = typeof model.stats.generated_at === 'string' ? model.stats.generated_at.slice(0, 10) : '';
  $('#generated').textContent = generated && formatDate(generated) !== 'Not available' ? `Snapshot updated ${fullDate(generated)}.` : model.end ? `Snapshot through ${fullDate(model.end)}.` : 'Snapshot date unavailable.';
  $('#explore-day').disabled = !hasDays;
  $('#replay-progress').disabled = !hasDays;
  // One step per day, so the arrow keys move the replay a day at a time.
  $('#replay-progress').step = model.days.length > 1 ? String(1 / (model.days.length - 1)) : 'any';
  $('#filter').disabled = !hasDays;
  $('#highlights').disabled = !hasDays || !model.peak;
  $('#highlight-month').disabled = !model.bestMonth?.dates?.length;
  $('#download-card').disabled = !hasDays;
  renderMomentum();
  const lead = $('#weekday-lead');
  lead.replaceChildren(document.createTextNode(hasDays ? model.peak ? WEEKDAYS[model.busiestWeekday] : 'No activity yet' : 'No daily record'));
  if (hasDays && model.peak) lead.append(el('small', null, `${formatCount(model.weekdayTotals[model.busiestWeekday])} contributions · busiest weekday`));
  const weekdays = $('#weekday-chart');
  weekdays.replaceChildren();
  if (hasDays) {
    const scale = Math.max(1, ...model.weekdayTotals);
    model.weekdays.forEach((item, index) => {
      const row = el('div', `weekday-row${model.peak && index === model.busiestWeekday ? ' is-busiest' : ''}`);
      row.setAttribute('aria-label', `${item.label}: ${formatCount(item.count)} contributions`);
      const track = el('span', 'weekday-row__track');
      const fill = el('i', 'weekday-row__fill');
      fill.style.setProperty('--bar-width', `${item.count / scale * 100}%`);
      track.setAttribute('aria-hidden', 'true');
      track.append(fill);
      row.append(el('span', null, item.label.slice(0, 3)), track, el('strong', null, formatCount(item.count)));
      weekdays.append(row);
    });
  }
  const rate = Math.round(model.activeRate * 100);
  $('#active-rate').textContent = model.observedDays ? `${rate}%` : '—';
  $('#ring-value').style.strokeDasharray = `${rate} 100`;
  $('#consistency-note').textContent = model.observedDays ? `${formatCount(model.activeCount)} active days in ${formatCount(model.observedDays)} observed account days.` : hasDays ? 'No account days observed in this snapshot.' : 'No daily records to measure yet.';
  $('#best-week-value').textContent = hasDays ? `${formatCount(model.bestWeek.total)} contributions` : '—';
  $('#best-week-range').textContent = hasDays ? model.peak ? dateRange(model.bestWeek.start, model.bestWeek.end) : 'No activity in observed weeks.' : 'No daily record yet';
  $('#best-week').disabled = !model.peak;
}
function renderMomentum() {
  const model = state.model;
  const momentum = model.momentum;
  const value = $('#momentum-value');
  value.replaceChildren(document.createTextNode(model.days.length ? formatCount(momentum.current) : '—'));
  if (momentum.pct != null) value.append(el('small', null, `${momentum.pct >= 0 ? '+' : ''}${momentum.pct}%`));
  else if (model.days.length) value.append(el('small', null, momentum.comparable ? 'No prior-period activity' : 'No comparable prior period'));
  $('#momentum-label').textContent = state.available ? momentum.label : 'Monthly records are unavailable.';
  $('#momentum-period').textContent = !model.days.length ? 'No daily record' : momentum.partial ? 'Partial month' : 'Complete month';
  const chart = $('#month-chart');
  chart.replaceChildren();
  const months = model.months.filter((month) => month.dates.some((date) => !model.byDate.get(date).sea)).slice(-6);
  const scale = Math.max(1, ...months.map((month) => month.total));
  months.forEach((month) => {
    const partial = momentum.partial && month.key === model.end.slice(0, 7);
    const button = el('button', `month-bar${partial ? ' is-partial' : ''}`);
    button.type = 'button';
    button.dataset.action = 'highlight-month';
    button.dataset.month = month.key;
    button.setAttribute('aria-label', `${formatCount(month.total)} contributions in ${formatDate(`${month.key}-01`, { month: 'long', year: 'numeric' })}${partial ? ', partial month' : ''}. Explore a day in this month.`);
    const bar = el('span', 'month-bar__column');
    bar.style.setProperty('--bar-height', `${Math.max(2, month.total / scale * 86)}px`);
    button.append(el('span', 'month-bar__value', formatCount(month.total)), bar, el('span', 'month-bar__label', month.label));
    button.addEventListener('click', () => exploreMonth(month));
    chart.append(button);
  });
}
function exploreMonth(month) {
  if (!month?.dates.length) return;
  // The busiest day of the month (earliest on ties), or its first day when the month is empty.
  const date = month.dates.reduce((best, key) => (state.model.byDate.get(key).count > state.model.byDate.get(best).count ? key : best), month.dates[0]);
  setFilter('all');
  selectHighlight(date);
}
function selectHighlight(date) {
  setSelected(date, { focus: true });
  if (!mqMobile.matches) $('#stage').scrollIntoView({ block: 'center', behavior: mqReduce.matches ? 'instant' : 'smooth' });
}
function setReplayProgress(progress) {
  state.replayProgress = Math.max(0, Math.min(1, Number(progress) || 0));
  const at = replayAt(state.model, state.replayProgress);
  const slider = $('#replay-progress');
  if (Number(slider.value) !== state.replayProgress) slider.value = String(state.replayProgress);
  $('#replay-date').textContent = at.date ? shortDate(at.date) : 'No daily record';
  $('#replay-total').textContent = state.available ? formatCount(at.total) : '—';
  slider.setAttribute('aria-valuetext', at.date ? `${shortDate(at.date)}, ${formatCount(at.total)} contributions to date` : 'No daily record');
  // Applied synchronously so a scrub is exact even when motion is off or reduced.
  sceneCall('setReplayProgress', state.replayProgress);
  syncCells();
}
function syncReplay() {
  const button = $('#replay-play');
  const reduced = mqReduce.matches;
  button.disabled = !state.model?.days.length;
  button.dataset.state = state.playing ? 'on' : 'off';
  $('span', button).textContent = reduced ? 'Step one week' : state.playing ? 'Pause history' : 'Play history';
  $('#replay-note').hidden = !reduced;
}
function stopReplay() {
  state.playing = false;
  cancelAnimationFrame(state.replayFrame);
  syncReplay();
}
function playReplay() {
  if (state.playing) return stopReplay();
  const days = state.model.days.length;
  if (!days) return;
  // Reduced motion: each press steps one week forward (wrapping to the start) instead of animating.
  if (mqReduce.matches) {
    setReplayProgress(state.replayProgress >= 1 ? 0 : state.replayProgress + 7 / Math.max(1, days - 1));
    return;
  }
  if (state.replayProgress >= 1) setReplayProgress(0);
  state.playing = true;
  syncReplay();
  const startedAt = performance.now() - state.replayProgress * REPLAY_MS;
  const frame = (timestamp) => {
    if (!state.playing) return;
    setReplayProgress((timestamp - startedAt) / REPLAY_MS);
    if (state.replayProgress >= 1) stopReplay();
    else state.replayFrame = requestAnimationFrame(frame);
  };
  state.replayFrame = requestAnimationFrame(frame);
}
function syncMotion() {
  $('#btn-motion').textContent = state.motion ? 'Pause motion' : 'Enable motion';
  $('#btn-motion').dataset.state = state.motion ? 'on' : 'off';
  $('#btn-motion').disabled = mqReduce.matches;
  $('#motion-note').textContent = mqReduce.matches ? 'Reduced motion is on. Camera motion and automatic replay are paused; you can still scrub the timeline.' : 'The landscape starts still. Motion is always optional.';
  if (mqReduce.matches) stopReplay();
  else syncReplay();
}
function syncInteractive() {
  $('#stage').classList.toggle('is-interactive', state.interactive);
  $('#interactive-toggle').dataset.state = state.interactive ? 'on' : 'off';
  $('#interactive-toggle').textContent = state.interactive ? 'Done exploring' : 'Explore in 3D';
  $('#stage-hint').textContent = state.interactive ? (mqCoarse.matches || mqMobile.matches ? 'Drag to orbit · Tap Done exploring to scroll' : 'Drag to orbit · Select a tower to inspect') : 'Scroll freely · Enable 3D to orbit';
}

// ---------- theme ----------
function applyTheme(theme, persist) {
  document.documentElement.dataset.theme = theme;
  if (persist) { try { localStorage.setItem('warroom-theme', theme); } catch (e) { /* storage unavailable */ } }
  $('#theme-toggle').setAttribute('aria-label', theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme');
  $('meta[name="theme-color"]').content = theme === 'dark' ? '#121d25' : '#f5f2e9';
  $('#stage-fallback').src = `./battlefield-${theme}.svg`;
  renderLegend();
  if (state.model) syncCells();
  if (state.model?.days.length && !state.sceneUnavailable) init3D();
}
function initTheme() {
  applyTheme(currentTheme(), false);
  $('#theme-toggle').addEventListener('click', () => applyTheme(currentTheme() === 'dark' ? 'light' : 'dark', true));
}

// ---------- 3D ----------
function disposeScene() {
  const scene = state.scene;
  state.scene = null;
  if (scene) {
    try { scene.dispose(); } catch (error) { console.warn('Landscape cleanup:', error); }
  }
  $('#stage-canvas').replaceChildren();
  $('#stage-labels').replaceChildren();
}
function fallback3D() {
  state.sceneGeneration++;
  disposeScene();
  state.sceneUnavailable = true;
  $('#atlas').classList.add('is-fallback');
  $('#stage').classList.remove('is-ready', 'is-interactive');
  $('#fallback-note').hidden = false;
  $('#stage-canvas').hidden = true;
  $('#stage-fallback').hidden = false;
  $('#stage-loading').hidden = true;
  $('#view-options').open = false;
}
async function init3D() {
  // ?flat forces the no-WebGL layout (handy for testing the fallback).
  if (new URLSearchParams(location.search).has('flat') || !state.model.days.length) return fallback3D();
  const generation = ++state.sceneGeneration;
  disposeScene();
  $('#stage').classList.remove('is-ready');
  $('#stage-canvas').hidden = false;
  $('#stage-loading').hidden = false;
  let timeout;
  try {
    const mod = await Promise.race([
      import('./scene.js'),
      new Promise((resolve, reject) => { timeout = setTimeout(() => reject(new Error('Interactive module timed out')), 12000); }),
    ]);
    clearTimeout(timeout);
    if (generation !== state.sceneGeneration) return;
    const scene = mod.createScene({
      container: $('#stage-canvas'), labels: $('#stage-labels'), toast: $('#stage-toast'),
      model: state.model, theme: currentTheme(), motion: state.motion, reducedMotion: mqReduce.matches,
      quality: state.quality, interactive: state.interactive,
      onHover(date, x, y) {
        if (generation === state.sceneGeneration) setHover(date, 'scene', date ? { x, y } : null);
      },
      onPick(date) {
        if (generation !== state.sceneGeneration || !state.model.byDate.has(date)) return;
        setSelected(date, { toggle: true, focus: mqMobile.matches });
      },
    });
    state.scene = scene;
    // Apply touch/pointer configuration before the first rendered frame.
    scene.setInteractive(state.interactive);
    scene.setReplayProgress(state.replayProgress);
    scene.setFilter(state.filter);
    scene.setCameraPreset(state.preset);
    scene.setSelection(state.selectedDate);
    scene.setHover(state.hoverDate);
    state.sceneUnavailable = false;
    $('#atlas').classList.remove('is-fallback');
    $('#fallback-note').hidden = true;
    $('#stage').classList.add('is-ready');
    $('#stage-loading').hidden = true;
    syncInteractive();
  } catch (error) {
    clearTimeout(timeout);
    if (generation !== state.sceneGeneration) return;
    console.warn('Interactive landscape unavailable:', error);
    fallback3D();
  }
}
function downloadCard() {
  const model = state.model;
  const status = $('#download-status');
  try {
    const dark = currentTheme() === 'dark';
    const canvas = document.createElement('canvas');
    canvas.width = 1600;
    canvas.height = 1000;
    const ctx = canvas.getContext('2d');
    if (!ctx) throw new Error('2D canvas unavailable');
    const ink = dark ? '#e7e5d9' : '#223034';
    const muted = dark ? '#a2acae' : '#626b68';
    ctx.fillStyle = dark ? '#121d25' : '#f5f2e9';
    ctx.fillRect(0, 0, 1600, 1000);
    ctx.strokeStyle = dark ? '#34434a' : '#d9d9cb';
    ctx.lineWidth = 1;
    for (let i = 0; i < 11; i++) {
      ctx.beginPath();
      ctx.ellipse(1500, 100, 140 + i * 50, 75 + i * 30, -.3, 0, Math.PI * 2);
      ctx.stroke();
    }
    ctx.fillStyle = muted;
    ctx.font = '18px monospace';
    ctx.fillText('THE ENGINEERING ATLAS', 90, 95);
    ctx.fillStyle = ink;
    ctx.font = '70px Georgia';
    ctx.fillText('A world of contributions.', 85, 200);
    ctx.font = '24px sans-serif';
    ctx.fillText('Abhishek Vishwakarma', 90, 255);
    ctx.fillStyle = muted;
    ctx.font = '19px sans-serif';
    ctx.fillText('AI Engineer at REI Systems · Developing solutions since 2016', 90, 295);
    const unit = Math.min(20, 1160 / model.nWeeks);
    const polygon = (points, fill) => {
      ctx.beginPath();
      points.forEach(([x, y], index) => index ? ctx.lineTo(x, y) : ctx.moveTo(x, y));
      ctx.closePath();
      ctx.fillStyle = fill;
      ctx.fill();
    };
    for (const day of model.days) {
      const x = 135 + day.week * unit + day.weekday * 17;
      const y = 625 - day.week * unit * .14 + day.weekday * 12;
      const h = day.sea ? 0 : 3 + day.count / model.maxCount * 165;
      const color = day.sea ? (dark ? '#293e45' : '#dce4df') : POWER[currentTheme()][day.level];
      polygon([[x, y], [x + unit * .78, y - 4], [x + unit * .78, y - h - 4], [x, y - h]], dark ? '#314044' : '#d2c3a6');
      polygon([[x + unit * .78, y - 4], [x + unit * .78 + 14, y + 4], [x + unit * .78 + 14, y - h + 4], [x + unit * .78, y - h - 4]], dark ? '#4b4b37' : '#c4b28b');
      polygon([[x, y - h], [x + unit * .78, y - h - 4], [x + unit * .78 + 14, y - h + 4], [x + 14, y - h + 8]], color);
    }
    ctx.strokeStyle = dark ? '#34434a' : '#d9d9cb';
    ctx.beginPath(); ctx.moveTo(90, 770); ctx.lineTo(1510, 770); ctx.stroke();
    [[`${formatCount(model.total)}`, 'CONTRIBUTIONS'], [`${formatCount(model.activeCount)}`, 'ACTIVE DAYS'], [`${formatCount(model.streak.longest)}`, 'LONGEST STREAK · DAYS']].forEach(([value, label], index) => {
      const x = 90 + index * 440;
      ctx.fillStyle = ink; ctx.font = '54px Georgia'; ctx.fillText(value, x, 845);
      ctx.fillStyle = muted; ctx.font = '15px monospace'; ctx.fillText(label, x, 880);
    });
    ctx.fillStyle = muted; ctx.font = '15px sans-serif';
    ctx.fillText(`${dateRange(model.start, model.end)} · Public contribution aggregates only`, 90, 955);
    const link = el('a');
    link.download = `engineering-atlas-${model.end || 'snapshot'}.png`;
    link.href = canvas.toDataURL('image/png');
    link.click();
    status.textContent = 'Your contribution card is ready.';
  } catch (error) {
    console.warn('Contribution card unavailable:', error);
    status.textContent = 'The contribution card could not be created. The daily records remain available above.';
  }
}

// ---------- boot ----------
function bindControls() {
  $('#details-close').addEventListener('click', dismissDetails);
  $('#day-prev').addEventListener('click', () => stepSelection(-1));
  $('#day-next').addEventListener('click', () => stepSelection(1));
  $('#day-input').addEventListener('change', (event) => {
    if (!state.model.byDate.has(event.target.value)) {
      $('#selection-status').textContent = 'No daily record is available for that date.';
      event.target.value = state.selectedDate;
      return;
    }
    const day = state.model.byDate.get(event.target.value);
    if (!matchesFilter(day, state.model, state.filter)) setFilter('all');
    setSelected(day.date);
  });
  $('#explore-day').addEventListener('click', () => setSelected(state.selectedDate || filteredDays().at(-1)?.date, { focus: true }));
  $('#filter').addEventListener('change', (event) => setFilter(event.target.value));
  $('#highlights').addEventListener('change', (event) => {
    const model = state.model;
    const choice = event.target.value;
    if (choice === 'peak' && model.peak) { setFilter('top'); selectHighlight(model.peak.date); }
    if (choice === 'streak' && model.streak.longest_start) { setFilter('streak'); selectHighlight(model.streak.longest_start); }
    if (choice === 'month' && model.bestMonth) exploreMonth(model.bestMonth);
    event.target.value = '';
  });
  $('#best-week').addEventListener('click', () => { setFilter('all'); selectHighlight(state.model.bestWeek.start); });
  document.querySelectorAll('[data-camera]').forEach((button) => button.addEventListener('click', () => {
    state.preset = button.dataset.camera;
    document.querySelectorAll('[data-camera]').forEach((item) => item.setAttribute('aria-pressed', String(item === button)));
    sceneCall('setCameraPreset', state.preset);
  }));
  $('#btn-motion').addEventListener('click', () => {
    if (mqReduce.matches) return;
    state.motion = !state.motion;
    sceneCall('setMotion', state.motion);
    syncMotion();
  });
  $('#quality').addEventListener('change', (event) => { state.quality = event.target.value; sceneCall('setQuality', state.quality); });
  $('#interactive-toggle').addEventListener('click', () => {
    state.interactive = !state.interactive;
    sceneCall('setInteractive', state.interactive);
    syncInteractive();
  });
  $('#replay-play').addEventListener('click', playReplay);
  $('#replay-progress').addEventListener('input', (event) => { stopReplay(); setReplayProgress(event.target.value); });
  $('#download-card').addEventListener('click', downloadCard);
  mqReduce.addEventListener('change', () => {
    if (mqReduce.matches) state.motion = false;
    syncMotion();
    if (state.scene) init3D();
  });
  const disableTouchInteraction = () => {
    if (!mqCoarse.matches && !mqMobile.matches) return;
    state.interactive = false;
    sceneCall('setInteractive', false);
    syncInteractive();
  };
  mqCoarse.addEventListener('change', disableTouchInteraction);
  mqMobile.addEventListener('change', disableTouchInteraction);
  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape' || event.defaultPrevented) return;
    $('#view-options').open = false;
    if (state.selectedDate) dismissDetails();
    if (state.interactive && (mqCoarse.matches || mqMobile.matches)) {
      state.interactive = false;
      sceneCall('setInteractive', false);
      syncInteractive();
    }
  });
  document.addEventListener('pointerdown', (event) => { if (!$('#view-options').contains(event.target)) $('#view-options').open = false; });
  document.addEventListener('visibilitychange', () => { if (document.hidden) stopReplay(); });
  window.addEventListener('scroll', () => {
    if (tip.hidden) return;
    // Keep a keyboard-focused cell's tooltip attached to it; otherwise drop the tooltip.
    const cell = document.activeElement?.closest?.('.c[data-date]');
    if (cell && state.hoverDate === cell.dataset.date) {
      const box = cell.getBoundingClientRect();
      if (box.bottom < 0 || box.top > innerHeight) hideTip();
      else showTip(state.model.byDate.get(cell.dataset.date), box.left + box.width / 2, box.top);
    } else hideTip();
  }, { passive: true });
  $('#heat-scroller').addEventListener('scroll', () => {
    const cell = document.activeElement?.closest?.('.c[data-date]');
    if (cell && state.hoverDate === cell.dataset.date) {
      const box = cell.getBoundingClientRect();
      const frame = $('#heat-scroller').getBoundingClientRect();
      if (box.left >= frame.left + 30 && box.right <= frame.right) showTip(state.model.byDate.get(cell.dataset.date), box.left + box.width / 2, box.top);
      else hideTip();
    } else hideTip();
  }, { passive: true });
}
async function main() {
  initTheme();
  bindControls();
  let stats = {};
  try {
    const response = await fetch('./stats.json', { cache: 'no-cache' });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    if (!data || typeof data !== 'object' || Array.isArray(data)) throw new Error('Invalid contribution snapshot');
    stats = data;
    state.available = true;
  } catch (error) {
    console.warn('Contribution snapshot unavailable:', error);
  }
  state.model = buildModel(stats);
  renderHeatmap();
  renderStats();
  renderDetails();
  renderLegend();
  setReplayProgress(1);
  syncMotion();
  syncReplay();
  syncInteractive();
  await init3D();
}
main().catch((error) => {
  console.warn('Atlas initialization unavailable:', error);
  $('#total-line').textContent = 'The daily record is unavailable right now. The complete contribution map is still available.';
  fallback3D();
});
