import argparse
import json
import sqlite3
import sys
from pathlib import Path
from .core import Vault, VaultError, parse


def main():
    parser = argparse.ArgumentParser(description='Agent-neutral Vault local core')
    parser.add_argument('--root', default='.vault', help='shared authoritative store; never put inside public web root')
    subs = parser.add_subparsers(dest='command', required=True)
    for command in ('validate', 'submit'):
        p = subs.add_parser(command)
        p.add_argument('file')
        p.add_argument('--collection', required=True, choices=['books','reading','digest','html'])
        if command == 'submit':
            p.add_argument('--actor', required=True)
            p.add_argument('--id')
            p.add_argument('--expected', type=int, default=0)
            p.add_argument('--reason', default='initial submission')
    subs.add_parser('list')
    subs.add_parser('active')
    p = subs.add_parser('get'); p.add_argument('id'); p.add_argument('--revision', type=int)
    p = subs.add_parser('publish'); p.add_argument('id'); p.add_argument('--revision', type=int, required=True); p.add_argument('--actor', required=True)
    p = subs.add_parser('rollback'); p.add_argument('release'); p.add_argument('--actor', required=True)
    a = parser.parse_args()
    try:
        if a.command == 'validate':
            p = Path(a.file)
            result = parse(p.read_text(encoding='utf-8'), p.name, a.collection)
        else:
            v = Vault(a.root)
            if a.command == 'submit': result = v.submit(a.file, a.collection, a.actor, a.id, a.expected, a.reason)
            elif a.command == 'list': result = v.list()
            elif a.command == 'get': result = v.get(a.id, a.revision)
            elif a.command == 'publish': result = v.publish(a.id, a.revision, a.actor)
            elif a.command == 'rollback': result = v.rollback(a.release, a.actor)
            else: result = v.active()
        print(json.dumps({'ok': True, 'result': result}, ensure_ascii=False, indent=2))
        return 0
    except (VaultError, OSError, sqlite3.Error) as e:
        print(json.dumps({'ok': False, 'error': str(e)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
