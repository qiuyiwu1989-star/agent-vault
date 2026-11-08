(async()=>{
  if(document.querySelector('[data-annotation-sdk]'))return;
  const candidates=[...document.querySelectorAll('article,main')].filter(e=>!e.closest('nav,[data-annotation-ignore]'));
  const container=candidates.sort((a,b)=>b.textContent.length-a.textContent.length)[0]||document.body;
  try{
    const {mountVaultAnnotations}=await import('/vault/annotation/vault-adapter.js?v=1');
    const instance=await mountVaultAnnotations(container);
    const controls=document.querySelector('.bp-controls');
    if(controls&&instance?.open){const button=document.createElement('button');button.type='button';button.textContent='笔记';button.setAttribute('aria-label','打开本文笔记');button.onclick=()=>instance.open(button);controls.append(button);instance.setTrigger?.(button);document.querySelector('[data-annotation-sdk]')?.setAttribute('data-vault-inline','');}
  }catch(error){
    const a=document.createElement('a');
    a.href=error.message.includes('登录')?'/admin/login.html?next='+encodeURIComponent(location.pathname+location.search):'/admin/vault/read?url='+encodeURIComponent(location.pathname);
    a.textContent=error.message.includes('登录')?'登录后在本文划线与笔记':'在阅读页查看笔记';
    a.title=error.message;
    a.className='vault-reader-fallback';
    document.body.append(a);
  }
})();
