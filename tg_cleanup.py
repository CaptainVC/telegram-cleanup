import os
import json
import time
import argparse
from dataclasses import dataclass
from datetime import datetime

from telethon import TelegramClient
from telethon.errors import ChatAdminRequiredError, ChannelPrivateError, UserDeactivatedBanError
from telethon.tl.functions.channels import LeaveChannelRequest
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.types import InputPeerEmpty

from jinja2 import Environment, FileSystemLoader

DEFAULT_KEYWORDS_HIGH = [
    'trading','trader','signal','signals','calls','call','premium',
    'forex','fx','crypto','bitcoin','btc','eth','altcoin',
    'options','option','f&o','fno','futures','expiry','intraday','scalping',
    'nifty','banknifty','sensex','finifty',
    'stoploss','sl','target','tgt','tp'
]

DEFAULT_KEYWORDS_MED = [
    'breakout','swing','momentum','chart','technical analysis','price action',
    'pump','dump','leverage',
    'binance','bybit','okx',
    'zerodha','upstox','angel','groww'
]

DEFAULT_NEGATIVE = ['jobs','hiring','interview','placement','college','course','study']

@dataclass
class ChatCandidate:
    id: int
    title: str
    username: str
    kind: str
    score: int
    reasons: list


def load_env():
    # Minimal .env loader
    if os.path.exists('.env'):
        for line in open('.env', 'r', encoding='utf-8'):
            line=line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k,v = line.split('=',1)
            os.environ.setdefault(k.strip(), v.strip())


def compute_score(title: str, username: str):
    text = f"{title} {username}".lower()
    score = 0
    reasons = []

    for kw in DEFAULT_KEYWORDS_HIGH:
        if kw in text:
            score += 25
            reasons.append(kw)

    for kw in DEFAULT_KEYWORDS_MED:
        if kw in text:
            score += 10
            reasons.append(kw)

    for kw in DEFAULT_NEGATIVE:
        if kw in text:
            score -= 20
            reasons.append(f"-{kw}")

    score = max(0, min(100, score))
    return score, sorted(set(reasons))


def get_client():
    load_env()
    api_id = os.environ.get('TG_API_ID')
    api_hash = os.environ.get('TG_API_HASH')
    if not api_id or not api_hash:
        raise SystemExit('Missing TG_API_ID or TG_API_HASH in .env')

    session_dir = os.path.join('out', 'session')
    os.makedirs(session_dir, exist_ok=True)
    session_path = os.path.join(session_dir, 'telegram_cleanup')

    return TelegramClient(session_path, int(api_id), api_hash)


def scan(limit=1000):
    os.makedirs('out', exist_ok=True)

    env = Environment(loader=FileSystemLoader('templates'))
    tpl = env.get_template('report.html.j2')

    candidates = []
    unavailable = []

    with get_client() as client:
        dialogs = client.get_dialogs(limit=limit)
        for d in dialogs:
            ent = d.entity
            title = getattr(ent, 'title', None) or getattr(ent, 'first_name', '') or 'Unknown'
            username = getattr(ent, 'username', '') or ''

            kind = 'unknown'
            if d.is_channel:
                kind = 'channel'
            elif d.is_group:
                kind = 'group'
            elif d.is_user:
                kind = 'user'

            # only channels and groups
            if kind not in ('channel','group'):
                continue

            try:
                score, reasons = compute_score(title, username)
                candidates.append(ChatCandidate(id=ent.id, title=title, username=username, kind=kind, score=score, reasons=reasons))
            except Exception as e:
                unavailable.append({'title': title, 'kind': kind, 'error': str(e)})

    # sort high score first
    items = sorted(candidates, key=lambda x: x.score, reverse=True)

    out_json = {
        'generated_at': datetime.utcnow().isoformat() + 'Z',
        'items': [x.__dict__ for x in items],
        'unavailable': unavailable,
    }

    with open(os.path.join('out', 'candidates.json'), 'w', encoding='utf-8') as f:
        json.dump(out_json, f, indent=2)

    html = tpl.render(generated_at=out_json['generated_at'], items=[x.__dict__ for x in items], unavailable=unavailable)
    with open(os.path.join('out', 'report.html'), 'w', encoding='utf-8') as f:
        f.write(html)

    print('Wrote out/report.html and out/candidates.json')


def apply(selection_path: str, dry_run=False, delay_s=3.0):
    sel = json.load(open(selection_path, 'r', encoding='utf-8'))
    ids = set(sel.get('ids') or [])
    if not ids:
        print('No ids selected.')
        return

    os.makedirs(os.path.join('out','runs'), exist_ok=True)
    runlog = {'ts': datetime.utcnow().isoformat()+'Z', 'dry_run': dry_run, 'left': [], 'failed': []}

    with get_client() as client:
        dialogs = client.get_dialogs(limit=5000)
        id_to_dialog = {d.entity.id: d for d in dialogs if getattr(d, 'entity', None)}

        for chat_id in ids:
            d = id_to_dialog.get(int(chat_id))
            if not d:
                runlog['failed'].append({'id': chat_id, 'error': 'not found in dialogs'})
                continue

            ent = d.entity
            title = getattr(ent, 'title', None) or getattr(ent, 'first_name', '') or str(chat_id)

            try:
                if dry_run:
                    runlog['left'].append({'id': chat_id, 'title': title, 'dry_run': True})
                    continue

                # LeaveChannelRequest works for channels; groups are also treated as channels in many cases.
                client(LeaveChannelRequest(ent))
                runlog['left'].append({'id': chat_id, 'title': title})
                time.sleep(delay_s)
            except (ChatAdminRequiredError, ChannelPrivateError, UserDeactivatedBanError) as e:
                runlog['failed'].append({'id': chat_id, 'title': title, 'error': str(e)})
            except Exception as e:
                runlog['failed'].append({'id': chat_id, 'title': title, 'error': str(e)})

    out_path = os.path.join('out','runs', f"run_{int(time.time())}.json")
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(runlog, f, indent=2)

    print('Done. Log:', out_path)


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='cmd', required=True)

    s = sub.add_parser('scan')
    s.add_argument('--limit', type=int, default=2000)

    a = sub.add_parser('apply')
    a.add_argument('selection')
    a.add_argument('--dry-run', action='store_true')
    a.add_argument('--delay', type=float, default=3.0)

    args = p.parse_args()

    if args.cmd == 'scan':
        scan(limit=args.limit)
    elif args.cmd == 'apply':
        apply(args.selection, dry_run=args.dry_run, delay_s=args.delay)


if __name__ == '__main__':
    main()
