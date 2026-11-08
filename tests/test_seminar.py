import json, tempfile, unittest
from pathlib import Path
from agent_vault.seminar import validate, embed_metadata, skill, collection_page
from agent_vault.knowledge_mcp import rpc
from agent_vault.knowledge import Knowledge
from agent_vault.channel import render_channel

class SeminarTest(unittest.TestCase):
    def args(self):return dict(title='研讨文章',html='<html><head></head><body><h1>产品与判断</h1></body></html>',summary='为什么为自己做',date='2026-10-09',tags=['产品'],request_id='seminar-test-001')
    def test_scope_and_skill(self):
        msg=dict(jsonrpc='2.0',id=1,method='tools/list')
        names=[t['name'] for t in rpc(None,msg)['result']['tools']]
        self.assertIn('vault_get_seminar_skill',names);self.assertNotIn('vault_publish_seminar',names)
        self.assertIn('后续讨论',skill()['instructions'])
        msg.update(method='tools/call',params={'name':'vault_publish_seminar','arguments':self.args()})
        self.assertTrue(rpc(None,msg)['result']['isError'])
        seen=[]
        self.assertNotIn('isError',rpc(None,msg,seminar_publisher=lambda a:seen.append(a) or {'published':True})['result'])
        self.assertEqual(seen,[self.args()])
    def test_validation(self):
        for patch in [{'request_id':'../../x'},{'date':'2026-02-30'},{'date':'20261009'},{'tags':'private'},{'html':'fragment'},{'transcript':'private source'}]:
            with self.assertRaises(ValueError):validate({**self.args(),**patch})
    def test_public_metadata_no_private_fields_or_script_breakout(self):
        text=embed_metadata(self.args()['html'],{'content_type':'seminar_settlement','date':'2026-10-09','summary':'</script><script>alert(1)</script>','tags':['产品'],'request_id':'secret-internal','payload_hash':'private'})
        self.assertNotIn('secret-internal',text);self.assertNotIn('payload_hash',text)
        self.assertNotIn('<script>alert(1)</script>',text)
    def test_corpus_and_navigation(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp)/'seminar';d.mkdir();args=self.args()
            (d/'doc.html').write_text(embed_metadata(args['html'],{k:args[k] for k in ['date','summary','tags']}|{'content_type':'seminar_settlement'}))
            k=Knowledge(None,tmp,Path(tmp)/'missing.json');rows=k.corpus()
            self.assertEqual(len(rows),1);self.assertEqual(rows[0]['date'],'2026-10-09');self.assertEqual(rows[0]['summary'],args['summary']);self.assertEqual(rows[0]['collection'],'seminar')
            self.assertEqual(len(k.search('产品')),1)
        page=render_channel(collection_page(),'/vault/seminar/')
        self.assertIn('研讨沉淀',page);self.assertIn('aria-current="page">研讨沉淀',page)
        self.assertIn('work-shell.css',render_channel(self.args()['html'],'/vault/seminar/doc.html'))

class SkillRegistryTest(unittest.TestCase):
    def test_discovery_and_link(self):
        from agent_vault.skill_registry import listing,get,page
        self.assertEqual({r['id'] for r in listing()},{'seminar-settlement','vault-column-standards'})
        self.assertEqual(get(url='https://qiuyiwu.com/vault/seminar/a.html')['version'],'1.1.0')
        with self.assertRaises(ValueError):get(url='https://evil.example/vault/seminar/')
        self.assertIn('SKILL.md',page())
        for args in ({'id':'seminar-settlement'},{'url':'https://qiuyiwu.com/vault/seminar/'}):
            r=rpc(None,dict(jsonrpc='2.0',id=1,method='tools/call',params={'name':'vault_get_skill','arguments':args}))
            self.assertNotIn('isError',r['result'])
    def test_article_toolbar(self):
        p=render_channel('<html><head></head><body><header class="top"><a>旧导航</a></header><main>正文</main></body></html>','/vault/seminar/a.html')
        self.assertNotIn('旧导航',p)
        self.assertIn('seminar-toolbar',p)
        self.assertIn('本篇 Skill',p)
        self.assertEqual(p.count('id="reading"'),1)
