'use strict';
/* Drop-in after ui18*.js. Opens the jobs home first and keeps the map quiet.
   Public u18.showHome cannot wrap ui18's local showHome(); boot hides home
   once Atlas.data is ready, so keep asserting the home screen for a short
   window after that. */
(function(){
  const $ = (s, r=document) => r.querySelector(s);
  let userLeft = false;
  let afterData = 0;

  function deepLink(){
    return !!(location.hash && location.hash.length>1);
  }

  function compactPrivacy(){
    const n = $('.atlas-privacy');
    if(!n) return false;
    if(n.dataset.gui) return true;
    n.dataset.gui = '1';
    if(localStorage.getItem('atlas-privacy-hide')==='1'){ n.hidden = true; return true; }
    if(n.querySelector('.x')) return true;
    const x = document.createElement('button');
    x.className = 'x';
    x.type = 'button';
    x.setAttribute('aria-label', 'Hide notice');
    x.textContent = '×';
    x.onclick = () => { n.hidden = true; try{ localStorage.setItem('atlas-privacy-hide','1'); }catch(e){} };
    n.append(x);
    return true;
  }

  function modulesOnly(){
    const sel = $('#componentType');
    if(!sel) return false;
    if(sel.value!=='module') sel.value = 'module';
    if(!(window.Atlas && Atlas.state)) return false;
    Atlas.state.componentType = 'module';
    Atlas.state.selOnly = true;
    // Do not dispatch change: ui18's onchange closes the jobs home.
    if(typeof Atlas.render==='function' && !document.body.classList.contains('u18home')) Atlas.render();
    return true;
  }

  function openJobsHome(){
    if(!window.u18 || typeof u18.showHome!=='function') return false;
    if(deepLink() || userLeft) return true;
    if(!(window.Atlas && Atlas.data)) return false;
    u18.showHome(true);
    modulesOnly();
    return true;
  }

  function hookSkip(){
    const skip = $('#u18Skip');
    if(!skip || skip.dataset.gui) return;
    skip.dataset.gui = '1';
    skip.addEventListener('click', () => {
      userLeft = true;
      setTimeout(modulesOnly, 0);
    }, true);
  }

  function hookTabs(){
    if(hookTabs.on) return;
    hookTabs.on = 1;
    document.addEventListener('click', e => {
      if(e.target.closest('#u18HomeScr [data-job], #u18Tabs [data-u18tab]')) userLeft = true;
      const tab = e.target.closest('#u18Tabs [data-u18tab="map"]');
      if(!tab) return;
      setTimeout(() => {
        const busy = window.Atlas && Atlas.state && (Atlas.state.module || Atlas.state.node || Atlas.state.edge || Atlas.state.systems && Atlas.state.systems.size);
        if(!busy) modulesOnly();
      }, 50);
    }, true);
    addEventListener('hashchange', () => { if(deepLink()) userLeft = true; });
  }

  function boot(n){
    compactPrivacy();
    hookSkip();
    hookTabs();
    const ready = openJobsHome();
    compactPrivacy();
    if(!window.u18 || typeof u18.showHome!=='function' || !(window.Atlas && Atlas.data)){
      if(n<100) return setTimeout(() => boot(n+1), 80);
      return;
    }
    if(!deepLink() && !userLeft){
      afterData++;
      if(afterData<24) return setTimeout(() => boot(n+1), 50);
    }
    modulesOnly();
    if(!compactPrivacy() && n<120) return setTimeout(() => boot(n+1), 120);
  }

  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded', () => boot(0));
  else boot(0);
  addEventListener('load', () => {
    compactPrivacy();
    if(!deepLink() && !userLeft && window.u18 && typeof u18.showHome==='function') u18.showHome(true);
    modulesOnly();
  });
})();
