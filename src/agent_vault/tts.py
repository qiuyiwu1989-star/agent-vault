"""Private MiMo audio cache; credentials are supplied by systemd."""
import base64,hashlib,json,os,threading
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
LOCK=threading.Lock()
def synthesize(text):
    if not isinstance(text,str) or not text.strip() or len(text)>400:raise ValueError('语音文本须为 1–400 字')
    key=os.environ.get('MIMO_API_KEY','')
    if not key:raise ValueError('MiMo 语音服务尚未配置')
    model='mimo-v2.5-tts';voice='mimo_default'
    digest=hashlib.sha256((model+voice+text).encode()).hexdigest()
    path=Path(os.environ.get('VAULT_TTS_CACHE','/var/lib/agent-vault/tts'))/(digest+'.wav')
    with LOCK:
        if path.exists():audio=path.read_bytes()
        else:
            payload={'model':model,'messages':[{'role':'assistant','content':text}],'modalities':['text','audio'],'audio':{'format':'wav','voice':voice}}
            request=Request(os.environ.get('MIMO_BASE_URL','https://token-plan-cn.xiaomimimo.com/v1').rstrip('/')+'/chat/completions',data=json.dumps(payload).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
            try:
                with urlopen(request,timeout=45) as response:result=json.load(response)
                audio=base64.b64decode(result['choices'][0]['message']['audio']['data'],validate=True)
                if audio[:4]!=b'RIFF' or audio[8:12]!=b'WAVE':raise ValueError('MiMo 返回了无效音频')
            except HTTPError as e:raise ValueError('MiMo 语音请求失败（HTTP %s），请稍后重试'%e.code) from None
            except (URLError,TimeoutError,KeyError):raise ValueError('MiMo 语音暂时不可用，请稍后重试') from None
            path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix('.tmp');tmp.write_bytes(audio);tmp.chmod(0o600);tmp.replace(path)
    return {'audio':base64.b64encode(audio).decode(),'mime':'audio/wav','provider':'MiMo','id':digest}
