(()=>{
 const main=document.querySelector('main,[role=main]')||document.querySelector('article,.wrap,.container,.page,.sheet');if(main&&!main.matches('main,[role=main]'))main.setAttribute('role','main');
 if(main){if(!main.id)main.id='vault-main';const skip=document.createElement('a');skip.className='vault-skip';skip.href='#'+main.id;skip.textContent='跳到正文';document.body.prepend(skip);if(!main.hasAttribute('tabindex'))main.tabIndex=-1;}
 const browse=document.querySelector('.vn-browse');if(browse){document.addEventListener('click',e=>{if(!browse.contains(e.target))browse.open=false});document.addEventListener('keydown',e=>{if(e.key==='Escape'&&browse.open){browse.open=false;browse.querySelector('summary').focus()}});}
 function wrapTables(){document.querySelectorAll('table').forEach(t=>{if(t.closest('.vault-table-scroll'))return;const w=document.createElement('div');w.className='vault-table-scroll';w.tabIndex=0;w.setAttribute('role','region');w.setAttribute('aria-label','数据表，可横向滚动');t.before(w);w.append(t)});}
 document.querySelectorAll('.arch').forEach(e=>{e.tabIndex=0;e.setAttribute('role','region');e.setAttribute('aria-label','关系图，宽图可横向滚动')});
 wrapTables();const app=document.querySelector('#app');if(app)new MutationObserver(wrapTables).observe(app,{childList:true,subtree:true});
 // Only fix verified missing labels; never use placeholder as a general substitute.
 if(location.pathname.includes('apps-zaowuyun'))document.querySelector('input[type=search]')?.setAttribute('aria-label','搜索造物云应用');
 if(location.pathname.includes('ceo-os-workbench-v1')){document.querySelector('#trig')?.setAttribute('aria-label','描述触发本次判断的事件');document.querySelectorAll('.card').forEach(c=>{if(typeof c.onclick!=='function')return;c.tabIndex=0;c.setAttribute('role','button');c.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();c.click()}})});const cards=document.querySelector('#cards');if(cards)new MutationObserver(()=>{cards.querySelectorAll('.card:not([role=button])').forEach(c=>{c.tabIndex=0;c.setAttribute('role','button');c.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();c.click()}}})}).observe(cards,{childList:true});}
 // Restore the original site's relative-link context, never infer destinations.
 if(location.pathname==='/vault/html/apps-zaowuyun.html'){
  const canonical=document.querySelector('link[rel=canonical]')?.href;
  if(canonical){document.querySelectorAll('a[href]').forEach(a=>{const raw=a.getAttribute('href');if(raw&&!/^(?:[a-z]+:|\/|#)/i.test(raw)){a.href=new URL(raw,canonical).href;a.target='_blank';a.rel='noopener noreferrer'}});const notice=document.createElement('aside');notice.className='vault-source-notice';notice.textContent='这是应用市场的归档展示；应用与产品链接前往原站，归档本身不提供在线服务。';document.querySelector('.vault-nav')?.after(notice);}
 }
})();
