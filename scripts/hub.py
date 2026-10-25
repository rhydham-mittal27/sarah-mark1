"""Aggregator: while the benchmark runs, merge all worker files in bench-data/runs/<run>/ into bench-data/summary.json every 30 s.
Single writer (this job), so the only conflicts are with workers pushing - handled by fetch/rebase retries.
python scripts/hub.py <run_id> <total_jobs>      (exits when every job is done/error, or after 5.5 h)"""
import glob
import json
import os
import subprocess
import sys
import time

run_id, total = sys.argv[1], int(sys.argv[2])
W = "bench-wt"


def sh(*a, check=True):
    return subprocess.run(a, cwd=W, capture_output=True, text=True, check=check)


subprocess.run(["git", "fetch", "origin", "bench-data"], check=True)
subprocess.run(["git", "worktree", "add", "-f", W, "origin/bench-data"], check=True)
sh("git", "checkout", "-B", "hub")
sh("git", "config", "user.email", "actions@github.com")
sh("git", "config", "user.name", "sarah-bench-hub")
started = time.time()


def collect():
    jobs = []
    for f in sorted(glob.glob(f"{W}/runs/{run_id}/*.json")):
        try:
            jobs.append(json.load(open(f)))
        except Exception:
            pass
    done = sum(1 for j in jobs if j.get("phase") == "done")
    return dict(run_id=run_id, total=total, started=int(started), updated=int(time.time()), done=done, jobs=jobs)


while True:
    sh("git", "fetch", "origin", "bench-data", check=False)
    sh("git", "reset", "--hard", "origin/bench-data", check=False)
    summ = collect()
    finished = sum(1 for j in summ["jobs"] if j.get("phase") in ("done", "error"))
    stopping = finished >= total or time.time() - started > 5.5 * 3600
    open(f"{W}/summary.json", "w").write(json.dumps(summ, separators=(",", ":")))
    sh("git", "add", "summary.json")
    if sh("git", "diff", "--cached", "--quiet", check=False).returncode != 0:
        sh("git", "commit", "-m", f"summary {summ['done']}/{total}")
        for _ in range(5):
            if sh("git", "push", "origin", "HEAD:bench-data", check=False).returncode == 0:
                break
            sh("git", "fetch", "origin", "bench-data", check=False)
            sh("git", "rebase", "origin/bench-data", check=False)
    if stopping:
        break
    time.sleep(30)
