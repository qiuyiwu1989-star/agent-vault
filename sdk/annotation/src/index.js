import { selectionAnchor, rangeFor } from './dom.js';

const SHELL = `<style>
:host{all:initial;position:fixed;z-index:10000;right:18px;bottom:18px;font:14px/1.6 system-ui;color:#292623}*,*:before,*:after{box-sizing:border-box}button,textarea{font:inherit}button{border:1px solid #cfc7b6;background:#fff;color:#854530;border-radius:10px;padding:8px 12px;cursor:pointer}button:disabled{opacity:.6;cursor:wait}button:focus-visible,textarea:focus-visible{outline:2px solid #854530;outline-offset:2px}#panel{width:min(360px,calc(100vw - 36px));max-height:min(75vh,700px);overflow:auto;background:#fbfaf6;border:1px solid #cfc7b6;border-radius:18px;box-shadow:0 8px 35px #0002;padding:16px}#panel[hidden],#editor[hidden]{display:none}textarea{width:100%;min-height:90px;border:1px solid #cfc7b6;border-radius:10px;padding:9px}blockquote{white-space:pre-wrap;margin:10px 0;padding-left:9px;border-left:3px solid #dfbc64}article{border-top:1px solid #ded8cd;padding:10px 0}article p{margin:5px 0}#status{color:#62594e}#toggle{background:#854530;color:white;border-color:#854530}#close{float:right}
</style><button id="toggle" aria-expanded="false">✎ 我的笔记</button><section id="panel" aria-label="文章笔记" hidden><button id="close" aria-label="收起笔记">收起</button><p id="status" role="status">选中正文即可划线或写笔记。</p><div id="editor" hidden><blockquote id="quote"></blockquote><textarea id="comment" aria-label="笔记内容" placeholder="写下想法；也可以只保存划线"></textarea><button id="save">保存</button><button id="cancel">取消</button></div><div id="list"></div></section>`;

/** Mount one annotation instance on one stable article container. */
export async function mountAnnotations({ container, document: identity, api, locale = 'zh-CN', onSaved, onError }) {
  if (!(container instanceof Element) || !identity?.namespace || !identity?.id) throw new TypeError('container, document.namespace and document.id are required');
  for (const method of ['list','create','update']) if (typeof api?.[method] !== 'function') throw new TypeError(`api.${method} is required`);
  if (container.__annotationInstance) throw new Error('Annotations already mounted on this container');
  const host = document.createElement('div'); host.setAttribute('data-annotation-sdk',''); host.setAttribute('lang',locale); host.attachShadow({ mode:'open' }); host.shadowRoot.innerHTML=SHELL; document.body.append(host);
  const $=selector=>host.shadowRoot.querySelector(selector);
  const id={ namespace:identity.namespace, documentId:identity.id, revision:identity.revision||null };
  let notes=[], candidate=null, editing=null, destroyed=false, busy=false;
  const highlightName='annotation-'+Math.random().toString(36).slice(2);
  const highlightStyle=document.createElement('style');highlightStyle.textContent=`::highlight(${highlightName}){background:#f4dfa0;color:inherit}`;document.head.append(highlightStyle);
  const status=t=>{if(!destroyed)$('#status').textContent=t};
  const fail=e=>{status(e.message||'操作失败');onError?.(e)};
  const show=visible=>{$('#panel').hidden=!visible;$('#toggle').setAttribute('aria-expanded',String(visible))};
  function draw() {
    const list=$('#list');list.replaceChildren();
    for(const note of notes){const article=document.createElement('article'),q=document.createElement('blockquote'),p=document.createElement('p'),button=document.createElement('button');q.textContent=note.quote;p.textContent=note.comment||'仅划线';button.textContent='编辑笔记';button.onclick=()=>{editing=note;candidate=null;$('#quote').textContent=note.quote;$('#comment').value=note.comment||'';$('#editor').hidden=false;show(true)};article.append(q,p,button);list.append(article)}
    if(window.CSS?.highlights && window.Highlight){const ranges=notes.filter(note=>note.anchor?.status!=='unresolved').map(note=>rangeFor(container,note.anchor||note)).filter(Boolean);CSS.highlights.set(highlightName,new Highlight(...ranges))}
  }
  async function refresh(){notes=await api.list(id);if(!Array.isArray(notes))throw new TypeError('api.list must return an array');if(!destroyed)draw();return notes}
  async function capture(){if(destroyed||busy)return;const anchor=selectionAnchor(container);if(!anchor)return;candidate=anchor;editing=null;$('#quote').textContent=anchor.quote;$('#comment').value='';$('#editor').hidden=false;show(true);status('已选中正文，可以保存划线或写笔记。')}
  const mouseup=()=>capture();const keyup=e=>{if(e.key==='Shift'||e.key==='ArrowLeft'||e.key==='ArrowRight')capture()};
  const touchend=()=>requestAnimationFrame(capture);
  const highlightClick=e=>{
    if(!document.caretRangeFromPoint || window.getSelection()?.toString())return;
    const caret=document.caretRangeFromPoint(e.clientX,e.clientY);
    if(!caret)return;
    const note=notes.find(n=>{const range=rangeFor(container,n.anchor||n);return range?.isPointInRange(caret.startContainer,caret.startOffset)});
    if(note){editing=note;candidate=null;$('#quote').textContent=note.quote;$('#comment').value=note.comment||'';$('#editor').hidden=false;show(true)}
  };
  container.addEventListener('mouseup',mouseup);container.addEventListener('keyup',keyup);container.addEventListener('touchend',touchend);container.addEventListener('click',highlightClick);
  $('#toggle').onclick=()=>show($('#panel').hidden);$('#close').onclick=()=>show(false);$('#cancel').onclick=()=>{$('#editor').hidden=true;candidate=null;editing=null};
  $('#save').onclick=async()=>{if(busy||(!candidate&&!editing))return;busy=true;$('#save').disabled=true;try{const record=editing?await api.update(id,editing,{comment:$('#comment').value,expected:editing.version}):await api.create(id,{...candidate,comment:$('#comment').value});await refresh();$('#editor').hidden=true;candidate=null;editing=null;status('笔记已保存。');onSaved?.(record)}catch(e){fail(e)}finally{busy=false;if(!destroyed)$('#save').disabled=false}};
  try{await refresh()}catch(e){fail(e)}
  const instance={refresh,destroy(){if(destroyed)return;destroyed=true;container.removeEventListener('mouseup',mouseup);container.removeEventListener('keyup',keyup);container.removeEventListener('touchend',touchend);container.removeEventListener('click',highlightClick);window.CSS?.highlights?.delete(highlightName);highlightStyle.remove();host.remove();delete container.__annotationInstance}};
  container.__annotationInstance=instance;
  return instance;
}
