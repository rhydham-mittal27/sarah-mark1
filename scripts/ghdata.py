"""Tiny helper: write a file to the `bench-data` branch through the GitHub contents API (per-file, retried on conflicts)."""
import base64
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request

REPO = os.environ.get("GITHUB_REPOSITORY", "")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
BRANCH = "bench-data"


def _req(method, url, body=None):
    r = urllib.request.Request(url, method=method, data=json.dumps(body).encode() if body is not None else None,
                               headers={"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json", "User-Agent": "sarah-bench"})
    with urllib.request.urlopen(r, timeout=30) as f:
        return json.loads(f.read() or b"{}")


def put(path, text, message="progress"):
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    for attempt in range(8):
        try:
            sha = None
            try:
                sha = _req("GET", f"{url}?ref={BRANCH}").get("sha")
            except urllib.error.HTTPError as e:
                if e.code != 404:
                    raise
            body = dict(message=message, content=base64.b64encode(text.encode()).decode(), branch=BRANCH)
            if sha:
                body["sha"] = sha
            _req("PUT", url, body)
            return True
        except Exception as e:                                   # 409/422 conflicts with other workers: back off and retry
            time.sleep(1.5 + random.random() * 3 * (attempt + 1))
    print("ghdata.put failed for", path, file=sys.stderr)
    return False


if __name__ == "__main__":              # python ghdata.py <local file> <remote path>
    ok = put(sys.argv[2], open(sys.argv[1], encoding="utf-8").read(), message=f"update {sys.argv[2]}")
    sys.exit(0 if ok else 1)
