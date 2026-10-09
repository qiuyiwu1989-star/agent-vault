import os,sys,json,base64,io,wave,hashlib
from pathlib import Path
from agent_vault.production import KNOWLEDGE
from agent_vault.tts import synthesize
r=KNOWLEDGE.brief(sys.argv[1] if len(sys.argv)>1 else None);root=Path(os.environ.get('VAULT_TTS_CACHE','/var/lib/agent-vault/tts'));root.mkdir(exist_ok=True)
(root/(r['day']+'.json')).write_text(json.dumps(r,ensure_ascii=False,indent=2));(root/(r['day']+'.txt')).write_text(r['script'])
chunks=[r['script'][i:i+300] for i in range(0,len(r['script']),300)]
frames=[];params=None
for i,t in enumerate(chunks):
 audio=base64.b64decode(synthesize(t)['audio'])
 with wave.open(io.BytesIO(audio)) as w:
  p=(w.getnchannels(),w.getsampwidth(),w.getframerate())
  if params and params!=p:raise ValueError('audio format changed')
  params=p;frames.append(w.readframes(w.getnframes()))
 print('part',i+1,'/',len(chunks),flush=True)
out=root/(r['day']+'.wav');tmp=out.with_suffix('.tmp')
with wave.open(str(tmp),'wb') as w:
 w.setnchannels(params[0]);w.setsampwidth(params[1]);w.setframerate(params[2]);w.writeframes(b''.join(frames))
tmp.chmod(0o600);tmp.replace(out)
print(json.dumps({'day':r['day'],'mode':r['mode'],'sources':len(r['items']),'characters':len(r['script']),'seconds':len(b''.join(frames))/(params[0]*params[1]*params[2]),'bytes':out.stat().st_size}),flush=True)
