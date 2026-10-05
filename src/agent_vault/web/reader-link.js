(async()=>{
  if(document.querySelector('[data-annotation-sdk]'))return;
  const candidates=[...document.querySelectorAll('article,main')].filter(e=>!e.closest('nav,[data-annotation-ignore]'));
  const container=candidates.sort((a,b)=>b.textContent.length-a.textContent.length)[0]||document.body;
  try{
    const {mountVaultAnnotations}=await import('/vault/annotation/vault-adapter.js?v=1');
    await mountVaultAnnotations(container);
  }catch(error){
    const a=document.createElement('a');
    a.href=error.message.includes('登录')?'/admin/login.html?next='+encodeURIComponent(location.pathname):'/admin/vault/read?url='+encodeURIComponent(location.pathname);
    a.textContent=error.message.includes('登录')?'登录后在本文划线与笔记':'在阅读页查看笔记';
    a.title=error.message;
    Object.assign(a.style,{position:'fixed',right:'18px',bottom:'18px',zIndex:10000,background:'#854530',color:'#fff',padding:'9px 14px',borderRadius:'20px',font:'14px system-ui',textDecoration:'none'});
    document.body.append(a);
  }
})();
