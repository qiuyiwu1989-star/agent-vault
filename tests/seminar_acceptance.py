"""PostgreSQL acceptance in isolated schema and directory; never publish live samples."""
import tempfile, uuid
from pathlib import Path
from agent_vault import production as p
from agent_vault.knowledge import Knowledge

original=p.DSN;old_root=p.ROOT;old_knowledge=p.KNOWLEDGE
schema='seminar_acceptance_'+uuid.uuid4().hex
with p.connect() as db,db.cursor() as c:c.execute('CREATE SCHEMA '+schema)
try:
    with tempfile.TemporaryDirectory() as tmp:
        p.ROOT=Path(tmp);p.DSN=original+' options=-csearch_path='+schema
        p.KNOWLEDGE=Knowledge(p.connect,p.ROOT,p.ROOT/'missing.json')
        p.init()
        args=dict(title='Sample seminar',html='<html><head><title>Sample</title></head><body><h1>Knowledge</h1><p>Product judgment.</p></body></html>',summary='Test summary',date='2026-10-09',tags=['产品'],request_id='acceptance-request-001')
        r=p.publish_seminar(args);assert r['published'] and r['collection']=='seminar' and not r['unchanged']
        again=p.publish_seminar(args);assert again['id']==r['id'] and again['unchanged']
        assert len(p.listing())==len(p.public_catalog())==1
        cat=p.public_catalog()[0];assert cat['date']=='2026-10-09' and cat['summary']=='Test summary' and cat['tags']==['产品']
        try:p.publish_seminar({**args,'title':'Different'});raise AssertionError('changed retry accepted')
        except ValueError:pass
        assert p.KNOWLEDGE.search('judgment')[0]['collection']=='seminar'
        saved=p.get(r['id']);draft=p.save({**saved,'content':saved['content'].replace('Product judgment.','Owner draft.'),'expected':saved['revision']})
        again=p.publish_seminar(args)
        assert again['revision']==1 and p.get(r['id'])['revision']==2
        assert 'Owner draft.' not in p.target('seminar/'+r['id']+'.html').read_text()
        p.publish(r['id'],draft['revision'])
        assert p.get(r['id'],1)['content']==args['html']
        assert 'Owner draft.' in p.target('seminar/'+r['id']+'.html').read_text()
        assert 'vault-seminar-metadata' in p.target('seminar/'+r['id']+'.html').read_text()
        assert '研讨沉淀' in p.shell()
        print('PASS: seminar publish, exact retry reuse, changed retry refusal, public metadata, search, draft isolation, owner revision history')
finally:
    p.DSN=original;p.ROOT=old_root;p.KNOWLEDGE=old_knowledge
    with p.connect() as db,db.cursor() as c:c.execute('DROP SCHEMA '+schema+' CASCADE')
