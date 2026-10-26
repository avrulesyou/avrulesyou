import { buildModel, matchesFilter, replayAt, contributionText } from '../site/model.js';

const equal = (actual, expected, message) => {
  if (JSON.stringify(actual) !== JSON.stringify(expected)) throw new Error(`${message}: ${JSON.stringify(actual)} !== ${JSON.stringify(expected)}`);
};
const finite = (model) => {
  for (const value of [model.total, model.activeRate, model.meanPerDay, model.maxCount, model.momentum.current, model.momentum.previous]) {
    if (!Number.isFinite(value)) throw new Error('Non-finite aggregate');
  }
};
const fixture = (start, counts, joined = start) => ({
  joined, totals: { private: 999999 },
  weeks: [counts.map((count, index) => {
    const date = new Date(`${start}T00:00:00Z`);
    date.setUTCDate(date.getUTCDate() + index);
    return { date: date.toISOString().slice(0, 10), count, level: count > 0 ? 2 : 0 };
  })],
});

export function runModelTests() {
  const empty = buildModel({});
  equal([empty.total, empty.activeCount, empty.peak, empty.streak.longest], [0, 0, null, 0], 'Empty data');
  equal(replayAt(empty, 0), { index: -1, date: '', total: 0 }, 'Empty replay');
  finite(empty);
  const zero = buildModel(fixture('2026-01-01', Array(20).fill(0)));
  equal([zero.total, zero.activeRate, zero.momentum.pct, zero.bestMonth], [0, 0, null, null], 'Zero activity');
  equal(empty.bestMonth, null, 'Empty best month');
  finite(zero);
  const one = buildModel(fixture('2026-01-01', [47]));
  equal([one.total, one.activeCount, one.streak.longest, one.privateCount, one.publicCount], [47, 1, 1, 47, 0], 'One day');
  equal(replayAt(one, 0).total, 47, 'Single day replay');
  const ranked = buildModel(fixture('2026-01-04', [4, 4, 2, 0, 1, 0, 0]));
  equal(ranked.days.map((day) => day.rank || 0), [1, 1, 3, 0, 4, 0, 0], 'Competition ranks');
  equal([ranked.streak.longest, ranked.streak.longest_start, ranked.streak.current], [3, '2026-01-04', 0], 'Streak and stale current');
  equal(ranked.days.filter((day) => matchesFilter(day, ranked, 'weekends')).map((day) => day.date), ['2026-01-04', '2026-01-10'], 'Weekend filter');
  equal(ranked.days.filter((day) => matchesFilter(day, ranked, 'streak')).length, 3, 'Streak filter');
  const joined = buildModel(fixture('2026-01-01', [0, 0, 3, 0], '2026-01-03'));
  equal([joined.observedDays, joined.activeRate, joined.meanPerDay], [2, 0.5, 1.5], 'Observed account period');
  const current = buildModel(fixture('2026-01-01', [0, 2, 2, 0]));
  equal([current.streak.current, current.streak.current_start], [2, '2026-01-02'], 'Yesterday-ended current streak');
  const full = buildModel(fixture('2026-01-01', Array(365).fill(1)));
  equal([full.total, full.activeCount, full.streak.longest, full.activeRate], [365, 365, 365, 1], 'Full year');
  equal(full.topDates.size, 10, 'Top ten deterministic ties');
  equal(replayAt(full, 0.5).total, 183, 'Replay cumulative');
  equal(replayAt(full, 1).total, 365, 'Replay final');
  finite(full);
  const malformed = buildModel({ weeks: [[null, { date: '2026-02-30', count: 2 }, { date: '2026-01-01', count: -4 }, { date: '2026-01-01', count: 9 }]] });
  equal([malformed.days.length, malformed.total], [1, 0], 'Invalid and duplicate days');
  const counts = Array(56).fill(1);
  for (let index = 31; index < 56; index++) counts[index] = 2;
  const momentum = buildModel(fixture('2026-01-01', counts));
  equal([momentum.momentum.current, momentum.momentum.previous, momentum.momentum.pct, momentum.momentum.previousEnd], [50, 25, 100, '2026-01-25'], 'Matched elapsed month comparison');
  equal([momentum.bestMonth.key, momentum.bestMonth.total, momentum.bestMonth.dates.length], ['2026-02', 50, 25], 'Best month by total');
  const tied = buildModel(fixture('2026-01-31', [3, 3]));
  equal(tied.bestMonth.key, '2026-01', 'Best month earliest on ties');
  const incomplete = buildModel(fixture('2026-01-20', Array(37).fill(1)));
  equal(incomplete.momentum.comparable, false, 'Missing previous-period coverage');
  equal(contributionText(0, '2026-01-01'), 'No contributions on Thursday, January 1, 2026', 'Zero tooltip');
  equal(contributionText(1, '2026-01-01'), '1 contribution on Thursday, January 1, 2026', 'Singular tooltip');
  const future = buildModel(fixture('2026-01-01', [0], '2026-02-01'));
  equal([future.observedDays, future.momentum.comparable], [0, false], 'No observed account days');
  finite(future);
  return { passed: true };
}
