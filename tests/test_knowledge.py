import tempfile,unittest,json
from pathlib import Path
from agent_vault.knowledge import extract,discoveries,matches,reanchor,Knowledge,safe_url
from agent_vault.knowledge_mcp import rpc,call
class KnowledgeTests(unittest.TestCase):
 def test_extract_removes_executable_and_navigation(self):
  text,links=extract('<head><title>Title</title></head><body><nav>Noise</nav><p>作者：言之（公众号「言之AI笔记」）</p><script>bad()</script><p>Hello <b>World</b></p><a href="https://example.com/a">Source</a></body>')
  self.assertNotIn('bad()',text);self.assertNotIn('Noise',text);self.assertIn('Hello World',text)
  d=dict(id='x',text=text,links=links,collection='reading');names={(e['kind'],e['name']) for e in discoveries(d)}
  self.assertIn(('person','言之'),names);self.assertIn(('wechat','言之AI笔记'),names);self.assertIn(('source','example.com'),names)
 def test_alias_overlap_and_boundaries(self):
  self.assertEqual(len(matches('Aaron Levie and Aaron Levie. Box sandbox.', ['Aaron','Aaron Levie'])),2)
  self.assertEqual(len(matches('Box sandbox BOX', ['Box'])),2)
 def test_anchor_relocate_and_ambiguous(self):
  n=dict(quote='重点',start=0,end=2,content_hash='old',prefix='',suffix='')
  self.assertEqual(reanchor(n,dict(text='新前言重点后文',hash='new'))['start'],3)
  self.assertEqual(reanchor(n,dict(text='重点然后重点',hash='new'))['status'],'unresolved')
 def test_corpus_dates_dedup_summaries(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'reading').mkdir();(root/'reading/2026-10-05-a.html').write_text('<title>A</title><p>正文</p>');(root/'reading/2026-10-05-copy.html').write_text('<title>A copy</title><p>正文</p>');(root/'reading/index.html').write_text('Index')
   builders=root/'builders.json';builders.write_text(json.dumps({'2026-09-09':{'summary':'Aaron Levie','url':'https://feishu.cn/docx/ok'}}));k=Knowledge(None,root,builders);docs=k.corpus();self.assertEqual(len(docs),2);self.assertEqual(k.duplicate,1);self.assertEqual(docs[0]['date'],'2026-10-05');self.assertEqual(docs[1]['kind'],'summary')
   self.assertNotIn('private_notes',k.pack([docs[0]['id']]))
 def test_mcp_cannot_request_notes_or_write(self):
  class Fake:
   def search(self,*args):return []
  response=rpc(Fake(),dict(jsonrpc='2.0',id=1,method='tools/call',params={'name':'vault_search','arguments':{'include_notes':True}}));self.assertTrue(response['result']['isError'])
  response=rpc(Fake(),dict(jsonrpc='2.0',id=2,method='tools/call',params={'name':'vault_save','arguments':{}}));self.assertTrue(response['result']['isError'])
  self.assertIsNone(rpc(Fake(),dict(jsonrpc='2.0',method='notifications/initialized')))
 def test_unsafe_source_url(self):
  self.assertEqual(safe_url('javascript:alert(1)'),'');self.assertEqual(safe_url('https://feishu.cn/docx/a)(https://bad'),'')
if __name__=='__main__':unittest.main()
