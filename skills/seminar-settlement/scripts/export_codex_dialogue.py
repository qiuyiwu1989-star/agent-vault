"""Export visible Codex conversation batches. No reasoning, tools or credential data."""
import argparse,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--session',required=True);p.add_argument('--document-id',required=True);p.add_argument('--source-id',required=True);p.add_argument('--output',required=True);args=p.parse_args()
raw=Path(args.session).read_bytes();lines=raw.split(b'\n');messages=[]
for n,line in enumerate(lines,1):
 if not line:continue
 try:x=json.loads(line)
 except json.JSONDecodeError:
  if n==len(lines):break
  raise
 a=x.get('payload',{})
 if x.get('type')!='response_item' or a.get('type')!='message' or a.get('role') not in ('user','assistant'):continue
 if a['role']=='assistant' and a.get('phase',a.get('channel')) not in ('final','final_answer','commentary'):continue
 text='\n'.join(c.get('text','') for c in a.get('content',[]) if c.get('type') in ('input_text','output_text','text'))
 if a['role']=='user':
  if '## My request:' in text:text=text.split('## My request:',1)[1].strip()
  elif text.lstrip().startswith(('<environment_context>','<external_codex_apps_open_page>')):continue
 if text:messages.append({'id':'line-'+str(n),'role':a['role'],'text':text,'timestamp':x.get('timestamp','')})
out=Path(args.output);out.mkdir(parents=True,exist_ok=True);batch=[];index=0
for m in messages:
 if batch and (len(batch)>=100 or len(json.dumps(batch,ensure_ascii=False).encode())+len(m['text'].encode())>700000):
  (out/f'batch-{index:03}.json').write_text(json.dumps({'document_id':args.document_id,'source_id':args.source_id,'messages':batch},ensure_ascii=False));index+=1;batch=[]
 batch.append(m)
if batch:(out/f'batch-{index:03}.json').write_text(json.dumps({'document_id':args.document_id,'source_id':args.source_id,'messages':batch},ensure_ascii=False))
print(json.dumps({'messages':len(messages),'batches':index+bool(batch),'last_source_line':messages[-1]['id'] if messages else None}))
