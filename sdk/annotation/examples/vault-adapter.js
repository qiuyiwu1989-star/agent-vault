/** Vault adapter: signed-in notes use the server; guests use this browser only. */
import { locate, context } from './anchor.js';
import { textMap } from './dom.js';
import { mountAnnotations } from './index.js';

export async function mountVaultAnnotations(container, path=location.pathname){
  const sessionResponse=await fetch('/api/inside/annotations/v1/session',{credentials:'same-origin'});
  if(sessionResponse.status===401)return mountGuestAnnotations(container,path);
  if(!sessionResponse.ok)throw new Error('笔记服务暂时不可用，请稍后重试。');
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

function mountGuestAnnotations(container,path){
  const key='web-annotations:v1:'+location.origin+':'+path;
  const read=()=>{try{const rows=JSON.parse(localStorage.getItem(key)||'[]');return Array.isArray(rows)?rows:[]}catch{return []}};
  const write=rows=>localStorage.setItem(key,JSON.stringify(rows));
  const canonical=anchor=>{const text=textMap(container).text;let found=locate(text,anchor);if(found.status==='unresolved')found=locate(text,{quote:anchor.quote,prefix:anchor.prefix,suffix:anchor.suffix});if(found.status==='unresolved')throw new Error('原文无法唯一定位，请重新选择。');return context(text,found.start,found.end)};
  return mountAnnotations({
    container,document:{namespace:'guest',id:path,revision:null},modeLabel:'仅存此浏览器',
    api:{
      list:async()=>read(),
      create:async(_,data)=>{const rows=read();const record={id:crypto.randomUUID(),...canonical(data),comment:data.comment,color:data.color,version:1};rows.push(record);write(rows);return record},
      update:async(_,note,change)=>{const rows=read(),at=rows.findIndex(row=>row.id===note.id);if(at<0||rows[at].version!==change.expected)throw new Error('笔记已变化，请刷新后重试。');rows[at]={...rows[at],comment:change.comment,color:change.color,version:rows[at].version+1};write(rows);return rows[at]},
    },
  });
}
