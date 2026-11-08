"""Home preview uses the existing authenticated captures API; HTML stays public."""
PREVIEW = '''<section id="home-captures" aria-labelledby="home-captures-title">
<style>
#home-captures{margin:32px 0;padding:24px 0;border-block:1px solid var(--v-line,#d9ded5)}
#home-captures header{display:flex;align-items:baseline;justify-content:space-between;gap:16px;flex-wrap:wrap}
#home-captures h2{margin:0;font-size:24px}#home-captures p{line-height:1.7;color:var(--v-muted,#657065)}
#home-captures a{color:inherit;text-underline-offset:4px}#home-captures a:focus-visible{outline:2px solid currentColor;outline-offset:4px}
#home-captures-grid{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:12px}
#home-captures-grid a{display:block;aspect-ratio:1;overflow:hidden;border-radius:12px;background:var(--v-bg,#faf9f5)}
#home-captures-grid img{width:100%;height:100%;object-fit:contain;display:block}
@media(max-width:700px){#home-captures-grid{grid-template-columns:repeat(3,minmax(0,1fr))}}
</style>
<header><h2 id="home-captures-title">爪爪 · 随手留下的图</h2><a href="/vault/inbox/">打开爪爪收件箱 →</a></header>
<p id="home-captures-status" role="status">正在加载最近收集的图片…</p>
<div id="home-captures-grid"></div><p><a href="/vault/annotations/">阅读批注</a> · <a href="/vault/dialogues/">研讨原始对话</a> · <a href="/vault/briefs/">内容简报</a></p>
<script>
(async()=>{
const status=document.getElementById('home-captures-status'),grid=document.getElementById('home-captures-grid');
try{
 const response=await fetch('/api/zhuazhua/captures?summary=1&limit=6',{credentials:'same-origin',cache:'no-store'});
 if(response.status===401||response.status===403){status.textContent='截图、灵感与随手收集的图片，登录后在这里查看。';return;}
 if(!response.ok)throw Error();
 const data=await response.json();if(!Array.isArray(data.items))throw Error();
 status.textContent=data.items.length?'最近收集 · 公开阅读':'还没有图片，使用爪爪收集后会出现在这里。';
 for(const item of data.items){
  if(!/^[a-f0-9]{64}$/.test(item.digest))continue;
  const link=document.createElement('a'),img=document.createElement('img');
  link.href='/vault/inbox/';link.setAttribute('aria-label','在爪爪收件箱查看图片');
  img.alt=typeof item.name==='string'?item.name:'爪爪收集的图片';img.loading='lazy';img.decoding='async';
  img.src='/api/zhuazhua/thumbnail/'+item.digest;
  img.onerror=()=>{img.remove();link.textContent='图片暂不可用，打开收件箱查看';};
  link.append(img);grid.append(link);
 }
}catch(e){status.textContent='图片暂时无法加载，请刷新页面重试，或打开爪爪收件箱。';}
})();
</script></section>'''


def decorate(content, path):
    if path not in ('/vault/', '/vault/index.html') or 'id="home-captures"' in content:
        return content
    # Retain the introduction, then show images ahead of the content filters.
    marker = '<section class="channel-toolbar"'
    if marker in content:
        return content.replace(marker, PREVIEW + marker, 1)
    return content.replace('</main>', PREVIEW + '</main>', 1)
