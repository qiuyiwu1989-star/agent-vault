"""Short-lived center identity assertion; not a complete replay prevention scheme."""
import hashlib
import hmac
import json
import time

PREFIX = 'X-Vault-Center-'
TTL = 60
ACTIONS = ('rules', 'create', 'search', 'read', 'revise', 'public.search', 'public.read', 'public.entities', 'public.evidence')


def _canonical(body, method, path, identity):
    return json.dumps(dict(v=1, method=method.upper(), path=path,
                           body_sha256=hashlib.sha256(body).hexdigest(), **identity),
                      sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def sign(body, method, path, secret, owner_id, credential_id, actions, request_id, timestamp=None):
    if not isinstance(secret, bytes) or len(secret) < 32 or not isinstance(body, bytes):
        raise ValueError('Invalid signing secret or body')
    identity = dict(owner_id=owner_id, credential_id=credential_id, actions=actions,
                    request_id=request_id, timestamp=int(time.time()) if timestamp is None else timestamp)
    if not all(isinstance(identity[k], str) and 0 < len(identity[k]) <= 160 and not any(ord(c) < 32 or ord(c) > 126 for c in identity[k]) for k in ('owner_id', 'credential_id', 'request_id')):
        raise ValueError('Invalid identity')
    if (not isinstance(actions, list) or not actions or len(actions) > len(ACTIONS)
            or any(a not in ACTIONS for a in actions) or len(set(actions)) != len(actions)
            or type(identity['timestamp']) is not int):
        raise ValueError('Invalid actions or timestamp')
    signature = hmac.new(secret, _canonical(body, method, path, identity), hashlib.sha256).hexdigest()
    values = dict(Owner=owner_id, Credential=credential_id, Actions=json.dumps(actions, separators=(',', ':')),
                  Request=request_id, Timestamp=str(identity['timestamp']), Signature=signature)
    return {PREFIX + k: v for k, v in values.items()}


def verify(headers, body, method, path, secret):
    try:
        lowered = {k.lower(): v for k, v in headers.items()}
        def get(key):
            return lowered.get((PREFIX + key).lower(), '')
        timestamp = int(get('Timestamp'))
        if abs(time.time() - timestamp) > TTL:
            return None
        actions = json.loads(get('Actions'))
        expected = sign(body, method, path, secret, get('Owner'), get('Credential'), actions,
                        get('Request'), timestamp)
        if not hmac.compare_digest(expected[PREFIX + 'Signature'], get('Signature')):
            return None
        return dict(owner_id=get('Owner'), credential_id=get('Credential'), actions=actions,
                    request_id=get('Request'), timestamp=timestamp)
    except (ValueError, TypeError, AttributeError, OverflowError):
        return None
