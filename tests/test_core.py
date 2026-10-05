import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from agent_vault.core import Vault, VaultError, parse

BASE = '''# 示例

- **日期**：2026-10-04
- **来源**：合成材料
- **作者**：示例作者
- **标签**：测试 / 归档
- **一句话**：有效摘要

## 核心判断
示例正文。
'''


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.v = Vault(self.root / 'store')
        self.f = self.root / '2026-10-04-test.md'
        self.f.write_text(BASE)

    def tearDown(self):
        self.temp.cleanup()

    def submit(self):
        return self.v.submit(self.f, 'reading', 'test')

    def test_strict_contract(self):
        cases = [BASE.replace('合成材料',''), BASE.replace('2026-10-04','2026-99-99'),
                 BASE.replace('有效摘要','长'*70), BASE.replace('测试 / 归档','测试'),
                 BASE+'\n# 第二标题', BASE.replace('- **作者**：示例作者\n',''),
                 BASE.replace('## 核心判断','无章节'), BASE.replace('- **来源**：合成材料','- **来源**：合成材料\n- **来源**：另一来源')]
        for content in cases:
            with self.subTest(content=content), self.assertRaises(VaultError):
                parse(content, self.f.name, 'reading')

    def test_idempotence_and_history(self):
        a = self.submit()
        self.assertTrue(self.submit()['unchanged'])
        self.f.write_text(BASE.replace('示例正文','修改正文'))
        with self.assertRaises(VaultError): self.submit()
        b = self.v.submit(self.f,'reading','other', a['id'],1,'correct source')
        self.assertEqual(b['revision'],2)
        self.assertEqual(self.v.get(a['id'],1)['markdown'],BASE)

    def test_concurrent_revision_conflict(self):
        a = self.submit()
        paths = []
        for n in range(2):
            directory = self.root / str(n); directory.mkdir()
            p = directory / self.f.name; p.write_text(BASE+f'\n变化{n}')
            paths.append(p)
        def write(p):
            try:
                self.v.submit(p,'reading','worker',a['id'],1,'revision')
                return 'ok'
            except VaultError:
                return 'conflict'
        with ThreadPoolExecutor(2) as pool:
            self.assertCountEqual(list(pool.map(write, paths)), ['ok','conflict'])

    def test_single_submission_retains_catalog_and_collection_paths(self):
        a = self.submit(); self.v.publish(a['id'],1,'publisher')
        p = self.root / '2026-10-04-digest.md'; p.write_text(BASE.replace('示例正文','日报正文'))
        b = self.v.submit(p,'digest','another-machine')
        release = self.v.publish(b['id'],1,'publisher')
        target = Path(release['path'])
        catalog = json.loads((target/'catalog.json').read_text())['items']
        self.assertEqual(len(catalog),2)
        self.assertTrue((target/'reading'/f'{a["id"]}.html').is_file())
        self.assertTrue((target/'digest'/'2026-10-04-digest.html').is_file())
        self.assertIn('返回集合', (target/'digest'/f'{b["id"]}.html').read_text())
        self.assertFalse(list(target.rglob('*.md')))

    def test_failed_build_preserves_active_and_publication(self):
        a = self.submit(); self.v.publish(a['id'],1,'publisher')
        previous = self.v.active()
        self.f.write_text(BASE+'\n修改')
        self.v.submit(self.f,'reading','test',a['id'],1,'fix')
        with patch('agent_vault.core.render_body',side_effect=RuntimeError('failed render')):
            with self.assertRaises(RuntimeError): self.v.publish(a['id'],2,'publisher')
        self.assertEqual(self.v.active(),previous)
        self.assertEqual(self.v.list()[0]['published_revision'],1)

    def test_rollback_restores_publication_snapshot(self):
        a = self.submit(); first = self.v.publish(a['id'],1,'publisher')
        self.f.write_text(BASE+'\n修改')
        self.v.submit(self.f,'reading','test',a['id'],1,'fix')
        self.v.publish(a['id'],2,'publisher')
        self.v.rollback(first['release'],'publisher')
        self.assertEqual(self.v.list()[0]['published_revision'],1)
        self.assertEqual(self.v.get(a['id'])['revision'],2)

    def test_publish_stale_revision_rejected(self):
        a = self.submit()
        self.f.write_text(BASE+'\n修改')
        self.v.submit(self.f,'reading','test',a['id'],1,'fix')
        with self.assertRaises(VaultError): self.v.publish(a['id'],1,'publisher')

    def test_html_input_escaped(self):
        self.f.write_text(BASE+'\n<script>alert(1)</script>')
        a = self.submit(); r = self.v.publish(a['id'],1,'publisher')
        html = (Path(r['path'])/'reading'/f'{a["id"]}.html').read_text()
        self.assertNotIn('<script>',html)
        self.assertIn('&lt;script&gt;',html)


if __name__ == '__main__':
    unittest.main()
