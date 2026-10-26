export const POWER = {
  light: ['#EFE6D2', '#FFE08A', '#F6B800', '#E5383B', '#C1121F'],
  dark: ['#1E1A12', '#6B5214', '#F6B800', '#E5383B', '#FF4D5A'],
};

export const WEEKDAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
const DAY = 86400000;
const count = (value) => Number.isFinite(Number(value)) ? Math.max(0, Math.floor(Number(value))) : 0;
const dateValue = (value) => typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value)
  && Number.isFinite(Date.parse(`${value}T00:00:00Z`))
  && new Date(`${value}T00:00:00Z`).toISOString().slice(0, 10) === value ? value : '';
export const toUTC = (value) => new Date(`${value}T00:00:00Z`);
export const formatDate = (value, options = { month: 'short', day: 'numeric' }) =>
  dateValue(value) ? new Intl.DateTimeFormat('en-US', { timeZone: 'UTC', ...options }).format(toUTC(value)) : 'Not available';
export const formatCount = (value) => new Intl.NumberFormat('en-US').format(count(value));
export const contributionText = (value, date) => {
  const n = count(value);
  return `${n ? `${formatCount(n)} contribution${n === 1 ? '' : 's'}` : 'No contributions'} on ${formatDate(date, { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })}`;
};

export function buildModel(input = {}) {
  const stats = input && typeof input === 'object' ? input : {};
  const joined = dateValue(stats.joined);
  const seen = new Set();
  const raw = [];
  for (const week of Array.isArray(stats.weeks) ? stats.weeks : []) {
    for (const source of Array.isArray(week) ? week : []) {
      if (!source || typeof source !== 'object') continue;
      const date = dateValue(source.date);
      if (!date || seen.has(date)) continue;
      seen.add(date);
      raw.push({ date, count: count(source.count), level: Math.min(4, count(source.level)) });
    }
  }
  raw.sort((a, b) => a.date.localeCompare(b.date));
  const start = raw[0]?.date || '';
  const end = raw[raw.length - 1]?.date || '';
  const origin = start ? +toUTC(start) - toUTC(start).getUTCDay() * DAY : 0;
  const nWeeks = start ? Math.floor((+toUTC(end) - origin) / (7 * DAY)) + 1 : 1;
  const weeks = Array.from({ length: nWeeks }, () => []);
  const days = raw.map((source, idx) => {
    const weekday = toUTC(source.date).getUTCDay();
    const week = Math.floor((+toUTC(source.date) - origin) / (7 * DAY));
    const day = { ...source, idx, weekday, week, sea: !!joined && source.date < joined };
    weeks[week].push(day);
    return day;
  });
  const byDate = new Map(days.map((day) => [day.date, day]));
  const grid = weeks.map((week) => {
    const result = Array(7).fill(null);
    for (const day of week) result[day.weekday] = day.idx;
    return result;
  });
  const weekTotals = weeks.map((week) => week.reduce((sum, day) => sum + day.count, 0));
  const total = days.length ? weekTotals.reduce((sum, value) => sum + value, 0) : count(stats.totals?.contributions);
  const privateCount = Math.min(total, count(stats.totals?.private));
  const active = days.filter((day) => day.count > 0).sort((a, b) => b.count - a.count || a.date.localeCompare(b.date));
  const rank = new Map();
  const tieCount = new Map();
  active.forEach((day, index) => {
    day.rank = index && active[index - 1].count === day.count ? active[index - 1].rank : index + 1;
    rank.set(day.idx, day.rank);
    tieCount.set(day.count, (tieCount.get(day.count) || 0) + 1);
  });
  const monthly = {};
  const weekdayTotals = Array(7).fill(0);
  let cumulative = 0;
  let run = [];
  let longest = [];
  let previous = null;
  for (const day of days) {
    const key = day.date.slice(0, 7);
    monthly[key] = (monthly[key] || 0) + day.count;
    weekdayTotals[day.weekday] += day.count;
    cumulative += day.count;
    day.cumulative = cumulative;
    if (day.count > 0) {
      run = previous && +toUTC(day.date) - +toUTC(previous.date) === DAY ? [...run, day] : [day];
      if (run.length > longest.length) longest = run;
    } else run = [];
    previous = day;
  }
  let current = [];
  let tail = days.length - 1;
  if (tail >= 0 && days[tail].count === 0) tail--;
  if (tail >= 0 && end && +toUTC(end) - +toUTC(days[tail].date) <= DAY) {
    for (let index = tail; index >= 0 && days[index].count > 0; index--) {
      if (index < tail && +toUTC(days[index + 1].date) - +toUTC(days[index].date) !== DAY) break;
      current.unshift(days[index]);
    }
  }
  const longestDates = new Set(longest.map((day) => day.date));
  const eligible = days.filter((day) => !day.sea);
  const meanPerDay = eligible.length ? eligible.reduce((sum, day) => sum + day.count, 0) / eligible.length : 0;
  for (const day of days) {
    day.inLongestStreak = longestDates.has(day.date);
    day.ratioToMean = meanPerDay > 0 ? day.count / meanPerDay : 0;
  }
  let coast = 0;
  for (const week of weeks) {
    if (week.length && week.every((day) => day.sea)) coast++;
    else break;
  }
  const months = Object.entries(monthly).map(([key, value]) => ({
    key, total: value, label: formatDate(`${key}-01`, { month: 'short' }),
    dates: days.filter((day) => day.date.startsWith(key)).map((day) => day.date),
  }));
  // Best month: greatest total, earliest on ties, null when nothing is positive.
  const bestMonth = months.reduce((best, month) => (month.total > 0 && (!best || month.total > best.total) ? month : best), null);
  const bestWeekIndex = weekTotals.length ? weekTotals.indexOf(Math.max(...weekTotals)) : 0;
  const bestWeekDays = weeks[bestWeekIndex] || [];
  const busiestWeekday = weekdayTotals.indexOf(Math.max(...weekdayTotals));
  const model = {
    stats, days, weeks, grid, byDate, nWeeks, coast, joined, start, end, total, privateCount,
    publicCount: Math.max(0, total - privateCount), activeCount: active.length,
    observedDays: eligible.length, activeRate: eligible.length ? eligible.filter((day) => day.count > 0).length / eligible.length : 0,
    maxCount: Math.max(1, ...days.map((day) => day.count)), meanPerDay,
    weekTotals, monthly, months, bestMonth, rank, tieCount, peak: active[0] || null,
    weekdayTotals, weekdays: WEEKDAYS.map((label, index) => ({ label, count: weekdayTotals[index] })), busiestWeekday,
    topDates: new Set(active.slice(0, 10).map((day) => day.date)), longestDates,
    streak: {
      current: current.length, current_start: current[0]?.date || null,
      longest: longest.length, longest_start: longest[0]?.date || null, longest_end: longest[longest.length - 1]?.date || null,
    },
    bestWeek: { index: bestWeekIndex, total: weekTotals[bestWeekIndex] || 0, start: bestWeekDays[0]?.date || '', end: bestWeekDays[bestWeekDays.length - 1]?.date || '' },
  };
  model.momentum = buildMomentum(model);
  return model;
}

function buildMomentum(model) {
  if (!model.end) return { current: 0, previous: 0, pct: null, comparable: false, label: 'No contribution data yet' };
  const latest = toUTC(model.end);
  const year = latest.getUTCFullYear();
  const month = latest.getUTCMonth();
  const date = latest.getUTCDate();
  const iso = (value) => value.toISOString().slice(0, 10);
  const monthStart = iso(new Date(Date.UTC(year, month, 1)));
  const currentStart = [monthStart, model.start, model.joined].filter(Boolean).sort().pop();
  if (currentStart > model.end) return { current: 0, previous: 0, pct: null, comparable: false, label: 'No observed account days yet' };
  const firstDay = toUTC(currentStart).getUTCDate();
  const previousLast = new Date(Date.UTC(year, month, 0)).getUTCDate();
  const completed = date === new Date(Date.UTC(year, month + 1, 0)).getUTCDate();
  const previousStart = iso(new Date(Date.UTC(year, month - 1, Math.min(firstDay, previousLast))));
  const previousEnd = iso(new Date(Date.UTC(year, month - 1, completed ? previousLast : Math.min(date, previousLast))));
  const inWindow = (start, end) => model.days.filter((day) => day.date >= start && day.date <= end && !day.sea);
  const currentDays = inWindow(currentStart, model.end);
  const previousDays = inWindow(previousStart, previousEnd);
  const expected = Math.round((+toUTC(previousEnd) - +toUTC(previousStart)) / DAY) + 1;
  const comparable = previousDays.length === expected && expected > 0;
  const current = currentDays.reduce((sum, day) => sum + day.count, 0);
  const previous = previousDays.reduce((sum, day) => sum + day.count, 0);
  return {
    current, previous, comparable, pct: comparable && previous > 0 ? Math.round((current / previous - 1) * 100) : null,
    currentStart, currentEnd: model.end, previousStart, previousEnd, partial: !completed,
    label: `${formatDate(currentStart)}–${formatDate(model.end, { day: 'numeric' })} compared with ${formatDate(previousStart)}–${formatDate(previousEnd, { day: 'numeric' })}`,
  };
}

export function matchesFilter(day, model, filter = 'all') {
  if (filter === 'top') return model.topDates.has(day.date);
  if (filter === 'streak') return model.longestDates.has(day.date);
  if (filter === 'weekdays') return !day.sea && day.weekday > 0 && day.weekday < 6;
  if (filter === 'weekends') return !day.sea && (day.weekday === 0 || day.weekday === 6);
  return true;
}

export function replayAt(model, progress) {
  const p = Number.isFinite(Number(progress)) ? Math.max(0, Math.min(1, Number(progress))) : 1;
  if (!model.days.length) return { index: -1, date: '', total: 0 };
  const index = Math.round(p * (model.days.length - 1));
  return { index, date: model.days[index].date, total: model.days[index].cumulative };
}
