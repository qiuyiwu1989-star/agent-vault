/** Vault adapter. Human session only; the SDK itself is host-agnostic. */
import { locate, context } from './anchor.js';
import { mountAnnotations } from './index.js';

export async function mountVaultAnnotations(container, path=location.pathname){
  const sessionResponse=await fetch('/api/inside/annotations/v1/session',{credentials:'same-origin'});
  if(!sessionResponse.ok)throw new Error('请先登录个人工作台，然后回到本文。');
  const {csrf}=await sessionResponse.json();
  const sourceResponse=await fetch('/api/inside/vault/knowledge/read?url='+encodeURIComponent(path),{credentials:'same-origin'});
  if(!sourceResponse.ok)throw new Error('当前文稿尚未建立可批注的正文索引。');
  const source=await sourceResponse.json();
  const route='/api/inside/annotations/v1/documents/vault/'+encodeURIComponent(source.id)+'/annotations';
  async function request(url,method='GET',body){
    const res=await fetch(url,{method,credentials:'same-origin',headers:{'Content-Type':'application/json','X-Vault-Token':csrf},body:body?JSON.stringify(body):undefined});
    const value=await res.json();if(!res.ok)throw new Error(value.error||'批注操作失败');return value;
  }
  function canonical(anchor){
    const found=locate(source.text,{quote:anchor.quote});
    if(found.status==='unresolved')throw new Error('这段文字无法在正文中唯一定位，请选择更完整的连续文字。');
    return context(source.text,found.start,found.end);
  }
  return mountAnnotations({
    container,
    document:{namespace:'vault',id:source.id,revision:source.hash},
    api:{
      list:()=>request(route),
      create:(_,data)=>request(route,'POST',{...canonical(data),contentRevision:source.hash,comment:data.comment,color:data.color}),
      update:(_,note,data)=>request(route+'/'+encodeURIComponent(note.id),'PATCH',data),
    },
  });
}
