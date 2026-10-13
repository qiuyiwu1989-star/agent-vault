import base64,hashlib,io,unittest
from unittest.mock import patch
from PIL import Image
from agent_vault.captures import validate,device

class CaptureValidation(unittest.TestCase):
    def setUp(self):
        f=io.BytesIO();Image.new('RGB',(12,8),'red').save(f,'PNG');self.raw=f.getvalue()
        self.data=dict(image=base64.b64encode(self.raw).decode(),digest=hashlib.sha256(self.raw).hexdigest(),collectedAt='2026-10-13T10:00:00+08:00',modifiedAt='2026-10-13T10:00:00+08:00',ocr='中文检索')
    def test_original_and_timezone(self):
        raw,digest,mime,size,meta=validate(self.data)
        self.assertEqual(raw,self.raw);self.assertEqual(mime,'image/png');self.assertEqual(size,(12,8))
        self.assertEqual(meta['collectedAt'],'2026-10-13T02:00:00+00:00');self.assertEqual(meta['ocr'],'中文检索')
    def test_tampered_digest_rejected(self):
        self.data['digest']='0'*64
        with self.assertRaises(ValueError):validate(self.data)
    def test_non_image_rejected(self):
        self.data.update(image=base64.b64encode(b'<html>bad</html>').decode(),digest=hashlib.sha256(b'<html>bad</html>').hexdigest())
        with self.assertRaises(ValueError):validate(self.data)
    def test_missing_timezone_rejected(self):
        self.data['collectedAt']='2026-10-13T10:00:00'
        with self.assertRaises(ValueError):validate(self.data)
    def test_scoped_device_auth(self):
        class Handler: headers={}
        h=Handler()
        with patch.dict('os.environ',CAPTURE_DEVICE_SHA256=hashlib.sha256(b'test-token').hexdigest()):
            self.assertFalse(device(h));h.headers={'Authorization':'Bearer wrong'};self.assertFalse(device(h))
            h.headers={'Authorization':'Bearer test-token'};self.assertTrue(device(h))


class CaptureListPerformance(unittest.TestCase):
    def test_compact_list_does_not_return_ocr_and_signs_thumbnail(self):
        from unittest.mock import MagicMock
        from agent_vault.captures import listing
        cursor=MagicMock();cursor.fetchall.return_value=[('a'*64,{'name':'test'},'2026-10-13',100,200,'thumb/key')]
        connection=MagicMock();connection.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value=cursor
        with patch('agent_vault.captures.signed_image',return_value='https://example.invalid/private-thumbnail') as sign:
            result=listing(connection,{'summary':['1'],'limit':['24']})
            self.assertNotIn('ocr',result['items'][0]);self.assertEqual(result['items'][0]['thumbnailURL'],'https://example.invalid/private-thumbnail');sign.assert_called_once()
        sql,params=cursor.execute.call_args.args
        self.assertIn("jsonb_build_object('name'",sql);self.assertEqual(params[-2:],(25,0))
    def test_legacy_list_keeps_proxy_urls_without_signing(self):
        from unittest.mock import MagicMock
        from agent_vault.captures import listing
        cursor=MagicMock();cursor.fetchall.return_value=[('b'*64,{'name':'test','ocr':'中文'},'2026-10-13',100,200,'thumb/key')]
        connection=MagicMock();connection.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value=cursor
        with patch('agent_vault.captures.signed_image') as sign:
            result=listing(connection,{})
            self.assertEqual(result['items'][0]['ocr'],'中文');self.assertTrue(result['items'][0]['thumbnailURL'].startswith('/api/zhuazhua/'));sign.assert_not_called()

if __name__=='__main__':unittest.main()
