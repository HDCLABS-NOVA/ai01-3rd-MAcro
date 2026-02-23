import json
import csv
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[3]
MODEL = ROOT / 'model'
BROWSER_ROOT = MODEL / 'data' / 'raw' / 'browser'
SERVER_ROOT = MODEL / 'data' / 'raw' / 'server'
OUT_JSON = MODEL / 'data' / 'prepared' / 'joined_logs.json'
OUT_CSV = MODEL / 'data' / 'prepared' / 'joined_logs.csv'


def load_json(path: Path):
    with path.open('r', encoding='utf-8') as f:
        return json.load(f)


def index_server_logs():
    by_flow = defaultdict(list)
    by_session = defaultdict(list)

    for p in SERVER_ROOT.rglob('*.json'):
        try:
            data = load_json(p)
        except Exception:
            continue
        meta = data.get('metadata', {})
        flow_id = meta.get('flow_id') or ''
        session_id = meta.get('session_id') or ''
        if flow_id:
            by_flow[flow_id].append((p, data))
        if session_id:
            by_session[session_id].append((p, data))
    return by_flow, by_session


def summarize_browser(data):
    meta = data.get('metadata', {})
    return {
        'performance_id': meta.get('performance_id', ''),
        'performance_title': meta.get('performance_title', ''),
        'selected_date': meta.get('selected_date', ''),
        'selected_time': meta.get('selected_time', ''),
        'booking_id': meta.get('booking_id', ''),
        'completion_status': meta.get('completion_status', ''),
        'total_duration_ms': meta.get('total_duration_ms', 0),
        'bot_type': meta.get('bot_type', ''),
    }


def summarize_server(data):
    meta = data.get('metadata', {})
    req = data.get('request', {})
    res = data.get('response', {})
    ident = data.get('identity', {})
    client = data.get('client_fingerprint', {})
    return {
        'request_id': meta.get('request_id', ''),
        'received_epoch_ms': meta.get('received_epoch_ms', 0),
        'endpoint': req.get('endpoint', ''),
        'method': req.get('method', ''),
        'status_code': res.get('status_code', 0),
        'latency_ms': res.get('latency_ms', 0),
        'body_size_bytes': req.get('body_size_bytes', 0),
        'ip_hash': ident.get('ip_hash', ''),
        'ip_raw': ident.get('ip_raw', ''),
        'user_agent_hash': client.get('user_agent_hash', ''),
        'referer': req.get('headers_whitelist', {}).get('referer', ''),
    }


def main():
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    by_flow, by_session = index_server_logs()

    joined = []
    rows = []

    for p in BROWSER_ROOT.rglob('*.json'):
        try:
            data = load_json(p)
        except Exception:
            continue

        meta = data.get('metadata', {})
        flow_id = meta.get('flow_id') or ''
        session_id = meta.get('session_id') or ''

        server_matches = []
        if flow_id and flow_id in by_flow:
            server_matches = by_flow[flow_id]
        elif session_id and session_id in by_session:
            server_matches = by_session[session_id]

        server_paths = [str(sp[0]) for sp in server_matches]
        server_summaries = [summarize_server(sp[1]) for sp in server_matches]

        record = {
            'browser_log': str(p),
            'flow_id': flow_id,
            'session_id': session_id,
            'browser_summary': summarize_browser(data),
            'server_logs': server_paths,
            'server_summaries': server_summaries,
        }
        joined.append(record)

        # CSV: use first server summary if available
        server_first = server_summaries[0] if server_summaries else {}
        rows.append({
            'browser_log': str(p),
            'flow_id': flow_id,
            'session_id': session_id,
            'performance_id': record['browser_summary'].get('performance_id', ''),
            'booking_id': record['browser_summary'].get('booking_id', ''),
            'completion_status': record['browser_summary'].get('completion_status', ''),
            'total_duration_ms': record['browser_summary'].get('total_duration_ms', 0),
            'server_request_id': server_first.get('request_id', ''),
            'server_status_code': server_first.get('status_code', ''),
            'server_latency_ms': server_first.get('latency_ms', ''),
            'server_body_size_bytes': server_first.get('body_size_bytes', ''),
        })

    OUT_JSON.write_text(json.dumps(joined, ensure_ascii=False, indent=2), encoding='utf-8')

    with OUT_CSV.open('w', newline='', encoding='utf-8') as f:
        fieldnames = [
            'browser_log',
            'flow_id',
            'session_id',
            'performance_id',
            'booking_id',
            'completion_status',
            'total_duration_ms',
            'server_request_id',
            'server_status_code',
            'server_latency_ms',
            'server_body_size_bytes',
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    print('Wrote:', OUT_JSON)
    print('Wrote:', OUT_CSV)


if __name__ == '__main__':
    main()
