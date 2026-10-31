/* Offline tests. Uses only Node built-ins and the packaged release.
   Run: node docs/dashboard/test_dashboard.cjs */
'use strict';
const fs=require('node:fs'), path=require('node:path'), vm=require('node:vm');
const assert=require('node:assert/strict');
const {webcrypto}=require('node:crypto');
const packageDir=path.resolve(__dirname,'../data/2025/release_2025_001');
function context() {
  const c=vm.createContext({URL,URLSearchParams,TextDecoder,Uint8Array,console});
  for(const name of ['content.js','data.js','views.js']) vm.runInContext(fs.readFileSync(path.join(__dirname,name),'utf8'),c,{filename:name});
  return c;
}
async function run() {
  const c=context(),D=c.DashboardData,V=c.DashboardViews;
  const model={release:JSON.parse(fs.readFileSync(path.join(packageDir,'releases.json'),'utf8')).releases[0]};
  for(const [key,[file,columns]] of Object.entries(D.CONTRACT)) {
    const text=fs.readFileSync(path.join(packageDir,file),'utf8');
    model[key]=columns?D.parseCSV(text,columns):JSON.parse(text);
  }
  let passed=0;
  async function test(name,body) {await body();passed++;}
  await test('saved release metadata and all driver-period records agree',()=>{
    D.validateMetadata({schema_version:1,releases:[model.release]});
    D.validateRatings(model.ratings,model.periods,model.ratingSummary,model.release);
    assert.equal(model.ratings.length,21);assert.equal(model.periods.length,78);assert.equal(model.diagnostics.length,63);
  });
  await test('CSV quotes, commas, newlines, blanks, and malformed input',()=>{
    const r=D.parseCSV('driver,notes,value\r\nAAA,"a,b\n""quote""",\r\n',['driver','notes','value']);
    assert.equal(r[0].notes,'a,b\n"quote"');assert.equal(r[0].value,'');
    assert.throws(()=>D.parseCSV('a,b\n"bad,2',['a','b']));
    assert.throws(()=>D.parseCSV('a,a\n1,2',['a']));assert.throws(()=>D.parseCSV('a,b\n1',['a','b']));
  });
  await test('allowlist blocks traversal, URLs, globs and provenance filenames',()=>{
    for(const file of ['../metrics.csv','/metrics.csv','https://example.invalid/x','*.csv','cache.sqlite','2025_qualifying_gaps_by_round.csv','race_pace_dry_final.csv']) assert.throws(()=>D.fileURL(file));
    assert.throws(()=>D.fileURL('metrics.csv','https://example.invalid/'));
  });
  await test('loader uses only allowlisted same-origin package URLs and verifies bytes',async()=>{
    const calls=[];
    const fetcher=async(url,options)=>{
      const u=new URL(url);assert.equal(u.origin,'http://127.0.0.1:8765');
      assert.equal(options.redirect,'error');assert.equal(options.credentials,'omit');
      assert(u.pathname.startsWith('/data/2025/release_2025_001/'));calls.push(u.pathname);
      const bytes=fs.readFileSync(path.join(packageDir,path.basename(u.pathname)));
      return {ok:true,arrayBuffer:async()=>bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength)};
    };
    const l=D.createLoader(fetcher,webcrypto,'http://127.0.0.1:8765/dashboard/index.html');
    assert.equal((await l.load('ratings')).length,21);await l.load('ratings');assert.equal(calls.length,2);
    await assert.rejects(l.load('../ratings'));assert.equal(calls.length,2);
  });
  await test('changed package contents fail before display',async()=>{
    const fetcher=async url=>{const file=path.basename(new URL(url).pathname);let b=fs.readFileSync(path.join(packageDir,file));
      if(file==='driver_rating_2025.csv')b=Buffer.from(b.toString().replace('ALB','ZZZ'));
      return {ok:true,arrayBuffer:async()=>b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength)};};
    await assert.rejects(D.createLoader(fetcher,webcrypto,'http://localhost/dashboard/').load('ratings'),/hash mismatch/);
  });
  await test('failed fetch and unknown metadata stop loading',async()=>{
    await assert.rejects(D.createLoader(async()=>({ok:false}),webcrypto,'http://localhost/dashboard/').load('ratings'));
    const r=JSON.parse(JSON.stringify(model.release));r.rating_method_version='wrong';
    assert.throws(()=>D.validateRatings(model.ratings,model.periods,model.ratingSummary,r));
  });
  await test('all groups stay separate with alphabetical driver ordering',()=>{
    let total=0;
    for(const group of model.release.groups) {
      const rows=D.groupRows(model.ratings,group),html=V.groupTable(model.ratings,group,model.release);
      const codes=Array.from(rows,x=>x.driver);assert.deepEqual(codes,codes.slice().sort());total+=rows.length;
      assert.equal((html.match(/data-rating-table=/g)||[]).length,1);
      assert(html.includes('data-group="'+group+'"'));
      for(const other of model.ratings.filter(x=>x.comparison_group!==group)) assert(!html.includes('data-driver="'+other.driver+'"'));
      assert(!/<th[^>]*>\s*(rank|position|#)\s*<\/th>/i.test(html));
    }
    assert.equal(total,model.ratings.length);
  });
  await test('fixture scores cannot cause an all-group or within-group score sort',()=>{
    const rows=[{driver:'BBB',comparison_group:'AAA+BBB',combined_rating:'-9'},{driver:'AAA',comparison_group:'AAA+BBB',combined_rating:'9'},{driver:'CCC',comparison_group:'CCC+DDD',combined_rating:'-99'}];
    assert.deepEqual(Array.from(D.groupRows(rows,'AAA+BBB'),x=>x.driver),['AAA','BBB']);
    assert.throws(()=>V.intervalChart(rows,'AAA+BBB',model.release));
  });
  await test('inclusive zero boundaries and missing intervals have separate labels',()=>{
    const r={combined_rating:'0.1',combined_ci_low:'-0.2',combined_ci_high:'0.3'};
    assert.equal(D.direction(r),'No clear gap');
    assert.equal(D.direction({...r,combined_ci_low:'0'}),'No clear gap');
    assert.equal(D.direction({...r,combined_ci_high:'0'}),'No clear gap');
    assert.equal(D.direction({...r,combined_ci_low:''}),'Direction uncertain: interval unavailable');
    assert.equal(D.direction({...r,combined_rating:''}),'Rating unavailable');
  });
  await test('high-confidence Norris and Piastri receive no direction claim',()=>{
    const html=V.groupTable(model.ratings,'NOR+PIA',model.release);
    assert.equal((html.match(/class="direction">No clear gap/g)||[]).length,2);
    assert(!html.includes('faster by about'));assert(!html.includes('slower by about'));
  });
  await test('every saved rating and its status and confidence appear unchanged',()=>{
    for(const r of model.ratings) {
      const html=V.driverDetail(model,r);
      for(const key of ['qualifying_rating','dry_rating','wet_rating','combined_rating']) assert(html.includes(V.number(r[key],true)));
      assert(html.includes(r.confidence));assert(html.includes(r.rating_status));
      assert(html.includes(V.interval(r.combined_ci_low,r.combined_ci_high)));
      assert(html.includes('Negative means faster than the teammate'));assert(html.includes(r.rating_units));
    }
  });
  await test('larger groups show the caution and correct visible period rows',()=>{
    for(const group of ['COL+DOO+GAS','HAD+LAW+TSU+VER']) for(const r of D.groupRows(model.ratings,group)) {
      const html=V.driverDetail(model,r);assert(html.includes('Do not subtract two drivers&#39; ratings'));
      const notes=JSON.parse(r.notes);assert.equal((html.match(/data-period-table=/g)||[]).length,notes.teammate_periods.length);
      for(const p of notes.teammate_periods) assert(html.includes(p.driver+' / '+p.teammate));
    }
  });
  await test('Doohan stays provisional and retains the documented label',()=>{
    const html=V.drivers(model,'COL+DOO+GAS','DOO');assert(html.includes('Provisional: only 1 usable dry race out of 4.'));
    assert(html.includes('low/provisional'));assert(html.includes('provisional'));
  });
  await test('inconsistent notes or missing period signals fail validation',()=>{
    const rows=JSON.parse(JSON.stringify(model.ratings));rows[0].notes='not json';assert.throws(()=>D.validateRatings(rows,model.periods,model.ratingSummary,model.release));
    assert.throws(()=>D.validateRatings(model.ratings,model.periods.slice(1),model.ratingSummary,model.release));
    const periods=JSON.parse(JSON.stringify(model.periods));periods[0].rating='9';assert.throws(()=>D.validateRatings(model.ratings,periods,model.ratingSummary,model.release));
  });
  await test('primary prediction rows and sample agree with the saved contract',()=>{
    D.validatePrediction(model.metrics,model.comparisons,model.counts,model.config,model.summary,model.release);
    const scores=D.predictionRows(model.metrics);assert.equal(scores.length,8);
    assert(scores.every(x=>x.pair_count==='95'&&x.weekend_count==='12'&&x.excluded_pair_count==='25'));
    assert.equal(D.primaryRows(model.comparisons).length,3);
  });
  await test('every target and period gets its own levels and paired intervals',()=>{
    for(const t of D.TARGETS)for(const p of D.PERIODS){
      const html=V.scoreTables(model,t,p);
      for(const r of D.predictionRows(model.metrics,t,p)) for(const m of D.METRICS) {
        assert(html.includes(V.metricCell(r[m],r[m+'_ci_low'],r[m+'_ci_high'],m)));
        assert(html.includes(V.esc(r[m])));assert(html.includes(V.esc(r[m+'_ci_low'])));
      }
      for(const r of D.primaryRows(model.comparisons,t,p)) assert(html.includes(V.metricCell(r.difference,r.ci_low,r.ci_high,r.metric,true)));
    }
  });
  await test('source difference is displayed without subtracting rounded scores',()=>{
    const changed={...model,comparisons:JSON.parse(JSON.stringify(model.comparisons))};
    const r=changed.comparisons.find(r=>r.target==='main_both_finish'&&r.period==='main'&&r.comparison==='primary'&&r.metric==='brier');r.difference='-0.1234567';
    assert(V.scoreTables(changed,'main_both_finish','main').includes('−0.1235'));
  });
  await test('exclusion browser has 25 rows and audit has 95 rows per method',()=>{
    assert.equal((V.exclusionTable(model.eligibility,model.config).match(/<tbody><tr>|<\/tr><tr>/g)||[]).length,25);
    for(const method of ['M1','M2','M3','qualifying','grid','previous','head_to_head','chance']) {
      const html=V.auditTable(model.predictions,method);assert.equal((html.match(/<tbody><tr>|<\/tr><tr>/g)||[]).length,95);
    }
  });
  await test('raw lap-time and unapproved columns are never page inputs',()=>{
    for(const [file,cols] of Object.values(D.CONTRACT)) {
      assert(!file.includes('qualifying_gaps_by_round'));if(cols)assert(cols.every(k=>!k.includes('time_seconds')&&!['position_a','position_b'].includes(k)));
    }
  });
  await test('teaching examples, source dates, method versions and footer appear',()=>{
    const html=V.overview(model);assert(html.includes('They are examples, not rankings.'));assert(html.includes('HAM+LEC'));assert(html.includes('NOR+PIA'));
    for(const view of ['overview','drivers','prediction','method']) {
      const p=V.provenance(model,view);assert(p.includes('2026-10-23'));assert(p.includes(model.release.rating_method_version));assert(p.includes('Data:'));
    }
    const footer=V.footer(model.release);assert(footer.includes('not affiliated'));assert(footer.includes('FastF1'));assert(footer.includes('Code is MIT licensed.'));
  });
  await test('stored text is escaped rather than interpreted as markup',()=>{
    assert.equal(V.esc('<script>"&'),'&lt;script&gt;&quot;&amp;');
    const rows=JSON.parse(JSON.stringify(model.ratings));rows[0].driver='<img onerror=bad>';
    const html=V.groupTable(rows,rows[0].comparison_group,model.release);assert(!html.includes('<img'));
  });
  await test('all four views render and there is no deferred route',()=>{
    for(const key of ['overview','prediction','method'])assert(V[key](model).length>1000);
    assert(V.drivers(model,'HAM+LEC','LEC').length>1000);
    const app=fs.readFileSync(path.join(__dirname,'app.js'),'utf8');assert(!app.includes('race_gaps'));assert(app.includes("on('audit-drawer','toggle'"));
  });
  await test('all approved copy blocks have rendered source tags and complete placeholders',()=>{
    const pages=[V.overview(model),V.prediction(model),V.method(model),...model.ratings.map(r=>V.drivers(model,r.comparison_group,r.driver))].join('');
    for(const [key,[file,section]] of Object.entries(c.DashboardCopy)) {
      assert(fs.existsSync(path.resolve(__dirname,'../..',file)));assert(section);
      assert(pages.includes('data-copy="'+key+'"'),key);
      assert(pages.includes('data-origin="'+key+'"'),key);
    }
    assert(!/\{(?:drivers|groups|rounds|m2_acc|m3_acc|brier_gain|pairs|wet_gap)\}/.test(pages));
    assert(pages.includes('Every 95% range for the differences includes zero'));
  });
  await test('numbers in components and periods remain saved values',()=>{
    for(const r of model.ratings){
      const html=V.driverDetail(model,r);
      for(const signal of D.SIGNALS) {
        assert(html.includes(V.number(r[signal+'_weight'])));
        assert(html.includes(r[signal+'_valid']+' / '+r[signal+'_eligible']));
        assert(html.includes(V.number(r[signal+'_effective_races'])));
      }
      for(const p of model.periods.filter(p=>p.driver===r.driver)) {
        assert(html.includes(V.number(p.rating,true)));assert(html.includes(V.number(p.coverage)));
      }
    }
    const html=V.overview(model),score=D.primaryRows(model.comparisons).find(r=>r.metric==='brier');
    assert(html.includes(V.metricCell(score.difference,score.ci_low,score.ci_high,'brier',true)));
    for(const key of ['drivers','comparison_groups'])assert(html.includes('<strong>'+model.ratingSummary[key]+'</strong>'));
  });
  await test('required conditional, uncertainty, thin-data and retirement caveats remain',()=>{
    const p=V.prediction(model),m=V.method(model);
    for(const text of ['Only races where both teammates finished','not the accuracy you would get before a race','not 95 independent tests','No uncertainty ranges were saved for them.'])assert(p.includes(text),text);
    for(const text of ['Of 200 dry-race pairs, 32 have no gap.','Only 6 of 30 eligible wet pairs got a gap','1 is high confidence','I did not label retirements as driver or car fault.','Miami counts for qualifying only.','Its gaps are kept, flagged, and count half.'])assert(m.includes(text),text);
    assert(V.footer(model.release).includes(V.esc(model.release.unofficial_project_disclaimer)));
  });
  await test('raw fields and JSON are confined to exact values or Data lines',()=>{
    function publicText(html) {
      const stack=[];let output='';
      for(const token of html.match(/<[^>]*>|[^<]+/g)||[]) {
        if(token.startsWith('</')){stack.pop();continue;}
        if(token.startsWith('<')) {
          const skip=/class="[^"\n]*(?:exact-values|data-line)/.test(token);
          if(!/^<(?:br|input|meta|link|hr)\b/.test(token))stack.push(skip||stack.includes(true));
        }else if(!stack.includes(true))output+=token+' ';
      }
      return output;
    }
    const pages=[V.overview(model),V.prediction(model),V.method(model),...model.ratings.map(r=>V.drivers(model,r.comparison_group,r.driver))];
    for(const html of pages) {
      const text=publicText(html);
      assert(!/\b(main_both_finish|strategy_confounded|effective_races|combined_rating|season_ci_low|early_fallback)\b|\.(?:csv|json|md)\b|[{}]/.test(text),text.slice(-1000));
      assert(!text.includes('Source:'));
    }
  });
  await test('one sign caption per grouped chart-table block and per period',()=>{
    assert.equal((V.overview(model).match(/class="copy sign-caption"/g)||[]).length,2);
    for(const group of model.release.groups)assert.equal((V.groupTable(model.ratings,group,model.release).match(/class="copy sign-caption"/g)||[]).length,1);
    const r=model.ratings.find(r=>r.driver==='TSU'),html=V.drivers(model,r.comparison_group,r.driver);
    assert.equal((html.match(/class="copy sign-caption"/g)||[]).length,2+JSON.parse(r.notes).teammate_periods.length);
    assert(html.indexOf('Do not subtract')<html.indexOf('class="interval-chart"'));
  });
  await test('data links preview allowlisted fields with a separate download',()=>{
    const html=V.dataPreview('ratings',model.ratings);
    assert(html.includes('download'));assert(html.includes('Exact values'));
    assert.equal((html.match(/<tbody><tr>|<\/tr><tr>/g)||[]).length,21);
    assert.throws(()=>V.dataPreview('../ratings',[]));
    assert(!html.includes('time_seconds'));assert(html.includes('data-line'));
    const app=fs.readFileSync(path.join(__dirname,'app.js'),'utf8');
    assert(app.includes('dialog.showModal()'));assert(app.includes('V.dataPreview'));
  });
  await test('source previews also keep rating groups separate and alphabetical',()=>{
    for(const key of ['ratings','periods','diagnostics']){
      const html=V.dataPreview(key,model[key],model);
      const tables=[...html.matchAll(/<table data-preview-group="([^"]+)"[^>]*>(.*?)<\/table>/gs)];
      assert.equal(tables.length,9);
      for(const [,group,body] of tables){
        const driverColumn=D.CONTRACT[key][1].indexOf('driver');
        const tbody=body.match(/<tbody>(.*?)<\/tbody>/s)[1];
        const rows=[...tbody.matchAll(/<tr>(.*?)<\/tr>/gs)].map(m=>[...m[1].matchAll(/<(?:th|td)[^>]*>(.*?)<\/(?:th|td)>/gs)][driverColumn][1]);
        assert(rows.length);assert.deepEqual(rows,rows.slice().sort());
        assert(rows.every(code=>model.ratings.find(r=>r.driver===code).comparison_group===group));
      }
    }
  });
  await test('dark default and guarded storage for all theme choices',()=>{
    const html=fs.readFileSync(path.join(__dirname,'index.html'),'utf8'),app=fs.readFileSync(path.join(__dirname,'app.js'),'utf8');
    assert(html.includes('data-theme="dark"'));assert(html.includes('value="dark" selected'));
    assert(app.includes("['auto','light','dark']"));
    assert(/try \{[^}]*localStorage.getItem/.test(app));assert(/try \{[^}]*localStorage.setItem/.test(app));
  });
  await test('WCAG AA prose and signal contrast on every theme surface',()=>{
    const css=fs.readFileSync(path.join(__dirname,'styles.css'),'utf8');
    function luminance(hex){const parts=hex.match(/../g).map(p=>parseInt(p,16)/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4);return parts[0]*.2126+parts[1]*.7152+parts[2]*.0722;}
    for(const block of css.matchAll(/(?:^:root \{|:root\[data-theme="light"\] \{)([^}]+)/gm)){
      const palette=Object.fromEntries([...block[1].matchAll(/--([a-z]+):#([a-f0-9]{6})/g)].map(m=>[m[1],m[2]]));
      for(const fg of ['ink','muted','accent','faster','slower','neutral'])for(const bg of ['bg','panel','wash']){
        const a=luminance(palette[fg]),b=luminance(palette[bg]);assert((Math.max(a,b)+.05)/(Math.min(a,b)+.05)>=4.5,fg+'/'+bg);
      }
    }
  });
  return {passed,driverRows:model.ratings.length,periodRows:model.periods.length,diagnosticRows:model.diagnostics.length,groups:model.release.groups.length};
}
module.exports={run};
if(require.main===module)run().then(r=>console.log(JSON.stringify(r))).catch(e=>{console.error(e);process.exitCode=1;});
