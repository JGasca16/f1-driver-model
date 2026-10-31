/* Read saved values, then format them for the four views. */
(function (root) {
  'use strict';
  const D=root.DashboardData, C=root.DashboardCopy, X=root.DashboardExact;
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const plain=s=>s.replace(/\*\*|`/g,'');
  const METHODS={M1:'Earlier ratings (M1)',M2:'Qualifying only (M2)',M3:'Qualifying plus ratings (M3)',qualifying:'Qualifying pick',grid:'Grid pick',previous:'Previous race',head_to_head:'Head-to-head record',chance:'Chance'};
  const SIGNALS={qualifying:'Qualifying',dry:'Dry race',wet:'Wet race'};
  const MEASURES={brier:'Brier score (lower is better)',accuracy:'Accuracy (higher is better)',log_loss:'Log loss (lower is better)'};
  const TITLES={'DASHBOARD_SPEC.md':'Dashboard specification','README.md':'Project overview','DRIVER_RATING_METHOD.md':'Driver rating method','METHOD_DRY_RACEPACE.md':'Dry race method','METHOD_WET_RACEPACE.md':'Wet race method','PREDICTION_TEST_METHOD.md':'Prediction test method'};
  // These scope counts are recorded in the dry and wet Known limitations sections.
  const COVERAGE={dry_pairs:200,dry_blank:32,wet_gap:6,wet_eligible:30,wet_high:1};
  const TARGET_LABELS={main_both_finish:'Both finished',all_starters:'All starters',no_double_retirement:'Exclude double retirements'};
  const PERIOD_LABELS={main:'Main period',early:'Early season',early_fallback:'Early fallback'};
  const REASONS={one_or_both_retired:'One or both retired',missing_current_qualifying:'No usable qualifying gap',did_not_start:'Did not start',disqualified:'Disqualified'};
  function fill(key,values={}) {
    D.check(C[key],'Unknown copy block');
    return C[key][2].replace(/\{(\w+)\}/g,(_,name)=>{D.check(Object.hasOwn(values,name),'Missing copy value: '+name);return String(values[name]);});
  }
  function copy(key,r,classes='',values={}) {return `<p class="copy ${classes}" data-copy="${key}">${esc(fill(key,values))}</p>`;}
  function link(url,label,extra=''){return `<a href="${esc(url)}" ${extra}>${esc(label)}</a>`;}
  function route(view,values={}){return '#'+view+(Object.keys(values).length?'?'+new URLSearchParams(values).toString():'');}
  function number(value,signed=false){return D.blank(value)?'No data':esc((signed&&Number(value)>0?'+':'')+String(value)).replace(/^-/,'−');}
  function interval(low,high){return D.numeric(low)&&D.numeric(high)?`${number(low,true)} to ${number(high,true)}`:'No data';}
  function badge(v){return `<span class="badge">${esc(v)}</span>`;}
  function table(headers,rows,caption,attributes=''){
    return `<div class="table-scroll" role="region" tabindex="0" aria-label="${esc(caption)}"><table ${attributes}><caption>${esc(caption)}</caption><thead><tr>${headers.map(h=>`<th scope="col">${esc(h)}</th>`).join('')}</tr></thead><tbody>${rows.join('')}</tbody></table></div>`;
  }
  function row(cells){return `<tr>${cells.map((cell,i)=>i===0?`<th scope="row">${cell}</th>`:`<td>${cell}</td>`).join('')}</tr>`;}
  function sources(keys){return `<p class="data-line">Data: ${keys.map(key=>`<button class="source-link" data-source="${key}">${esc(D.CONTRACT[key][0])}</button>`).join(' · ')}</p>`;}
  function origins(keys,r,exact=false){
    const records=exact?X:C;
    return `<details class="copy-origins"><summary>Where this text comes from</summary><ul>${keys.map(key=>{
      const [file,section]=records[key];
      // The specification is still local. Do not send readers to an unpublished file.
      const url=r.method_links[file]||(file==='README.md'?r.repository_url+'/blob/main/README.md':null);
      const label=TITLES[file]||'Method document';
      return `<li data-origin="${key}">${url?link(url,label):esc(label)} · ${esc(section)}</li>`;
    }).join('')}</ul></details>`;
  }
  function end(keys,blocks,r){return sources(keys)+origins(blocks,r);}
  function sign(r){return copy('sign',r,'sign-caption');}
  function exactRules(keys,r,title='Exact rules'){
    return `<details class="exact-rules"><summary>${title}</summary>${exactValues(keys.map(k=>`<p data-exact-copy="${k}">${esc(plain(X[k][2]))}</p>`).join(''))}${origins(keys,r,true)}</details>`;
  }
  function exactValues(html){return `<details class="exact-values"><summary>Exact values</summary>${html}</details>`;}
  function largeGroup(group){return group.split('+').length>2;}
  function directionState(r){const d=D.direction(r);return d==='Faster'?'faster':d==='Slower'?'slower':'neutral';}
  function directionText(r){
    const label=D.direction(r);
    if(label==='No clear gap')return label;
    if(label==='Rating unavailable')return 'No data';
    if(!['Faster','Slower'].includes(label))return 'Direction unclear';
    const other=largeGroup(r.comparison_group)?'teammates':r.teammates;
    return `${label} than ${other} by about ${Math.abs(Number(r.combined_rating)).toFixed(2)}%`;
  }
  function direction(r){const state=directionState(r);return `<span class="result ${state}"><span aria-hidden="true">${state==='faster'?'↑':state==='slower'?'↓':'●'}</span> <span class="direction">${esc(directionText(r))}</span></span>`;}
  function intervalChart(rows,group,r){
    D.check(rows.every(v=>v.comparison_group===group),'Chart cannot span groups');
    const values=rows.flatMap(v=>[v.combined_rating,v.combined_ci_low,v.combined_ci_high]).filter(D.numeric).map(Number);
    const span=Math.max(.05,...values.map(Math.abs))*1.15;
    const x=v=>330+Number(v)/span*190;
    const h=100+rows.length*54;
    return `<figure class="interval-chart" data-group="${esc(group)}"><svg viewBox="0 0 560 ${h}" role="img" aria-label="${esc(group)} ratings and 95% ranges">
      <text x="20" y="16" class="axis-word">faster than teammate</text><text x="520" y="16" text-anchor="end" class="axis-word">slower</text>
      <line class="axis" x1="140" x2="520" y1="30" y2="30"/>
      ${[-1,-.5,0,.5,1].map(v=>`<line class="tick" x1="${330+v*190}" x2="${330+v*190}" y1="25" y2="35"/>`).join('')}
      <line class="zero" x1="330" x2="330" y1="30" y2="${h-31}"/>
      ${rows.map((v,i)=>{const y=63+i*54,state=directionState(v);return `<g class="${state}"><text x="8" y="${y+5}" class="driver-code">${esc(v.driver)}</text>
        ${D.numeric(v.combined_ci_low)&&D.numeric(v.combined_ci_high)?`<line class="interval-line" x1="${x(v.combined_ci_low)}" x2="${x(v.combined_ci_high)}" y1="${y}" y2="${y}"/><line class="cap" x1="${x(v.combined_ci_low)}" x2="${x(v.combined_ci_low)}" y1="${y-7}" y2="${y+7}"/><line class="cap" x1="${x(v.combined_ci_high)}" x2="${x(v.combined_ci_high)}" y1="${y-7}" y2="${y+7}"/>`:''}
        ${D.numeric(v.combined_rating)?`<circle class="estimate" cx="${x(v.combined_rating)}" cy="${y}" r="6"/>`:''}</g>`;}).join('')}
      <text x="330" y="${h-10}" text-anchor="middle" class="axis-word">0 = same as teammate</text></svg></figure>`;
  }
  function groupTable(all,group,r,compact=false,showSign=true){
    const members=D.groupRows(all,group);
    return `${showSign?sign(r):''}${table(['Driver',...(compact?[]:['Qualifying','Dry race','Wet race']),compact?'Rating':'Combined','95% range','Result','Status','Confidence'],members.map(v=>row([
      link(route('drivers',{group,driver:v.driver}),v.driver),
      ...(compact?[]:['qualifying_rating','dry_rating','wet_rating'].map(k=>`<span data-field="${k}" data-driver="${esc(v.driver)}">${number(v[k],true)}</span>`)),
      `<strong data-field="combined_rating" data-driver="${esc(v.driver)}">${number(v.combined_rating,true)}</strong>`,
      `<span data-field="combined_ci_low">${interval(v.combined_ci_low,v.combined_ci_high)}</span>`,direction(v),badge(v.rating_status),badge(v.confidence)
     ])),group+' · Saved values',`data-rating-table="true" data-group="${esc(group)}"`)}`;
  }
  function formattedMetric(v,metric,diff=false){if(!D.numeric(v))return 'No data';const n=Number(v)*(metric==='accuracy'?100:1);return (diff&&n>0?'+':'')+n.toFixed(metric==='accuracy'?(diff?2:1):4).replace(/^-/,'−');}
  function metricCell(v,lo,hi,metric,diff=false){const unit=metric==='accuracy'?(diff?' pp':'%'):'';return `<span class="metric-value">${formattedMetric(v,metric,diff)}${unit}</span><span class="ci">[${formattedMetric(lo,metric,diff)}, ${formattedMetric(hi,metric,diff)}]${unit}</span>`;}
  function countValues(m,target='main_both_finish',period='main'){
    const r=D.predictionRows(m.metrics,target,period)[0];return {pairs:r.pair_count,weekends:r.weekend_count,excluded:r.excluded_pair_count};
  }
  function overview(m){
    const r=m.release,b=D.primaryRows(m.comparisons).find(v=>v.metric==='brier');
    return `<section class="hero"><div class="overview-lead"><div><h1>Teammates in the same car: who was faster in 2025?</h1>${copy('intro',r,'lede')}${copy('scope',r,'scope-line')}
      <p class="actions">${link('#drivers','See the ratings','class="button primary"')}${link('#prediction','See the prediction test','class="button"')}${link('#method','How it works','class="text-button"')}</p>
      <div class="scope-stats"><span><strong>${m.ratingSummary.drivers}</strong> drivers</span><span><strong>${m.ratingSummary.comparison_groups}</strong> teammate groups</span><span><strong>${r.rounds}</strong> races</span></div></div>
      <aside class="headline-metric"><div class="eyebrow">Prediction test</div><h2>Inconclusive, but leaning positive</h2>${copy('prediction',r)}<h3>Change in prediction error (Brier score)</h3>${metricCell(b.difference,b.ci_low,b.ci_high,'brier',true)}${copy('lower',r)}${copy('counts',r,'sample',countValues(m))}${copy('condition',r)}${link('#prediction','See the full test','class="text-button"')}</aside></div>
      ${end(['ratingSummary','comparisons','counts'],['intro','scope','prediction','lower','counts','condition'],r)}</section>
      <section><div class="section-heading"><h2>Two examples</h2>${copy('examples',r)}</div><div class="examples">${r.teaching_examples.examples.map(e=>`<article class="example rating-block" data-group="${e.group}"><span class="badge ${e.state==='clear_gap'?'faster':'neutral'}">${e.state==='clear_gap'?'Clear gap':'No clear gap'}</span><h3>${e.group}</h3>${intervalChart(D.groupRows(m.ratings,e.group),e.group,r)}${copy('exampleCaption',r,'sign-caption')}${groupTable(m.ratings,e.group,r,true,false)}${link(route('drivers',{group:e.group}),'Open this group','class="text-button"')}</article>`).join('')}</div>
      ${end(['ratings'],['examples','exampleCaption'],r)}</section>`;
  }
  function select(id,label,options,value){return `<label for="${id}">${esc(label)}</label><select id="${id}">${options.map(v=>`<option value="${esc(v.value??v)}" ${(v.value??v)===value?'selected':''}>${esc(v.label??v)}</option>`).join('')}</select>`;}
  function drivers(m,wantedGroup,wantedDriver){
    const r=m.release,groups=r.groups.slice().sort(),group=groups.includes(wantedGroup)?wantedGroup:groups[0];
    const members=D.groupRows(m.ratings,group),driver=members.find(v=>v.driver===wantedDriver)||members[0];
    return `<section><h1>Drivers</h1>${copy('driverIntro',r,'lede')}<div class="controls">${select('group-select','Teammate group',groups,group)}${select('driver-select','Driver',members.map(v=>v.driver),driver.driver)}</div><div class="rating-block"><h2>${esc(group)}</h2>${largeGroup(group)?copy('caution',r,'notice'):''}${intervalChart(members,group,r)}${sign(r)}${copy('confidenceHelp',r,'help')}${groupTable(m.ratings,group,r,false,false)}</div>${end(['ratings'],['driverIntro','caution','sign','confidenceHelp'],r)}</section>${driverDetail(m,driver)}`;
  }
  function driverDetail(m,v){
    const r=m.release,notes=JSON.parse(v.notes),periods=m.periods.filter(p=>p.driver===v.driver),diagnostics=m.diagnostics.filter(p=>p.driver===v.driver);
    D.check(diagnostics.length===3,'Missing driver diagnostics');
    return `<section class="driver-detail"><h2>${esc(v.driver)} in detail</h2><p class="subline">${esc(v.teams)} · ${badge(v.rating_status)} · ${badge(v.confidence)} confidence</p>${copy('combined',r,'combined-line',{combined:plainNumber(v.combined_rating,true),lo:plainNumber(v.combined_ci_low,true),hi:plainNumber(v.combined_ci_high,true)})}${D.direction(v)==='No clear gap'?copy('noClear',r):''}${v.driver==='DOO'?copy('provisional',r,'notice',{valid:v.dry_valid,eligible:v.dry_eligible}):''}${copy('missing',r)}${copy('coverage',r)}
      <div class="rating-block">${sign(r)}${table(['Signal','Rating','Weight used','Usable / eligible races','Missing','Coverage','Effective races'],D.SIGNALS.map(s=>{const d=diagnostics.find(d=>d.signal===s);return row([SIGNALS[s],number(v[s+'_rating'],true),number(v[s+'_weight']),`${v[s+'_valid']} / ${v[s+'_eligible']}`,esc(d.missing),number(d.coverage),number(v[s+'_effective_races'])]);}),v.driver+' · components','data-component-table="true"')}</div>
      ${exactValues(table(['Signal','season_ci_low','season_ci_high','single_race_ci_low','single_race_ci_high','single_race_round','season_ci_reason','missing_reasons','warnings'],diagnostics.map(d=>row([esc(d.signal),...['season_ci_low','season_ci_high','single_race_ci_low','single_race_ci_high','single_race_round','season_ci_reason','missing_reasons','warnings'].map(k=>esc(d[k]||'No data'))])), 'Saved component details')+`<pre>${esc(JSON.stringify(notes,null,2))}</pre>`)}
      <h3>Who they raced against</h3>${copy('periods',r)}${largeGroup(v.comparison_group)?copy('caution',r,'notice'):''}
      <div class="periods">${notes.teammate_periods.map(p=>`<article class="period rating-block"><h4>${esc(p.driver)} / ${esc(p.teammate)}</h4><p class="subline">${esc(p.team)} · Rounds ${p.round_start} to ${p.round_end}</p>${sign(r)}${table(['Signal','Rating','Usable / eligible races','Coverage','Missing','Effective races'],D.SIGNALS.map(s=>{const d=periods.find(d=>Number(d.period)===p.period&&d.signal===s);return row([SIGNALS[s],number(d.rating,true),`${d.valid} / ${d.eligible}`,number(d.coverage),number(d.missing),number(d.effective_races)]);}),p.driver+' / '+p.teammate,'data-period-table="true"')}</article>`).join('')}</div>
      ${end(['ratings','periods','diagnostics'],['combined','noClear','provisional','missing','coverage','periods','sign'],r)}</section>`;
  }
  function plainNumber(v,signed=false){return D.blank(v)?'No data':((signed&&Number(v)>0?'+':'')+String(v)).replace(/^-/,'−');}
  function scoreTables(m,target,period){
    const scores=D.predictionRows(m.metrics,target,period),pairs=D.primaryRows(m.comparisons,target,period),one=id=>scores.find(v=>v.method===id);
    return `<section data-prediction-scope="${esc(target+'/'+period)}">${copy('counts',m.release,'sample',countValues(m,target,period))}${table(['Measure','Qualifying only (M2)','Qualifying plus ratings (M3)','Difference'],pairs.map(c=>row([MEASURES[c.metric],...['M2','M3'].map(id=>{const v=one(id);return metricCell(v[c.metric],v[c.metric+'_ci_low'],v[c.metric+'_ci_high'],c.metric);}),metricCell(c.difference,c.ci_low,c.ci_high,c.metric,true)])),TARGET_LABELS[target]+' · '+PERIOD_LABELS[period],'data-primary-table="true"')}
      <details><summary>All models and baselines</summary>${table(['Model','Brier score','Accuracy','Log loss'],Object.keys(METHODS).map(id=>{const v=one(id);return row([METHODS[id],...D.METRICS.map(k=>metricCell(v[k],v[k+'_ci_low'],v[k+'_ci_high'],k))]);}), 'Saved scores and 95% ranges','data-baseline-table="true"')}${exactRules(['qualifyingPick','baseline'],m.release)}</details>
      ${exactValues(table(['Method','Metric','Stored value','Stored interval low','Stored interval high'],scores.flatMap(v=>D.METRICS.map(k=>row([esc(v.method),esc(k),esc(v[k]),esc(v[k+'_ci_low']),esc(v[k+'_ci_high'])]))),'Saved scores')+table(['Comparison','Metric','Stored difference','Stored interval low','Stored interval high'],pairs.map(v=>row(['M3 minus M2',esc(v.metric),esc(v.difference),esc(v.ci_low),esc(v.ci_high)])),'Saved differences'))}</section>`;
  }
  function prediction(m){
    const r=m.release,scores=D.predictionRows(m.metrics),m2=scores.find(v=>v.method==='M2'),m3=scores.find(v=>v.method==='M3'),b=D.primaryRows(m.comparisons).find(v=>v.metric==='brier');
    const reasons=JSON.parse(m2.exclusion_reasons);
    return `<section><h1>Prediction test</h1><h2>Inconclusive, but leaning positive.</h2>${copy('question',r,'lede')}${copy('how',r)}${copy('models',r)}${copy('condition',r,'notice')}${scoreTables(m,'main_both_finish','main')}
      ${copy('reading',r,'reading',{m2_acc :formattedMetric(m2.accuracy,'accuracy')+'%',m3_acc :formattedMetric(m3.accuracy,'accuracy')+'%',brier_gain:Math.abs(Number(b.difference)).toFixed(4)})}${copy('leftOut',r,'',{excluded:m2.excluded_pair_count,n1:reasons.one_or_both_retired,n2:reasons.missing_current_qualifying,n3:reasons.did_not_start,n4:reasons.disqualified})}${copy('conditional',r,'notice')}${copy('uncertainty',r,'',{pairs:m2.pair_count})}${copy('brier',r)}${copy('bootstrap',r)}
      <details id="exclusion-drawer"><summary>Left-out races</summary><div id="exclusion-content"><p role="status">Open to view the saved rows.</p></div></details>
      <details id="audit-drawer"><summary>Race-by-race predictions (loads when opened)</summary><p>Positive feature differences favour the first driver.</p><div id="audit-content"><p role="status">Open to view the saved rows.</p></div></details>
      <details id="other-reports"><summary>Early-season and other versions</summary><div class="controls">${select('target-select','Race selection',D.TARGETS.map(v=>({value:v,label:TARGET_LABELS[v]})),'main_both_finish')}${select('period-select','Period',D.PERIODS.map(v=>({value:v,label:PERIOD_LABELS[v]})),'early')}</div><div id="other-report-content">${scoreTables(m,'main_both_finish','early')}</div></details>
      ${end(['metrics','comparisons','counts','winners'],['question','how','models','condition','counts','reading','leftOut','conditional','uncertainty','brier','bootstrap'],r)}</section>
      <section><h2>Does it hold up without any one group?</h2>${copy('stability',r)}<p class="data-line">Data: ${link(D.fileURL('group_stability.csv'),'Download group_stability.csv','download')}</p>${origins(['stability'],r)}</section>`;
  }
  function exclusionTable(rows,config){
    const selected=rows.filter(v=>v.target==='main_both_finish'&&v.eligible==='False'&&Number(v.round_number)>=config.schedule.main_first&&Number(v.round_number)<=config.schedule.main_last);
    return table(['Round','Drivers','Reason'],selected.map(v=>row([esc(v.round_number),esc(v.driver_a+' / '+v.driver_b),esc(REASONS[v.reason_code]||'See exact values')])),'Left-out races','data-exclusion-table="true"')+exactValues(`<pre>${esc(JSON.stringify(selected,null,2))}</pre>`)+sources(['eligibility']);
  }
  function auditTable(rows,method='M3'){
    const selected=D.predictionRows(rows).filter(v=>v.method===method);
    const fields=['round_number','race','driver_a','driver_b','probability','outcome','status_a','status_b','prior_rating_a','prior_rating_b','rating_difference','qualifying_advantage','feature_source_max_round','training_rows','training_max_round','fallback_reason'];
    return `<div class="controls">${select('audit-method','Model',Object.keys(METHODS).map(v=>({value:v,label:METHODS[v]})),method)}</div>`+exactValues(table(fields,selected.map(v=>row(fields.map(k=>esc(v[k]||'No data')))), 'Probability A finishes ahead of B','data-audit-table="true"'))+sources(['predictions']);
  }
  function method(m){
    const r=m.release;
    return `<section><h1>How it works</h1>${copy('methodIntro',r,'lede')}<h2>What a rating means</h2>${copy('meaning',r)}${end(['ratings'],['methodIntro','meaning'],r)}</section>
      <section><h2>Three ways to compare</h2><div class="method-grid"><article><h3>Qualifying</h3>${copy('qualifyingMethod',r)}</article><article><h3>Dry races</h3>${copy('dryMethod',r)}</article><article><h3>Wet races</h3>${copy('wetMethod',r)}</article><article><h3>Combined</h3>${copy('ratingMethod',r)}</article></div>${end(['ratingSummary'],['qualifyingMethod','dryMethod','wetMethod','ratingMethod'],r)}</section>
      <section><h2>How sure is a rating?</h2>${copy('sure',r)}${exactRules(['status','confidence'],r)}${end(['ratings','ratingSummary'],['sure'],r)}</section>
      <section><h2>Where the data is thin</h2><h3>Dry races</h3>${copy('dryCoverage',r,'',COVERAGE)}<h3>Wet races</h3>${copy('wetCoverage',r,'',COVERAGE)}<h3>Miami</h3>${copy('miami',r)}<h3>Monaco</h3>${copy('monaco',r)}${copy('fault',r)}${end(['ratingSummary','diagnostics'],['dryCoverage','wetCoverage','miami','monaco','fault'],r)}</section>
      <section><h2>What this cannot tell you</h2>${copy('limits',r)}${end(['ratings','summary'],['limits'],r)}</section>
      <section>${exactRules(['precision','evidence','status','confidence','noPeriodInterval','overlap','auditDirection','auditHistory','fractions','settings','qualifyingMethod','dryMethod','wetMethod','ratingMethod','strictFirst','regression','wetWeather','wetTraffic','singleWet','bootstrap','leakage','selection','generalLimits','ratingLimits'],r,'Exact rules and settings')}${exactValues(`<pre>${esc(JSON.stringify({rating:m.ratingSummary.settings,prediction:m.config},null,2))}</pre>`)}${sources(['ratingSummary','config','summary'])}</section>`;
  }
  function provenance(m,view){
    const keys={overview:['ratings','ratingSummary','counts','comparisons'],drivers:['ratings','periods','diagnostics'],prediction:['metrics','comparisons','counts','summary','config'],method:['ratingSummary','config','summary']}[view],r=m.release;
    return `<details class="provenance"><summary>Release details and file hashes</summary><p>2025 season · Updated ${esc(r.results_last_updated)}</p>${exactValues(`<pre>${esc(JSON.stringify({rating_method_version:r.rating_method_version,prediction_specification:r.prediction_specification,release_id:r.release_id,prediction_run_id:r.prediction_run_id,date_provenance:r.date_provenance,sources:keys.map(k=>D.sourceEntry(r,D.CONTRACT[k][0]))},null,2))}</pre>`)}${sources(keys)}</details>`;
  }
  function footer(r){return `<p>${esc(r.unofficial_project_disclaimer)}</p><p>${link(r.data_credit.url,'Data from FastF1 and the official F1 timing data it uses.')}</p><p>Code is MIT licensed. The license covers the code only, not the race data.</p><p>${link(r.repository_url,'GitHub')} · ${link(r.license_url,'License')}</p>`;}
  function dataPreview(key,value,model){
    D.check(Object.hasOwn(D.CONTRACT,key),'Unknown data key');
    const [file,columns]=D.CONTRACT[key];
    let body;
    if(['ratings','periods','diagnostics'].includes(key)){
      const roster=key==='ratings'?value:model?.ratings;
      D.check(roster,'Missing comparison groups for preview');
      const groupOf=Object.fromEntries(roster.map(r=>[r.driver,r.comparison_group]));
      D.check(value.every(r=>groupOf[r.driver]),'Unknown preview driver');
      body=[...new Set(roster.map(r=>r.comparison_group))].sort().map(group=>{
        const rows=value.filter(r=>groupOf[r.driver]===group).slice().sort((a,b)=>a.driver.localeCompare(b.driver));
        return table(columns,rows.map(v=>row(columns.map(k=>esc(v[k])))),group+' · Saved values',`data-preview-group="${esc(group)}"`);
      }).join('');
    }else body=columns?table(columns,value.map(v=>row(columns.map(k=>esc(v[k])))),'Saved data'):`<pre>${esc(JSON.stringify(value,null,2))}</pre>`;
    return `<p class="data-line">Data: ${esc(file)} · ${link(D.fileURL(file),'Download file','download')}</p><p>Fields used by this page.</p><details class="exact-values" open><summary>Exact values</summary>${body}</details>`;
  }
  root.DashboardViews={esc,copy,fill,sign,number,interval,table,row,route,groupTable,intervalChart,overview,drivers,driverDetail,prediction,scoreTables,exclusionTable,auditTable,method,provenance,footer,formattedMetric,metricCell,dataPreview,COVERAGE};
  if(typeof module!=='undefined')module.exports=root.DashboardViews;
})(globalThis);
