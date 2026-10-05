import hashlib
import io
import json
import tarfile
import tempfile
import unittest
from pathlib import Path
from agent_vault.migration import audit
from agent_vault.core import VaultError


class MigrationTests(unittest.TestCase):
    def package(self, path, files):
        with tarfile.open(path,'w:gz') as t:
            for name,body in files.items():
                m=tarfile.TarInfo(name);m.size=len(body);t.addfile(m,io.BytesIO(body))

    def test_lossless_and_manifest_mismatch(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);name='vault-migration-snapshot/published/vault/html/demo.html'
            body=b'<img src="missing.png"><script>throw 1</script>'
            inventory={'count':1,'items':[{'package_path':name,'sha256':'bad','bytes':len(body)}]}
            self.package(root/'a.tar.gz',{name:body,'vault-migration-snapshot/inventory.json':json.dumps(inventory).encode()})
            r=audit(root/'a.tar.gz',root/'out')
            self.assertEqual(r['checksum_mismatches'],[name])
            self.assertEqual(len(r['missing_local_resources']),1)
            self.assertEqual((root/'out'/'blobs'/hashlib.sha256(body).hexdigest()).read_bytes(),body)
            self.assertNotIn('<script>',(root/'out'/'index.html').read_text())

    def test_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);self.package(root/'a.tar.gz',{'../escape':b'bad'})
            with self.assertRaises(VaultError):audit(root/'a.tar.gz',root/'out')
            self.assertFalse((root/'escape').exists())
