'use strict';
/* Drop-in after ui18*.js. Opens the jobs home first and keeps the map quiet. */
(function(){
  const $ = (s, r=document) => r.querySelector(s);

  function compactPrivacy(){
    const n = $('.atlas-privacy');
    if(!n || n.dataset.gui) return;
    n.dataset.gui = '1';
    if(localStorage.getItem('atlas-privacy-hide')==='1'){ n.hidden = true; return; }
    const x = document.createElement('button');
    x.className = 'x';
    x.type = 'button';
    x.setAttribute('aria-label', 'Hide notice');
    x.textContent = '×';
    x.onclick = () => { n.hidden = true; try{ localStorage.setItem('atlas-privacy-hide','1'); }catch(e){} };
    n.append(x);
  }

  function modulesOnly(){
    const sel = $('#componentType');
    if(!sel || sel.value==='module') return;
    sel.value = 'module';
    if(window.Atlas && Atlas.state){
      Atlas.state.componentType = 'module';
      Atlas.state.selOnly = true;
      if(typeof Atlas.render==='function') Atlas.render();
    }else{
      sel.dispatchEvent(new Event('change'));
    }
  }

  function openJobsHome(){
    if(!window.u18 || typeof u18.showHome!=='function') return false;
    const deep = location.hash && location.hash.length>1;
    if(deep) return true;
    u18.showHome(true);
    return true;
  }

  function hookSkip(){
    const skip = $('#u18Skip');
    if(!skip || skip.dataset.gui) return;
    skip.dataset.gui = '1';
    skip.addEventListener('click', () => setTimeout(modulesOnly, 0));
  }

  function hookTabs(){
    document.addEventListener('click', e => {
      const tab = e.target.closest('#u18Tabs [data-u18tab="map"]');
      if(!tab) return;
      setTimeout(() => {
        const busy = window.Atlas && Atlas.state && (Atlas.state.module || Atlas.state.node || Atlas.state.edge || Atlas.state.systems && Atlas.state.systems.size);
        if(!busy) modulesOnly();
      }, 50);
    });
  }

  function boot(n){
    compactPrivacy();
    hookSkip();
    if(!openJobsHome() && n<80) return setTimeout(() => boot(n+1), 80);
    hookTabs();
    compactPrivacy();
  }

  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded', () => boot(0));
  else boot(0);
  addEventListener('load', compactPrivacy);
})();
