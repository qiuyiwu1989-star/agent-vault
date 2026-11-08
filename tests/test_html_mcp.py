import unittest
from agent_vault.knowledge_mcp import rpc
class HtmlMcp(unittest.TestCase):
    def test_scope(self):
        msg={'jsonrpc':'2.0','id':1,'method':'tools/list'}
        self.assertEqual(len(rpc(None,msg)['result']['tools']),7)
        self.assertEqual(rpc(None,msg,lambda a:a)['result']['tools'][-1]['name'],'vault_publish_html')
    def test_write(self):
        args={'title':'Test','html':'<html><body>test</body></html>'}
        msg={'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':'vault_publish_html','arguments':args}}
        self.assertTrue(rpc(None,msg)['result']['isError'])
        seen=[]
        self.assertNotIn('isError',rpc(None,msg,lambda a:seen.append(a) or {'url':'test'})['result'])
        self.assertEqual(seen,[args])
        for bad in ({'title':'x','html':'fragment'},dict(args,id='../existing'),dict(args,title='')):
            msg['params']['arguments']=bad
            self.assertTrue(rpc(None,msg,lambda a:a)['result']['isError'])
