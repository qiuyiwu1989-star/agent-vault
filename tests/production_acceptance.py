"""Run on deployment host with PostgreSQL; isolated temporary schema and site."""
import tempfile,uuid
from pathlib import Path
from agent_vault import production as p
original=p.DSN
schema='acceptance_'+uuid.uuid4().hex
with p.connect() as db,db.cursor() as c:c.execute('CREATE SCHEMA '+schema)
try:
    with tempfile.TemporaryDirectory() as tmp:
        p.ROOT=Path(tmp);p.DSN=original+' options=-csearch_path='+schema
        (p.ROOT/'html').mkdir();f=p.ROOT/'html/original.html';f.write_text('<title>Original</title><h1>Original</h1>')
        p.init();items=p.listing();assert len(items)==1
        r=p.get(items[0]['id']);d={**r,'expected':r['revision'],'title':'Edited','content':'<title>Edited</title><h1>Edited</h1>'}
        r=p.save(d);assert 'Original' in f.read_text();p.publish(r['id'],1);assert 'Edited' in f.read_text()
        assert p.get(r['id'],0)['content'].find('Original')>=0
        try:p.save(d);raise AssertionError('stale save accepted')
        except ValueError:pass
        r=p.get(r['id']);d={**r,'expected':1,'content':'<title>New draft</title>'};r=p.save(d)
        f.write_text('<title>External writer</title>')
        try:p.publish(r['id'],2);raise AssertionError('external overwrite accepted')
        except ValueError:pass
        assert p.public_catalog()[0]['title']=='External writer'
        new=p.save(dict(expected=0,title='New markdown',summary='',collection='reading',kind='markdown',content='# New markdown\n\nBody'))
        assert len(p.public_catalog())==1;p.publish(new['id'],1);assert len(p.public_catalog())==2
        assert '127.0.0.1:8765' not in p.shell();assert '/api/inside/vault/save' in p.shell()
        print('PASS: import, draft isolation, publish, original history, stale revision, external conflict, live catalog, markdown, production UI URLs')
finally:
    p.DSN=original
    with p.connect() as db,db.cursor() as c:c.execute('DROP SCHEMA '+schema+' CASCADE')
