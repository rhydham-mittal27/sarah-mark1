"""Runs next to a benchmark worker: every INTERVAL seconds, upload its progress file (if it changed) to bench-data/runs/<run>/<name>.json.
python scripts/uploader.py <progress.json> <run_id> <job_name> <meta_json>     (stops when <progress.json>.stop exists)"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ghdata  # noqa: E402

path, run_id, name, meta = sys.argv[1], sys.argv[2], sys.argv[3], json.loads(sys.argv[4])
INTERVAL = 45
last = None
while True:
    stopping = os.path.exists(path + ".stop")
    try:
        cur = json.load(open(path)) if os.path.exists(path) else dict(phase="starting")
    except Exception:
        cur = None
    if cur is not None:
        blob = json.dumps(dict(name=name, **meta, **cur, t=int(time.time())), separators=(",", ":"))
        key = json.dumps({k: v for k, v in cur.items() if k != "curve"})
        if key != last:
            if ghdata.put(f"runs/{run_id}/{name}.json", blob):
                last = key
    if stopping:
        break
    time.sleep(INTERVAL)
