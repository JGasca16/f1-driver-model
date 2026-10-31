/* Four hash routes share one static document. URL values select saved records;
   they never supply a filename, a calculation setting or an external request. */
(async function () {
  'use strict';
  const D=DashboardData,V=DashboardViews, main=document.getElementById('main');
  const loader=D.createLoader(window.fetch.bind(window),window.crypto,window.location.href);
  document.querySelector('.skip').addEventListener('click',e=>{e.preventDefault();main.focus();});
  const theme=document.getElementById('theme-select');
  try {const saved=localStorage.getItem('teammate-theme');if(['auto','light','dark'].includes(saved))theme.value=saved;} catch (_) { /* Storage can be disabled. */ }
  document.documentElement.dataset.theme=theme.value;
  theme.addEventListener('change',e=>{
    document.documentElement.dataset.theme=e.target.value;
    try {localStorage.setItem('teammate-theme',e.target.value);} catch (_) { /* Keep this visit usable. */ }
  });
  const dialog=document.getElementById('data-dialog'),dataContent=document.getElementById('data-content');
  let previewRequest=0;
  document.getElementById('close-data').addEventListener('click',()=>dialog.close());
  main.addEventListener('click',async e=>{
    const button=e.target.closest('button[data-source]');if(!button)return;
    const request=++previewRequest;
    dataContent.innerHTML='<p role="status">Loading saved results…</p>';dialog.showModal();
    try {const value=await loader.load(button.dataset.source);if(request===previewRequest)dataContent.innerHTML=V.dataPreview(button.dataset.source,value,model);}
    catch(err){error(dataContent,err);}
  });
  let model, predictions, rendering=0;
  function error(target,e) { target.innerHTML='<p class="notice" role="alert">Saved data could not be loaded.</p><details class="exact-values"><summary>Exact values</summary><pre>'+V.esc(e.message)+'</pre></details>'; }
  try {
    const release=await loader.metadata();
    const keys=['ratings','periods','diagnostics','ratingSummary','metrics','comparisons','counts','summary','config','winners'];
    const values=await Promise.all(keys.map(k=>loader.load(k)));
    model={release,...Object.fromEntries(keys.map((k,i)=>[k,values[i]]))};
    D.validateRatings(model.ratings,model.periods,model.ratingSummary,release);
    D.validatePrediction(model.metrics,model.comparisons,model.counts,model.config,model.summary,release);
    document.getElementById('repository').href=release.repository_url;
    document.getElementById('footer').innerHTML=V.footer(release);
  } catch(e) { error(main,e);main.setAttribute('aria-busy','false');return; }
  function on(id,event,fn) { const e=document.getElementById(id);if(e)e.addEventListener(event,fn); }
  function render(focus=false) {
    const token=++rendering;
    const [page,query='']=location.hash.slice(1).split('?');
    const view=['overview','drivers','prediction','method'].includes(page)?page:'overview';
    const params=new URLSearchParams(query);
    let html;
    try {
      html=view==='drivers'?V.drivers(model,params.get('group'),params.get('driver')):V[view](model);
      main.innerHTML=`<div class="release-strip">${model.release.season} season · Updated ${V.esc(model.release.results_last_updated)}</div>`+html+V.provenance(model,view);
      main.setAttribute('aria-busy','false');
      document.querySelectorAll('nav [data-view]').forEach(a=>{
        if(a.dataset.view===view)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');
      });
      document.title=({overview:'Overview',drivers:'Drivers',prediction:'Prediction test',method:'How it works'}[view])+' · 2025 F1 teammate pace';
      if(focus){main.focus({preventScroll:true});window.scrollTo({top:0,behavior:'instant'});}
      on('group-select','change',e=>{location.hash=V.route('drivers',{group:e.target.value});});
      on('driver-select','change',e=>{location.hash=V.route('drivers',{group:document.getElementById('group-select').value,driver:e.target.value});});
      const updateOther=()=>{
        document.getElementById('other-report-content').innerHTML=V.scoreTables(model,document.getElementById('target-select').value,document.getElementById('period-select').value);
        // Hash filters preserve the selected separate report when shared.
        const target=document.getElementById('target-select').value,period=document.getElementById('period-select').value;
        history.replaceState(null,'',V.route('prediction',{target,period}));
      };
      on('target-select','change',updateOther);on('period-select','change',updateOther);
      if(view==='prediction' && D.TARGETS.includes(params.get('target')) && D.PERIODS.includes(params.get('period'))) {
        document.getElementById('target-select').value=params.get('target');document.getElementById('period-select').value=params.get('period');
        document.getElementById('other-reports').open=true;updateOther();
      }
      on('exclusion-drawer','toggle',async e=>{
        if(!e.target.open || e.target.dataset.loaded)return;e.target.dataset.loaded='true';
        const target=document.getElementById('exclusion-content');
        try { const rows=await loader.load('eligibility');if(token===rendering)target.innerHTML=V.exclusionTable(rows,model.config); }
        catch(e){error(target,e);}
      });
      on('audit-drawer','toggle',async e=>{
        if(!e.target.open || e.target.dataset.loaded)return;e.target.dataset.loaded='true';
        const target=document.getElementById('audit-content');
        function draw(method='M3') {
          target.innerHTML=V.auditTable(predictions,method);on('audit-method','change',e=>draw(e.target.value));
        }
        try { predictions=await loader.load('predictions');if(token===rendering)draw(); }
        catch(e){error(target,e);}
      });
    }catch(e){error(main,e);}
  }
  window.addEventListener('hashchange',()=>render(true));render();
})();
