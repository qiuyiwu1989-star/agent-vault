import unittest
from uuid import uuid4
from agent_vault import notes, telemetry


def sample():
    return dict(id=str(uuid4()),title='笔记',markdown='# 你好\n正文',tags='测试',sourceURL='',collectedAt='2026-10-13T10:00:00Z',modifiedAt='2026-10-13T10:00:00Z',attachments=[],version=0)

class ValidationTests(unittest.TestCase):
    def test_image_references_registered(self):
        data=sample();data['markdown']='![图](/api/zhuazhua/image/'+'a'*64+')'
        self.assertEqual(notes.validate(data)[0]['attachments'],['a'*64])
    def test_reject_empty_and_invalid_versions(self):
        for patch in ({'id':None},{'id':42},{'markdown':'bad\x00text'},{'markdown':'  '},{'version':True},{'attachments':['https://example.com']},{'collectedAt':'2026-01-01'}):
            with self.assertRaises(ValueError): notes.validate(dict(sample(),**patch))
    def test_telemetry_rejects_content_and_unbounded_values(self):
        base=dict(event='note_saved',source='web',outcome='success')
        self.assertEqual(telemetry.validate(base)['count'],0)
        for patch in ({'markdown':'private'},{'source':'secret-site'},{'durationMs':-1},{'count':True},{'errorCode':'private exception'}):
            with self.assertRaises(ValueError): telemetry.validate(dict(base,**patch))


class NoteRoutes(unittest.TestCase):
    def handler(self,origin=None):
        from unittest.mock import MagicMock
        import io,json
        h=MagicMock();h.path='/api/zhuazhua/notes';h.authenticated.return_value=True
        body=json.dumps(sample()).encode();h.rfile=io.BytesIO(body)
        h.headers={'Content-Length':str(len(body))}
        if origin is not None:h.headers['Origin']=origin
        return h
    def test_cookie_write_requires_explicit_same_origin(self):
        from agent_vault import captures
        from unittest.mock import patch
        for origin,status in [(None,401),('https://attacker.invalid',403)]:
            h=self.handler(origin)
            with patch.object(captures,'device',return_value=False),patch.object(notes,'upsert') as save:
                captures.handle(h,None,'POST');self.assertEqual(h.reply.call_args.args[0],status);save.assert_not_called()
    def test_cookie_same_origin_write(self):
        from agent_vault import captures
        from unittest.mock import patch
        h=self.handler('https://qiuyiwu.com')
        with patch.object(captures,'device',return_value=False),patch.object(notes,'upsert',return_value={'attachments':[],'version':1}):
            captures.handle(h,None,'POST');self.assertEqual(h.reply.call_args.args[0],200)
    def test_conflict_returns_current(self):
        from agent_vault import captures
        from unittest.mock import patch
        h=self.handler('https://qiuyiwu.com')
        with patch.object(captures,'device',return_value=False),patch.object(notes,'upsert',side_effect=notes.Conflict({'version':2})):
            captures.handle(h,None,'POST');self.assertEqual(h.reply.call_args.args[0],409)
            self.assertEqual(h.reply.call_args.args[1]['current']['version'],2)

if __name__=='__main__': unittest.main()
