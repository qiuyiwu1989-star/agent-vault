import hashlib
import io
import json
import tarfile
import tempfile
import unittest
from pathlib import Path
from agent_vault.core import Vault,VaultError
from agent_vault.migration import audit
from agent_vault.legacy import metadata,import_review,review_export


class LegacyTests(unittest.TestCase):
    def fixture(self,root):
        prefix='vault-migration-snapshot/'
        files={prefix+'source/vault-staging/books/2026-04-05_旧名.md':
               '# 书\n\n## 书籍元信息\n```\n作者：某作者\n类型：管理 / 设计\n```\n\n**一句话总结：** 核心判断\n\n## 正文\n来源：这是正文中的讨论，不是来源元数据\n'.encode(),
               prefix+'published/vault/html/demo/index.html':b'<title>Demo</title><img src="pic.png"><script>alert(1)</script>',
               prefix+'published/vault/html/demo/pic.png':b'fake asset'}
        items=[{'package_path':n,'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)} for n,b in files.items()]
        files[prefix+'inventory.json']=json.dumps({'count':len(items),'items':items}).encode()
        archive=root/'a.tar.gz'
        with tarfile.open(archive,'w:gz') as t:
            for n,b in files.items():
                m=tarfile.TarInfo(n);m.size=len(b);t.addfile(m,io.BytesIO(b))
        audit(archive,root/'audit');return files

    def test_explicit_fields_only(self):
        r=metadata('# 书\n\n## 书籍元信息\n作者：某人\n类型：管理\n\n## 正文\n来源：正文中出现\n','2026-04-05_旧名.md','markdown')
        self.assertEqual(r['values']['author'],'某人')
        self.assertNotIn('source',r['values']);self.assertNotIn('tags',r['values'])
        self.assertEqual(r['evidence']['date']['method'],'filename')

    def test_import_idempotence_assets_and_no_publication(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);files=self.fixture(root)
            a=import_review(root/'audit',root/'vault','test')
            b=import_review(root/'audit',root/'vault','test')
            self.assertFalse(a['unchanged']);self.assertTrue(b['unchanged'])
            v=Vault(root/'vault');self.assertEqual(v.list(),[]);self.assertIsNone(v.active())
            with v.connect() as db:
                rows=db.execute('SELECT f.path,b.content FROM legacy_files f JOIN legacy_blobs b ON f.sha256=b.sha256').fetchall()
                self.assertEqual(len(rows),3)
                for r in rows:self.assertEqual(r['content'],files[r['path']])
            review_export(root/'vault',a['snapshot'],root/'preview')
            self.assertEqual(len(list((root/'preview').glob('legacy-*.html'))),2)
            for p in (root/'preview').glob('*.html'):self.assertNotIn('<script>',p.read_text())

    def test_tampered_blob_rejected_before_import(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);self.fixture(root)
            next((root/'audit'/'blobs').iterdir()).write_bytes(b'tamper')
            with self.assertRaises(VaultError):import_review(root/'audit',root/'vault','test')
            self.assertFalse((root/'vault').exists())
