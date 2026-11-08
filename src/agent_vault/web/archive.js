/* Read-only archive UI. External text is always rendered as text, never HTML. */
(function () {
  'use strict';
  const TYPES = {article:'资料档案',book:'书籍档案',media:'音视频档案',note:'思考笔记',discussion:'研讨档案',brief:'简报',work:'作品与方案'};
  const BODY = {article:'核心内容',book:'阅读整理',media:'内容整理',note:'思考正文',discussion:'讨论整理',brief:'简报正文',work:'成果正文'};
  const KINDS = {original:'原始内容',summary:'内容整理',analysis:'Agent 分析',user_note:'个人笔记',question:'待追问'};
  const $ = id => document.getElementById(id);
  let generation = 0;
  function node(tag, text, cls) { const n=document.createElement(tag); if(text!==undefined)n.textContent=text; if(cls)n.className=cls; return n; }
  function safeURL(value) { try {const u=new URL(value); return ['http:','https:'].includes(u.protocol) ? u.href : null;} catch (_) {return null;} }
  function section(title) {const s=node('section',undefined,'archive-section');s.append(node('h2',title));return s;}
  function recordOf(item) {if(!item || typeof item.id!=='string' || !Number.isInteger(item.revision) || !item.record || typeof item.record!=='object')throw Error('档案响应不完整，请重试。');return item.record;}
  function meta(item,r) {return [TYPES[r.type]||'待分类', '私人档案', '修订 '+item.revision, item.updated_at ? '更新于 '+item.updated_at : '更新时间未记录'].join(' · ');}
  function detail(item) {
    const r=recordOf(item), root=$('archive-content');
    $('page-title').textContent=r.title||'未命名档案';
    root.append(node('p',meta(item,r),'archive-meta'));
    const provenance=section('获取范围与参与者');
    provenance.append(node('p','保存范围：'+(r.coverage||'未记录，请结合来源核对；不代表完整获取。')));
    if(Array.isArray(r.participants)&&r.participants.length){const list=node('ul');for(const p of r.participants){const name=typeof p==='string'?p:(p.name||p.id||'未记录姓名');list.append(node('li',name+(typeof p==='object'&&p.role?' · '+p.role:'')));}provenance.append(list);}
    if(Array.isArray(r.tags)&&r.tags.length)provenance.append(node('p','主题：'+r.tags.join(' / ')));
    root.append(provenance);
    if(Array.isArray(r.sections)&&r.sections.length){for(const part of r.sections){if(!part||typeof part.text!=='string')continue;const block=section(part.title||BODY[r.type]||'正文');block.append(node('p',KINDS[part.kind]||'内容模块','archive-meta'),node('pre',part.text,'archive-body'));root.append(block);}}
    else {const body=section(BODY[r.type]||'正文');body.append(node('pre',typeof r.body==='string'&&r.body?r.body:'尚未整理正文。','archive-body'));root.append(body);}
    const sources=section('来源与获取情况');
    if(!Array.isArray(r.sources)||!r.sources.length)sources.append(node('p','尚未补充来源记录。'));
    else {const list=node('ul');for(const source of r.sources){const s=source&&typeof source==='object'?source:{},li=node('li'),url=safeURL(s.url);li.append(node('span',s.description||'来源材料'));if(url){const a=node('a',' 打开来源');a.href=url;a.target='_blank';a.rel='noopener noreferrer';li.append(a);}else if(s.url)li.append(node('span','（来源地址不可打开）'));li.append(node('p','获取范围：'+(s.coverage||'未记录')));list.append(li);}sources.append(list);}root.append(sources);
  }
  function listing(items) {if(!Array.isArray(items))throw Error('列表响应不完整，请重试。');if(!items.length){$('archive-content').append(node('p','没有找到档案。可以先在 Agent 中保存一段讨论，或换个关键词搜索。'));return;}for(const item of items){const r=recordOf(item),card=node('article',undefined,'archive-card'),h=node('h2'),a=node('a',r.title||'未命名档案');a.href='/admin/vault/archive?id='+encodeURIComponent(item.id);h.append(a);card.append(h,node('p',meta(item,r),'archive-meta'));if(r.body)card.append(node('p',String(r.body).slice(0,180)));$('archive-content').append(card);}}
  async function load() {
    const current=++generation,id=new URLSearchParams(location.search).get('id');
    $('archive-content').replaceChildren();$('page-title').textContent=id?'档案详情':'私人档案';$('archive-status').textContent='正在读取…';$('archive-retry').hidden=true;
    try {const response=await fetch(id?'/api/inside/vault/archive/'+encodeURIComponent(id):'/api/inside/vault/archive?query='+encodeURIComponent($('query').value),{headers:{Accept:'application/json'},credentials:'same-origin'});let data;try{data=await response.json();}catch(_){throw Error('服务响应无法读取，请重试。');}if(current!==generation)return;if(!response.ok){if(response.status===401){const a=node('a','登录个人工作台');a.href='/admin/login.html?next='+encodeURIComponent(location.pathname+location.search);$('archive-status').textContent='请先登录。';$('archive-status').append(a);return;}throw Error(typeof data.error==='string'?data.error:(data.error&&data.error.message)||'无法读取档案。');}if(id)detail(data);else listing(data.items);$('archive-status').textContent=id?'档案已读取。':'已显示 '+data.items.length+' 份档案。';}catch(error){if(current!==generation)return;$('archive-content').replaceChildren();$('page-title').textContent='私人档案';$('archive-status').textContent=error.message||'读取失败，请重试。';$('archive-retry').hidden=false;}
  }
  $('archive-search').onsubmit=e=>{e.preventDefault();if(new URLSearchParams(location.search).get('id')){location.href='/admin/vault/archive?query='+encodeURIComponent($('query').value);return;}load();};
  $('query').value=new URLSearchParams(location.search).get('query')||'';
  $('archive-retry').onclick=load;
  load();
}());
