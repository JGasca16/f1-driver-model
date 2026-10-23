"""Offline, expanding-window teammate prediction test with frozen settings."""
import argparse
from dataclasses import dataclass
import hashlib
import io
import json
from pathlib import Path
import pickle
import re
import sqlite3
import time

import numpy as np
import pandas as pd
from scipy.optimize import minimize

import driver_rating as rating
import qualifying_gaps_combined as qualifying

ROOT = Path(__file__).resolve().parent
IDENTITY = ['round_number', 'race', 'team', 'driver', 'teammate']
# Read only named columns. Points and race-win totals never enter a table.
INPUT_COLUMNS = {
    'qualifying_rounds': IDENTITY + ['q1_gap', 'q2_gap', 'q3_gap'],
    'qualifying': IDENTITY + ['combined_gap', 'reason_code'],
    'dry': IDENTITY + ['final_gap', 'final_se_pp', 'reason_code'],
    'wet': IDENTITY + ['wet_gap_2pct', 'wet_gap_se_pp_2pct', 'reason_code'],
}
RESULT_COLUMNS = ['Abbreviation', 'TeamName', 'GridPosition', 'Position']
METRICS = ['brier', 'accuracy', 'log_loss']


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def path_for(config, section, name, root=ROOT):
    return Path(root) / config[section][name].format(season=config['season'])


def load_config(path=ROOT/'prediction_test_config.json'):
    config = json.loads(Path(path).read_text())
    if config['logistic']['intercept'] or config['network'] or config['overwrite']:
        raise ValueError('This test requires no intercept, no network and no overwrite.')
    if config['schedule']['initial_training_first'] != config['history']['calendar_rounds'] + 1:
        raise ValueError('Training must start at the first allowed feature round.')
    # The imported method has fixed constants. Stop if a config requests a different method.
    expected = config['rating']
    if expected['method_version'] != rating.METHOD_VERSION or expected['round_weights'] != qualifying.ROUND_WEIGHTS:
        raise ValueError('Config differs from the approved imported rating method.')
    for se in (np.nan, 0., .15, .3, 1.):
        configured = max(expected['precision_floor'], 1/(1+(se/expected['precision_se_scale'])**2)) if np.isfinite(se) else expected['precision_floor']
        if rating.observation_weight('dry', se, 'Other Grand Prix') != configured:
            raise ValueError('Config precision weights differ from the imported method.')
    return config


def load_inputs(config, root=ROOT):
    tables = {}
    for name, columns in INPUT_COLUMNS.items():
        tables[name] = pd.read_csv(path_for(config, 'inputs', name, root), usecols=columns,
                                  dtype=str, keep_default_na=False)
        tables[name]['round_number'] = tables[name].round_number.astype(int)
    q = tables['qualifying']
    if q.duplicated(['round_number','driver']).any():
        raise ValueError('Repeated qualifying driver-round.')
    if set(q.round_number) != set(range(1, config['rounds']+1)):
        raise ValueError('Incomplete season roster.')
    for _, group in q.groupby(['round_number','team']):
        if len(group) != 2 or set(group.driver) != set(group.teammate):
            raise ValueError('Incomplete teammate pair.')
    results = []
    pattern = config['inputs']['results_glob'].format(season=config['season'])
    for path in sorted(Path(root).glob(pattern)):
        number = int(path.name.split('_')[1])
        frame = pd.read_csv(path, usecols=RESULT_COLUMNS)
        frame['round_number'] = number
        frame['result_source'] = str(path.relative_to(root))
        results.append(frame)
    result = pd.concat(results, ignore_index=True)
    if set(result.round_number) != set(range(1, config['rounds']+1)):
        raise ValueError('Missing race-result file.')
    if result.duplicated(['round_number','Abbreviation']).any():
        raise ValueError('Repeated result driver-round.')
    return tables, result


def read_status_cache(config, results, root=ROOT):
    """Open SQLite without permission to update it, including journal sidecars."""
    cache = path_for(config, 'inputs', 'cache', root)
    uri = cache.resolve().as_uri() + '?mode=ro&immutable=1'
    pattern = re.compile(r'https://api\.jolpi\.ca/ergast/f1/' + str(config['season']) + r'/(\d+)/results\.json')
    rows = []
    with sqlite3.connect(uri, uri=True) as connection:
        for (blob,) in connection.execute('SELECT value FROM responses'):
            # This is the project's existing requests-cache dictionary format.
            response = pickle.loads(blob)
            match = pattern.fullmatch(response.get('url', ''))
            if not match:
                continue
            payload = json.loads(response['_content'])
            for race in payload['MRData']['RaceTable']['Races']:
                for entry in race['Results']:
                    rows.append({'round_number':int(match[1]), 'driver':entry['Driver']['code'],
                                 'status':entry['status'], 'cached_position':int(entry['position']),
                                 'source_url':response['url'], 'source_note':'Existing FastF1 HTTP cache; read-only immutable; no refresh'})
    status = pd.DataFrame(rows)
    if status.duplicated(['round_number','driver']).any():
        raise ValueError('Ambiguous cached status records.')
    allowed = set(config['finisher_statuses'] + config['excluded_statuses'] + [config['retired_status']])
    if set(status.status) - allowed:
        raise ValueError('Unrecognised finishing status.')
    merged = status.merge(results.rename(columns={'Abbreviation':'driver'}), on=['round_number','driver'],
                          how='outer', validate='one_to_one', indicator=True)
    if not merged['_merge'].eq('both').all():
        raise ValueError('Cache and result CSV rosters differ.')
    merged['position_matches_csv'] = merged.cached_position.eq(merged.Position)
    if not merged.position_matches_csv.all():
        raise ValueError('A cached position does not match its race CSV.')
    return merged[['round_number','driver','status','cached_position','Position',
                   'position_matches_csv','result_source','source_url','source_note']].sort_values(['round_number','driver']).reset_index(drop=True)


def settings(config):
    r = config['rating']
    return rating.Settings(tuple(r['signal_weights']), tuple(r['reference_races']), r['monaco_multiplier'])


def rebuild_prior(tables, before_round, config):
    """Slice FIRST, then use existing calculation functions on that history only."""
    history = {name: frame.loc[frame.round_number < before_round].copy() for name, frame in tables.items()}
    source, stored = history['qualifying_rounds'], history['qualifying']
    if source.empty:
        return pd.DataFrame()
    rebuilt = qualifying.combine_table(source)
    indexed = stored.set_index(['round_number','driver'])
    for row in rebuilt.itertuples():
        saved = indexed.loc[(row.round_number,row.driver)]
        if row.reason_code != saved.reason_code:
            raise ValueError('Stored and recombined qualifying reasons differ.')
        if not row.reason_code and abs(row.combined_gap-float(saved.combined_gap)) > config['rating']['qualifying_export_tolerance']:
            raise ValueError('Stored qualifying differs from log-round combination.')
    records = []
    for row in rebuilt.itertuples():
        records.append(dict(signal='qualifying', round_number=row.round_number, race=row.race,
                            driver=row.driver, teammate=row.teammate, contribution=row.combined_gap,
                            se_log=np.nan, reason_code=row.reason_code, warnings=''))
    for signal, gapcol, secol in [('dry','final_gap','final_se_pp'), ('wet','wet_gap_2pct','wet_gap_se_pp_2pct')]:
        for row in history[signal].to_dict('records'):
            a, b, se = rating.log_pair(row[gapcol], row[secol])
            for driver, teammate, value in [(row['driver'],row['teammate'],a),(row['teammate'],row['driver'],b)]:
                if (row['round_number'],driver) not in indexed.index or indexed.loc[(row['round_number'],driver),'teammate'] != teammate:
                    raise ValueError('Historical race-pace teammate mismatch.')
                records.append(dict(signal=signal, round_number=row['round_number'], race=row['race'],
                                    driver=driver, teammate=teammate, contribution=value, se_log=se,
                                    reason_code=row['reason_code'], warnings=''))
    observations = rating.add_weights(pd.DataFrame(records), settings(config))
    drivers = sorted(source.driver.unique())
    scores, components, effective, weights = rating.season_arrays(observations, drivers, settings(config))
    rows = []
    for index, driver in enumerate(drivers):
        record = {'feature_round':before_round, 'driver':driver, 'combined_rating':scores[0,index],
                  'source_max_round':int(observations.round_number.max()),
                  'appearances':int(source.driver.eq(driver).sum())}
        summaries = {}
        for si, signal in enumerate(rating.SIGNALS):
            summary = rating.summarize_signal(observations[(observations.driver==driver)&(observations.signal==signal)])
            summaries[signal] = summary
            for column in ['valid','eligible','coverage','effective_races']:
                record[f'{signal}_{column}'] = summary[column]
            record[f'{signal}_rating'] = components[0,index,si]
            record[f'{signal}_weight'] = weights[0,index,si]
        q, d = summaries['qualifying'], summaries['dry']
        record['rating_status'] = rating.rating_status(q['rating'], d['rating'], q['effective_races'], d['effective_races'], q['coverage'], d['coverage'])
        rows.append(record)
    return pd.DataFrame(rows)


def validate_full_slice(tables, config, root=ROOT):
    rebuilt = rebuild_prior(tables, config['rounds']+1, config)
    # This is the only score read from the full-season file; it is validation only.
    saved = pd.read_csv(path_for(config,'inputs','ratings',root), usecols=['driver','combined_rating','method_version'])
    if not saved.method_version.eq(config['rating']['method_version']).all():
        raise ValueError('Unexpected full-season rating version.')
    comparison = rebuilt[['driver','combined_rating']].merge(saved, on='driver', suffixes=('_rebuilt','_saved'), how='outer', validate='one_to_one')
    comparison['absolute_difference'] = abs(comparison.combined_rating_rebuilt-comparison.combined_rating_saved)
    if comparison.absolute_difference.isna().any() or (comparison.absolute_difference>config['rating']['full_slice_tolerance']).any():
        raise ValueError('STOP: full-slice rating does not reproduce the saved three-decimal table.')
    return comparison


def target_reason(row, target, config):
    """One primary exclusion reason, with lapped drivers counted as finishers."""
    if not row['result_present']:
        return 'missing_result'
    statuses = [row['status_a'],row['status_b']]
    if 'Disqualified' in statuses:
        return 'disqualified'
    if 'Did not start' in statuses:
        return 'did_not_start'
    if not row['valid_positions']:
        return 'invalid_position'
    finished = sum(s in config['finisher_statuses'] for s in statuses)
    rule = config['target_rules'][target]
    if rule == 'both_finish' and finished != 2:
        return 'one_or_both_retired'
    if rule == 'at_least_one_finisher' and finished == 0:
        return 'double_retirement'
    return ''


def build_pairs(tables, results, status, config):
    q = tables['qualifying']
    result = results.set_index(['round_number','Abbreviation'])
    statuses = status.set_index(['round_number','driver'])
    rows = []
    for (number,team), group in q.groupby(['round_number','team'], sort=True):
        group = group.sort_values('driver')
        first, second = list(group.itertuples())
        a,b = first.driver, second.driver
        present = (number,a) in result.index and (number,b) in result.index
        pa = float(result.loc[(number,a),'Position']) if (number,a) in result.index else np.nan
        pb = float(result.loc[(number,b),'Position']) if (number,b) in result.index else np.nan
        ga = float(result.loc[(number,a),'GridPosition']) if (number,a) in result.index else np.nan
        gb = float(result.loc[(number,b),'GridPosition']) if (number,b) in result.index else np.nan
        grids = results.loc[results.round_number.eq(number),'GridPosition']
        grid_valid = all(np.isfinite(x) and x>0 and grids.eq(x).sum()==1 for x in (ga,gb)) and ga!=gb
        validq = not first.reason_code and not second.reason_code
        gap = float(first.combined_gap) if validq else np.nan
        if validq and (not np.isfinite(gap) or gap != -float(second.combined_gap)):
            raise ValueError('Current qualifying values must be symmetric finite log gaps.')
        row = dict(round_number=number, race=first.race, team=team, driver_a=a, driver_b=b,
                   pair_id=f'{number:02}_{a}_{b}', result_present=present,
                   valid_positions=bool(np.isfinite(pa) and np.isfinite(pb) and pa>0 and pb>0 and pa!=pb),
                   status_a=statuses.loc[(number,a),'status'] if (number,a) in statuses.index else '',
                   status_b=statuses.loc[(number,b),'status'] if (number,b) in statuses.index else '',
                   position_a=pa, position_b=pb, outcome=float(pa<pb) if present else np.nan,
                   valid_qualifying=validq, qualifying_advantage=-gap, grid_valid=grid_valid,
                   grid_flag='' if grid_valid else 'ambiguous_or_nonpositive_grid',
                   grid_pick=float(ga<gb) if grid_valid else np.nan)
        row['main_history_usable'] = not target_reason(row,'main_both_finish',config) and validq
        rows.append(row)
    pairs = pd.DataFrame(rows).sort_values(['round_number','driver_a','driver_b']).reset_index(drop=True)
    # Previous-result and head-to-head histories stop at the current weekend.
    for index,row in pairs.iterrows():
        past = pairs[pairs.round_number<row.round_number]
        exact = past[(past.driver_a==row.driver_a)&(past.driver_b==row.driver_b)]
        # A teammate change starts a fresh period; do not bridge a later reunion.
        roster_history = q[(q.driver==row.driver_a)&(q.round_number<row.round_number)]
        changed = roster_history[(roster_history.teammate!=row.driver_b)|(roster_history.team!=row.team)]
        period_after = int(changed.round_number.max()) if len(changed) else 0
        usable = exact[exact.main_history_usable & (exact.round_number>period_after)]
        previous = usable[usable.round_number==row.round_number-1]
        pairs.loc[index,'previous_pick'] = float(previous.iloc[0].outcome) if len(previous)==1 else np.nan
        pairs.loc[index,'head_to_head_probability'] = smooth_probability(usable.outcome.sum(),len(usable),config)
        pairs.loc[index,'head_to_head_comparisons'] = len(usable)
        pairs.loc[index,'qualifying_pick'] = float(row.qualifying_advantage>0) if row.valid_qualifying and row.qualifying_advantage!=0 else np.nan
    return pairs


def smooth_probability(successes, attempts, config):
    b = config['baselines']
    return float((successes+b['pseudo_success'])/(attempts+b['pseudo_success']+b['pseudo_failure']))


def build_feature_table(tables, pairs, config):
    all_priors, frames = [], []
    for number in range(config['schedule']['initial_training_first'],config['rounds']+1):
        prior = rebuild_prior(tables,number,config)
        all_priors.append(prior)
        indexed = prior.set_index('driver')
        current = pairs[pairs.round_number==number].copy()
        for side in ['a','b']:
            current[f'prior_rating_{side}'] = current[f'driver_{side}'].map(indexed.combined_rating)
            current[f'prior_qualifying_{side}'] = current[f'driver_{side}'].map(indexed.qualifying_valid).fillna(0).astype(int)
            current[f'prior_status_{side}'] = current[f'driver_{side}'].map(indexed.rating_status).fillna('unavailable')
        current['rating_difference'] = current.prior_rating_b-current.prior_rating_a
        current['history_eligible'] = (current.prior_qualifying_a>=config['history']['valid_qualifying_per_driver']) & (current.prior_qualifying_b>=config['history']['valid_qualifying_per_driver']) & np.isfinite(current.rating_difference)
        current['feature_source_max_round'] = number-1
        frames.append(current)
    return pd.concat(frames,ignore_index=True), pd.concat(all_priors,ignore_index=True)


def make_eligibility(pairs, features, config):
    feature_map = features.set_index('pair_id')
    records = []
    for target in config['target_rules']:
        for row in pairs.to_dict('records'):
            reasons = []
            reason = target_reason(row,target,config)
            if reason: reasons.append(reason)
            if not row['valid_qualifying']: reasons.append('missing_current_qualifying')
            if row['round_number']<=config['history']['calendar_rounds']:
                reasons.append('calendar_history_gate')
            elif not feature_map.loc[row['pair_id'],'history_eligible']:
                reasons.append('driver_history_gate')
            records.append(dict(target=target,pair_id=row['pair_id'],round_number=row['round_number'],
                                driver_a=row['driver_a'],driver_b=row['driver_b'],eligible=not reasons,
                                reason_code=reasons[0] if reasons else '',all_reasons=';'.join(reasons)))
    return pd.DataFrame(records)


def symmetric_probability(features, coefficients):
    """Compute one positive-side sigmoid and its exact floating-point complement."""
    z = np.asarray(features,dtype=float) @ np.asarray(coefficients,dtype=float)
    positive = 1/(1+np.exp(-np.abs(z)))
    return np.where(z>=0,positive,1-positive)


@dataclass
class LogisticFit:
    coefficients: np.ndarray
    intercept: float = 0.0

    def predict(self, features):
        return symmetric_probability(features,self.coefficients)


def fit_logistic(features, outcomes, config):
    x,y = np.asarray(features,float),np.asarray(outcomes,float)
    c = config['logistic']['C']
    def objective(beta):
        z = x @ beta
        loss = np.sum(np.logaddexp(0,z)-y*z)+np.dot(beta,beta)/(2*c)
        gradient = x.T @ (symmetric_probability(x,beta)-y)+beta/c
        return loss,gradient
    options = {key:config['logistic'][key] for key in ['maxiter','gtol','ftol']}
    solution = minimize(objective,np.zeros(x.shape[1]),jac=True,method=config['logistic']['solver'],options=options)
    if not solution.success or not np.isfinite(solution.x).all():
        raise ValueError(f'Logistic fit failed: {solution.message}')
    return LogisticFit(solution.x)


def baseline_probability(method, train, current, config):
    if method=='chance':
        return np.full(len(current),config['baselines']['uninformed_probability'])
    if method=='head_to_head':
        return current.head_to_head_probability.to_numpy(float)
    column = {'qualifying':'qualifying_pick','grid':'grid_pick','previous':'previous_pick'}[method]
    valid = train[column].notna()
    successes = (train.loc[valid,column]==train.loc[valid,'outcome']).sum()
    accuracy = smooth_probability(successes,int(valid.sum()),config)
    pick = current[column].to_numpy(float)
    return np.where(np.isnan(pick),config['baselines']['uninformed_probability'],np.where(pick==1,accuracy,1-accuracy))


def count_samples(eligibility, config):
    rows=[]
    s=config['schedule']
    for target, group in eligibility.groupby('target',sort=False):
        eligible=group[group.eligible]
        initial=eligible[eligible.round_number.between(s['initial_training_first'],s['initial_training_last'])]
        main=eligible[eligible.round_number.between(s['main_first'],s['main_last'])]
        early_start=next((n for n in range(s['initial_training_first'],s['initial_training_last']+1) if (eligible.round_number<n).sum()>=s['minimum_training_rows']),None)
        early=initial[initial.round_number>=early_start] if early_start else initial.iloc[:0]
        fallback=initial[initial.round_number<early_start] if early_start else initial
        rows.append(dict(target=target,eligible_rows=len(eligible),initial_training_rows=len(initial),initial_training_weekends=initial.round_number.nunique(),
                         main_rows=len(main),main_weekends=main.round_number.nunique(),main_exclusions=int(group.round_number.between(s['main_first'],s['main_last']).sum()-len(main)),
                         early_first_round=early_start,early_rows=len(early),early_weekends=early.round_number.nunique(),early_fallback_rows=len(fallback)))
    return pd.DataFrame(rows)


def make_predictions(features, eligibility, config):
    predictions,coefficients=[],[]
    s=config['schedule']
    for target in config['target_rules']:
        ids=set(eligibility.loc[(eligibility.target==target)&eligibility.eligible,'pair_id'])
        eligible=features[features.pair_id.isin(ids)].copy()
        for number,current in eligible.groupby('round_number',sort=True):
            train=eligible[eligible.round_number<number]
            enough=len(train)>=s['minimum_training_rows']
            period='main' if number>=s['main_first'] else 'early' if enough else 'early_fallback'
            probabilities={m:baseline_probability(m,train,current,config) for m in config['baselines']['methods']}
            for model,columns in config['models'].items():
                fallback='too_few_earlier_training_rows' if not enough else ''
                beta=np.full(len(columns),np.nan)
                if enough:
                    try:
                        fitted=fit_logistic(train[columns],train.outcome,config)
                        beta=fitted.coefficients
                        probabilities[model]=fitted.predict(current[columns])
                    except ValueError as exc:
                        fallback=str(exc)
                if fallback: probabilities[model]=probabilities['qualifying'].copy()
                coefficients.append(dict(target=target,period=period,prediction_round=number,method=model,training_rows=len(train),
                                         training_max_round=int(train.round_number.max()) if len(train) else 0,
                                         rating_coefficient=float(beta[columns.index('rating_difference')]) if 'rating_difference' in columns else np.nan,
                                         qualifying_coefficient=float(beta[columns.index('qualifying_advantage')]) if 'qualifying_advantage' in columns else np.nan,
                                         intercept=0.,fallback_reason=fallback))
                for i,row in enumerate(current.to_dict('records')):
                    predictions.append({**row,'target':target,'period':period,'method':model,'probability':float(probabilities[model][i]),
                                        'training_rows':len(train),'training_max_round':int(train.round_number.max()) if len(train) else 0,'fallback_reason':fallback})
            for method in config['baselines']['methods']:
                for i,row in enumerate(current.to_dict('records')):
                    predictions.append({**row,'target':target,'period':period,'method':method,'probability':float(probabilities[method][i]),
                                        'training_rows':len(train),'training_max_round':int(train.round_number.max()) if len(train) else 0,'fallback_reason':''})
    return pd.DataFrame(predictions),pd.DataFrame(coefficients)


def metric_arrays(y,p,config):
    y,p=np.asarray(y,float),np.asarray(p,float)
    threshold=config['metrics']['decision_threshold']
    accuracy=np.where(p==threshold,config['metrics']['tie_credit'],(p>threshold)==y).astype(float)
    clipped=np.clip(p,*config['metrics']['log_loss_clip'])
    return {'brier':(p-y)**2,'accuracy':accuracy,'log_loss':-(y*np.log(clipped)+(1-y)*np.log1p(-clipped))}


def weekend_bootstrap(group, config):
    """Use identical weekend draws for every method; keep each weekend intact."""
    methods=sorted(group.method.unique())
    weekends=sorted(group.round_number.unique())
    first=group[group.method==methods[0]]
    ids=set(first.pair_id)
    if any(set(group.loc[group.method==m,'pair_id'])!=ids for m in methods):
        raise ValueError('Methods were not scored on identical pair-races.')
    rng=np.random.default_rng(config['bootstrap']['seed'])
    draws=rng.integers(0,len(weekends),size=(config['bootstrap']['resamples'],len(weekends)))
    multiplicities=np.array([np.bincount(row,minlength=len(weekends)) for row in draws])
    sizes=first.groupby('round_number').size().reindex(weekends).to_numpy()
    denominator=multiplicities @ sizes
    output={}
    for method in methods:
        frame=group[group.method==method]
        arrays=metric_arrays(frame.outcome,frame.probability,config)
        output[method]={}
        for metric,values in arrays.items():
            sums=pd.Series(values,index=frame.round_number).groupby(level=0).sum().reindex(weekends).to_numpy()
            output[method][metric]=multiplicities @ sums / denominator
    return output


def analyse(predictions,eligibility,group_map,config):
    metrics,bootrows,comparisons,stability,winners=[] ,[],[],[],[]
    for (target,period),group in predictions.groupby(['target','period'],sort=False):
        boot=weekend_bootstrap(group,config)
        observed={}
        rounds=set(group.round_number)
        scope=eligibility[(eligibility.target==target)&eligibility.round_number.isin(rounds)]
        excluded=scope[~scope.eligible]
        reasons=json.dumps(excluded.reason_code.value_counts().to_dict(),sort_keys=True)
        for method,frame in group.groupby('method',sort=False):
            values=metric_arrays(frame.outcome,frame.probability,config)
            observed[method]={k:float(v.mean()) for k,v in values.items()}
            metricrow=dict(target=target,period=period,method=method,pair_count=len(frame),weekend_count=frame.round_number.nunique(),
                           excluded_pair_count=len(excluded),exclusion_reasons=reasons,ties=int(frame.probability.eq(.5).sum()),fallback_rows=int(frame.fallback_reason.ne('').sum()))
            for metric,estimate in observed[method].items():
                lo,hi=np.percentile(boot[method][metric],config['bootstrap']['percentiles'])
                metricrow.update({metric:estimate,f'{metric}_ci_low':lo,f'{metric}_ci_high':hi})
            metrics.append(metricrow)
            for sample in range(config['bootstrap']['resamples']):
                bootrows.append(dict(target=target,period=period,draw=sample,method=method,**{m:boot[method][m][sample] for m in METRICS}))
        compare=[('M3','M2','primary')]+[(m,b,'simple_baseline') for m in config['comparisons']['against_simple_baselines'] for b in config['baselines']['methods']]
        for metric in METRICS:
            reverse=metric=='accuracy'
            ranked=sorted(config['baselines']['methods'],key=lambda m: (-observed[m][metric] if reverse else observed[m][metric],m))
            best=ranked[0]
            tied=[m for m in ranked if observed[m][metric]==observed[best][metric]]
            winners.append(dict(target=target,period=period,metric=metric,best_simple_baselines=';'.join(tied),value=observed[best][metric],exploratory=True))
            for candidate,baseline,kind in compare+[(m,best,'best_baseline_exploratory') for m in ['M1','M3']]:
                delta=boot[candidate][metric]-boot[baseline][metric]
                lo,hi=np.percentile(delta,config['bootstrap']['percentiles'])
                comparisons.append(dict(target=target,period=period,candidate=candidate,baseline=baseline,comparison=kind,metric=metric,
                                        difference=observed[candidate][metric]-observed[baseline][metric],ci_low=lo,ci_high=hi,
                                        pair_count=group[group.method==candidate].shape[0],weekend_count=len(rounds)))
        groups=sorted(set(group_map.values()))
        for omitted in groups:
            kept=group[~group.driver_a.map(group_map).eq(omitted)]
            row=dict(target=target,period=period,omitted_group=omitted,remaining_pairs=int(kept.method.eq('M3').sum()),remaining_weekends=kept.round_number.nunique())
            for method in ['M2','M3']:
                frame=kept[kept.method==method]
                for metric,values in metric_arrays(frame.outcome,frame.probability,config).items():
                    row[f'{method}_{metric}']=float(values.mean())
            for metric in METRICS: row[f'difference_{metric}']=row[f'M3_{metric}']-row[f'M2_{metric}']
            stability.append(row)
    return tuple(pd.DataFrame(rows) for rows in (metrics,bootrows,comparisons,stability,winners))


def write_csv(frame,path):
    with Path(path).open('x',newline='') as handle:
        frame.to_csv(handle,index=False,na_rep='',float_format='%.17g')


def new_run_folder(config,root=ROOT):
    base=path_for(config,'outputs','runs',root)
    base.mkdir(parents=True,exist_ok=True)
    number=1
    while True:
        path=base/f"{config['outputs']['run_prefix']}{number:03}"
        try:
            path.mkdir()
            return path
        except FileExistsError:
            number+=1


def run(config_path=ROOT/'prediction_test_config.json',root=ROOT):
    started=time.perf_counter()
    config=load_config(config_path)
    tables,results=load_inputs(config,root)
    validation=validate_full_slice(tables,config,root)
    print('Full-slice validation passed; maximum difference from rounded saved score:',validation.absolute_difference.max(),flush=True)
    status=read_status_cache(config,results,root)
    pairs=build_pairs(tables,results,status,config)
    features,priors=build_feature_table(tables,pairs,config)
    eligibility=make_eligibility(pairs,features,config)
    counts=count_samples(eligibility,config)
    print('COUNTS BEFORE METRICS\n'+counts.to_string(index=False),flush=True)
    predictions,coefficients=make_predictions(features,eligibility,config)
    # Full-season comparison groups are read only after all predictions are fixed.
    saved_groups=pd.read_csv(path_for(config,'inputs','ratings',root),usecols=['driver','comparison_group'])
    group_map=dict(zip(saved_groups.driver,saved_groups.comparison_group))
    metrics,bootstrap,comparisons,stability,winners=analyse(predictions,eligibility,group_map,config)
    folder=new_run_folder(config,root)
    status_path=path_for(config,'outputs','status',root)
    if status_path.exists():
        existing=pd.read_csv(status_path,dtype=str,keep_default_na=False)
        expected_csv = status.to_csv(index=False,na_rep='',float_format='%.17g')
        if not existing.equals(pd.read_csv(io.StringIO(expected_csv),dtype=str,keep_default_na=False)):
            raise ValueError('Existing status export differs; it has not been overwritten.')
    else:
        write_csv(status,status_path)
    outputs={'predictions':predictions,'metrics':metrics,'bootstrap':bootstrap,'comparisons':comparisons,
             'group_stability':stability,'baseline_winners':winners,'coefficients':coefficients,'counts':counts,
             'eligibility':eligibility,'excluded_pairs':eligibility[~eligibility.eligible],
             'missing_qualifying_pairs':pairs[~pairs.valid_qualifying], 'prior_ratings':priors,'features':features,
             'full_slice_validation':validation,'race_finish_status':status}
    for name,frame in outputs.items(): write_csv(frame,folder/f'{name}.csv')
    config_bytes=Path(config_path).read_bytes()
    with (folder/'prediction_test_config.json').open('xb') as handle: handle.write(config_bytes)
    config_hash=hashlib.sha256(config_bytes).hexdigest()
    (folder/'config.sha256').write_text(config_hash+'\n')
    sources=[path_for(config,'inputs',name,root) for name in INPUT_COLUMNS]+[path_for(config,'inputs','ratings',root),path_for(config,'inputs','cache',root)]
    sources += sorted(Path(root).glob(config['inputs']['results_glob'].format(season=config['season'])))
    summary={'config_sha256':config_hash,'runtime_seconds':time.perf_counter()-started,'counts':counts.to_dict('records'),
             'status_counts':status.status.value_counts().to_dict(),'position_matches':int(status.position_matches_csv.sum()),
             'full_slice_max_difference':validation.absolute_difference.max(),'source_sha256':{str(p.relative_to(root)):sha256(p) for p in sources},
             'script_sha256':sha256(__file__), 'rating_script_sha256':sha256(rating.__file__),
             'qualifying_script_sha256':sha256(qualifying.__file__), 'feature_correlation':{},
             'exclusion_counts':eligibility[~eligibility.eligible].groupby(['target','reason_code']).size().to_dict()}
    summary['exclusion_counts']={f'{target}/{reason}':int(count) for (target,reason),count in summary['exclusion_counts'].items()}
    for target in config['target_rules']:
        sample=predictions[(predictions.target==target)&(predictions.period=='main')&(predictions.method=='M3')]
        summary['feature_correlation'][target]=sample.rating_difference.corr(sample.qualifying_advantage)
    with (folder/'summary.json').open('x') as handle:json.dump(summary,handle,indent=2)
    for (target,period), group in metrics.groupby(['target','period'],sort=False):
        print(f'\n{target} / {period}\n'+group[['method','pair_count','weekend_count','brier','accuracy','log_loss','ties']].to_string(index=False))
    print('\nPRIMARY DIFFERENCES (candidate minus baseline)\n'+comparisons[comparisons.comparison=='primary'].to_string(index=False))
    print(f'\nSaved {folder}; runtime {summary["runtime_seconds"]:.2f}s')
    return folder


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,default=ROOT/'prediction_test_config.json')
    args=parser.parse_args()
    run(args.config)
