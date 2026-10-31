/* Read saved cells only. No model, gap, error, interval or metric calculation. */
(function (root) {
  'use strict';
  const BASE = '../data/2025/release_2025_001/';
  const words = s => s.split(' ');
  const CONTRACT = Object.freeze({
    ratings: ['driver_rating_2025.csv', words('season driver teams teammates comparison_group teammate_changed season_appearances qualifying_rating dry_rating wet_rating combined_rating rating_units rating_status qualifying_weight dry_weight wet_weight qualifying_valid qualifying_eligible qualifying_effective_races dry_valid dry_eligible dry_effective_races wet_valid wet_eligible wet_effective_races races_included confidence combined_ci_low combined_ci_high bootstrap_valid dry_strict_count dry_linear_count monaco_included notes method_version')],
    periods: ['driver_rating_teammate_periods.csv', words('season driver period team teammate round_start round_end signal valid eligible missing coverage effective_races rating median missing_reasons warnings')],
    diagnostics: ['driver_rating_signal_diagnostics.csv', words('season driver signal valid eligible missing coverage effective_races rating median missing_reasons warnings single_race_ci_low single_race_ci_high single_race_round season_ci_low season_ci_high season_ci_reason')],
    ratingSummary: ['driver_rating_run_summary.json', null],
    metrics: ['metrics.csv', words('target period method pair_count weekend_count excluded_pair_count exclusion_reasons ties fallback_rows brier brier_ci_low brier_ci_high accuracy accuracy_ci_low accuracy_ci_high log_loss log_loss_ci_low log_loss_ci_high')],
    comparisons: ['comparisons.csv', words('target period candidate baseline comparison metric difference ci_low ci_high pair_count weekend_count')],
    counts: ['counts.csv', words('target eligible_rows initial_training_rows initial_training_weekends main_rows main_weekends main_exclusions early_first_round early_rows early_weekends early_fallback_rows')],
    summary: ['summary.json', null],
    config: ['prediction_test_config.json', null],
    winners: ['baseline_winners.csv', words('target period metric best_simple_baselines exploratory')],
    eligibility: ['eligibility.csv', words('target pair_id round_number driver_a driver_b eligible reason_code all_reasons')],
    predictions: ['predictions.csv', words('target period method pair_id round_number race team driver_a driver_b probability outcome status_a status_b prior_rating_a prior_rating_b rating_difference qualifying_advantage feature_source_max_round training_rows training_max_round fallback_reason')]
  });
  // Stability is download-only. Qualifying and race-gap files are not page inputs
  // in this version, including the by-round file's recorded lap-time columns.
  const DOWNLOADS = Object.freeze([...Object.values(CONTRACT).map(x => x[0]), 'group_stability.csv']);
  const SIGNALS = Object.freeze(['qualifying', 'dry', 'wet']);
  const METRICS = Object.freeze(['brier', 'accuracy', 'log_loss']);
  const TARGETS = Object.freeze(['main_both_finish', 'all_starters', 'no_double_retirement']);
  const PERIODS = Object.freeze(['main', 'early', 'early_fallback']);
  function check(ok, message) { if (!ok) throw new Error(message); }
  function blank(v) { return v === '' || v === null || v === undefined; }
  function numeric(v) { return !blank(v) && Number.isFinite(Number(v)); }
  function parseCSV(text, columns) {
    // Quoted commas, escaped quotes, CRLF, embedded newlines and empty cells.
    text = text.replace(/^\uFEFF/, '');
    const rows = []; let row = [], cell = '', quoted = false, closed = false;
    for (let i = 0; i < text.length; i++) {
      const ch = text[i];
      if (quoted) {
        if (ch === '"' && text[i + 1] === '"') { cell += '"'; i++; }
        else if (ch === '"') { quoted = false; closed = true; }
        else cell += ch;
      } else if (ch === '"' && cell === '' && !closed) quoted = true;
      else if (ch === ',') { row.push(cell); cell = ''; closed = false; }
      else if (ch === '\n' || ch === '\r') {
        if (ch === '\r' && text[i + 1] === '\n') i++;
        row.push(cell); rows.push(row); row = []; cell = ''; closed = false;
      } else { check(!closed && ch !== '"', 'Malformed CSV quoting'); cell += ch; }
    }
    check(!quoted, 'Unclosed CSV quote');
    if (cell || row.length || closed) { row.push(cell); rows.push(row); }
    const header = rows.shift();
    check(header && new Set(header).size === header.length, 'Missing or duplicate CSV headers');
    check(columns.every(c => header.includes(c)), 'Required saved column missing');
    return rows.map(values => {
      check(values.length === header.length, 'CSV row width differs from header');
      return Object.fromEntries(columns.map(c => [c, values[header.indexOf(c)]]));
    });
  }
  function fileURL(file, base = BASE) {
    check(DOWNLOADS.includes(file) || file === 'releases.json', 'File outside dashboard allowlist');
    check(base === BASE, 'Release base cannot be supplied by a URL filter');
    return base + file;
  }
  function sourceEntry(release, file) {
    const matches = release.sources.filter(s => s.package_path === 'docs/data/2025/release_2025_001/' + file);
    check(matches.length === 1, 'Missing or duplicate source manifest entry');
    return matches[0];
  }
  function validateMetadata(metadata) {
    check(metadata.schema_version === 1 && metadata.releases.length === 1, 'Unsupported release metadata');
    const r = metadata.releases[0];
    check(r.season === 2025 && r.release_id === 'release_2025_001', 'Unexpected packaged release');
    check(r.results_last_updated === '2026-10-23', 'Unexpected approved release date');
    check(r.display_rules.global_leaderboard === false && r.display_rules.rank_numbers === false, 'Unsafe display rules');
    check(r.display_rules.driver_order === 'alphabetical', 'Unexpected driver order');
    check(r.sources.length === 17, 'Incomplete release manifest');
    for (const file of DOWNLOADS) {
      const s = sourceEntry(r, file);
      check(/^[a-f0-9]{64}$/.test(s.source_sha256), 'Invalid source fingerprint');
    }
    check(r.teaching_examples.purpose === 'teaching examples, not top results', 'Missing teaching-example label');
    check(r.teaching_examples.examples.map(e => e.group).join('|') === 'HAM+LEC|NOR+PIA', 'Unexpected teaching examples');
    return r;
  }
  function createLoader(fetcher, cryptoObject, pageURL) {
    const pending = new Map(); let release;
    async function request(file) {
      const url = new URL(fileURL(file), pageURL);
      check(url.origin === new URL(pageURL).origin, 'External data URL blocked');
      const response = await fetcher(url.href, {credentials: 'omit', redirect: 'error', cache: 'no-store'});
      check(response.ok, 'Saved file unavailable: ' + file);
      return new Uint8Array(await response.arrayBuffer());
    }
    async function metadata() {
      if (!pending.has('metadata')) pending.set('metadata', (async () => {
        release = validateMetadata(JSON.parse(new TextDecoder().decode(await request('releases.json'))));
        return release;
      })());
      return pending.get('metadata');
    }
    async function load(key) {
      check(Object.hasOwn(CONTRACT, key), 'Unknown data key');
      if (!pending.has(key)) pending.set(key, (async () => {
        const r = await metadata(); const [file, columns] = CONTRACT[key];
        const bytes = await request(file); const expected = sourceEntry(r, file);
        check(bytes.byteLength === expected.bytes, 'Saved source length mismatch: ' + file);
        check(cryptoObject && cryptoObject.subtle, 'Source verification unavailable');
        const hash = [...new Uint8Array(await cryptoObject.subtle.digest('SHA-256', bytes))].map(b => b.toString(16).padStart(2, '0')).join('');
        check(hash === expected.source_sha256, 'Saved source hash mismatch: ' + file);
        const text = new TextDecoder('utf-8', {fatal: true}).decode(bytes);
        return columns ? parseCSV(text, columns) : JSON.parse(text);
      })());
      return pending.get(key);
    }
    return {metadata, load};
  }
  function groupRows(rows, group) {
    const members = rows.filter(r => r.comparison_group === group);
    check(members.length > 0, 'Unknown comparison group');
    return members.slice().sort((a, b) => a.driver.localeCompare(b.driver));
  }
  function direction(row) {
    if (!numeric(row.combined_rating)) return 'Rating unavailable';
    if (!numeric(row.combined_ci_low) || !numeric(row.combined_ci_high)) return 'Direction uncertain: interval unavailable';
    const low = Number(row.combined_ci_low), high = Number(row.combined_ci_high);
    check(low <= high, 'Reversed saved interval');
    if (low <= 0 && high >= 0) return 'No clear gap';
    return high < 0 ? 'Faster' : 'Slower';
  }
  function validateRatings(rows, periods, summary, release) {
    check(rows.length === summary.drivers && rows.length === release.scope_counts.drivers, 'Driver scope differs');
    check(new Set(rows.map(r => r.driver)).size === rows.length, 'Duplicate driver');
    const groups = [...new Set(rows.map(r => r.comparison_group))].sort();
    check(JSON.stringify(groups) === JSON.stringify(release.groups.slice().sort()) && groups.length === summary.comparison_groups, 'Comparison groups differ');
    check(summary.method_version === release.rating_method_version, 'Rating method version differs');
    const keys = new Set();
    for (const p of periods) {
      const key = [p.driver, p.period, p.signal].join('|');
      check(!keys.has(key), 'Duplicate period signal'); keys.add(key);
    }
    const expected = new Set();
    for (const r of rows) {
      check(r.season === String(release.season) && r.method_version === release.rating_method_version, 'Rating identity differs');
      check(r.rating_units === 'log-percentage points', 'Unexpected rating units');
      direction(r);
      const notes = JSON.parse(r.notes);
      check(Array.isArray(notes.teammate_periods), 'Missing teammate periods');
      for (const period of notes.teammate_periods) for (const signal of SIGNALS) {
        const key = [r.driver, period.period, signal].join('|');
        expected.add(key);
        const p = periods.find(p => [p.driver, p.period, p.signal].join('|') === key);
        check(p, 'Missing saved period');
        for (const field of ['season', 'driver', 'team', 'teammate', 'round_start', 'round_end']) check(String(period[field]) === p[field], 'Period identity disagrees with notes');
        const s = period.signals[signal];
        check(Number(p.valid) === s.valid && Number(p.eligible) === s.eligible, 'Period evidence disagrees with notes');
        check(s.mean === null ? blank(p.rating) : numeric(p.rating) && Math.abs(Number(p.rating) - s.mean) <= 0.000500000001, 'Period rating disagrees at saved precision');
      }
    }
    check(keys.size === expected.size && [...keys].every(k => expected.has(k)), 'Unexpected period rows');
    for (const [field, labels] of [['confidence', summary.confidence_counts], ['rating_status', summary.rating_status_counts]])
      for (const [label, count] of Object.entries(labels)) check(rows.filter(r => r[field] === label).length === count, 'Saved label counts disagree');
  }
  function predictionRows(rows, target = 'main_both_finish', period = 'main') {
    check(TARGETS.includes(target) && PERIODS.includes(period), 'Unknown prediction scope');
    return rows.filter(r => r.target === target && r.period === period);
  }
  function primaryRows(rows, target = 'main_both_finish', period = 'main') {
    const selected = predictionRows(rows, target, period).filter(r => r.comparison === 'primary' && r.candidate === 'M3' && r.baseline === 'M2');
    check(selected.length === 3 && METRICS.every(m => selected.filter(r => r.metric === m).length === 1), 'Missing primary comparison');
    return METRICS.map(m => selected.find(r => r.metric === m));
  }
  function validatePrediction(metrics, comparisons, counts, config, summary, release) {
    check(config.specification === release.prediction_specification && config.rating.method_version === release.rating_method_version, 'Prediction version differs');
    check(config.season === release.season && config.rounds === release.rounds, 'Prediction season differs');
    check(summary.config_sha256 === sourceEntry(release, 'prediction_test_config.json').source_sha256, 'Prediction config fingerprint differs');
    for (const [source, hash] of Object.entries(summary.source_sha256)) {
      if (release.source_sha256[source]) check(hash === release.source_sha256[source], 'Prediction input fingerprint differs');
    }
    const count = counts.find(r => r.target === 'main_both_finish');
    check(count && Number(count.main_rows) === release.scope_counts.main_pair_races && Number(count.main_weekends) === release.scope_counts.main_weekends && Number(count.main_exclusions) === release.scope_counts.main_exclusions, 'Main sample differs');
    for (const target of TARGETS) for (const period of PERIODS) {
      const selected = predictionRows(metrics, target, period);
      check(selected.length === 8 && new Set(selected.map(r => r.method)).size === 8, 'Missing method scores');
      const primary = primaryRows(comparisons, target, period);
      for (const r of selected) {
        check(r.pair_count === selected[0].pair_count && r.weekend_count === selected[0].weekend_count && r.excluded_pair_count === selected[0].excluded_pair_count, 'Methods use different samples');
        for (const m of METRICS) check([r[m], r[m + '_ci_low'], r[m + '_ci_high']].every(numeric), 'Missing saved score interval');
      }
      for (const r of primary) check(r.pair_count === selected[0].pair_count && r.weekend_count === selected[0].weekend_count && [r.difference, r.ci_low, r.ci_high].every(numeric), 'Comparison sample or interval differs');
    }
    for (const r of predictionRows(metrics)) check(r.pair_count === count.main_rows && r.weekend_count === count.main_weekends && r.excluded_pair_count === count.main_exclusions, 'Main metrics/counts disagree');
  }
  root.DashboardData = {BASE, CONTRACT, DOWNLOADS, SIGNALS, METRICS, TARGETS, PERIODS, check, blank, numeric, parseCSV, fileURL, sourceEntry, validateMetadata, createLoader, groupRows, direction, validateRatings, predictionRows, primaryRows, validatePrediction};
  if (typeof module !== 'undefined') module.exports = root.DashboardData;
})(globalThis);
