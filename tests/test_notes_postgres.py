"""Opt-in PostgreSQL integration. Creates/drops ONLY a random isolated schema.
ZHUA_TEST_DATABASE='dbname=agentvault' python -m unittest discover -s tests -p test_notes_postgres.py
Never contacts COS or writes public captures.
"""
import os,unittest
from uuid import uuid4
import psycopg2
from psycopg2 import sql
from agent_vault import notes,telemetry

@unittest.skipUnless(os.environ.get('ZHUA_TEST_DATABASE'),'isolated PostgreSQL test is opt-in')
class NotesPostgres(unittest.TestCase):
    def setUp(self):
        self.schema='zhua_test_'+uuid4().hex
        with psycopg2.connect(os.environ['ZHUA_TEST_DATABASE']) as db,db.cursor() as c:
            c.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(self.schema)))
        notes.init(self.connect);telemetry.init(self.connect)
        with self.connect() as db,db.cursor() as c:
            c.execute('CREATE TABLE zhuazhua_captures(digest text PRIMARY KEY)')
            c.execute('INSERT INTO zhuazhua_captures VALUES(%s)',('a'*64,))
        self.data=dict(id=str(uuid4()),title='中文笔记',markdown='正文',tags='',sourceURL='',collectedAt='2026-10-13T10:00:00Z',modifiedAt='2026-10-13T10:00:00Z',attachments=['a'*64],version=0)
    def connect(self):
        return psycopg2.connect(os.environ['ZHUA_TEST_DATABASE'],options='-c search_path='+self.schema)
    def tearDown(self):
        with psycopg2.connect(os.environ['ZHUA_TEST_DATABASE']) as db,db.cursor() as c:
            c.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(self.schema)))
    def test_versions_retry_conflict_search(self):
        first=notes.upsert(self.connect,self.data)
        self.assertEqual(first['version'],1)
        self.assertEqual(notes.upsert(self.connect,self.data)['version'],1)
        newer=dict(self.data,version=1,markdown='第二版',collectedAt='2026-10-14T10:00:00Z')
        self.assertEqual(notes.upsert(self.connect,newer)['version'],2)
        self.assertEqual(notes.upsert(self.connect,newer)['version'],2)
        self.assertEqual(notes.detail(self.connect,self.data['id'])['collectedAt'],'2026-10-13T10:00:00+00:00')
        with self.assertRaises(notes.Conflict) as ctx: notes.upsert(self.connect,dict(self.data,markdown='过期编辑'))
        self.assertEqual(ctx.exception.current['markdown'],'第二版')
        self.assertEqual(len(notes.listing(self.connect,{'q':['第二版']})['items']),1)
        self.assertEqual(notes.listing(self.connect,{'q':['没有']})['items'],[])
        self.assertEqual(notes.detail(self.connect,self.data['id'])['version'],2)
    def test_missing_attachment_rolls_back(self):
        with self.assertRaises(ValueError):notes.upsert(self.connect,dict(self.data,attachments=['b'*64]))
        self.assertIsNone(notes.detail(self.connect,self.data['id']))
    def test_aggregate_only(self):
        event=dict(event='note_saved',source='web',outcome='success',durationMs=10,count=1)
        telemetry.record(self.connect,event);telemetry.record(self.connect,event)
        rows=telemetry.metrics(self.connect,{'days':['7']})['items']
        self.assertEqual(rows[0]['samples'],2);self.assertEqual(rows[0]['durationMs'],20)

if __name__=='__main__':unittest.main()
