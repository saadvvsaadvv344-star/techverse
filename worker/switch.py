"""Auric's switch, for GitHub's free computers (the PC has the real one, switch.py).

* Saad's ON / OFF: the PC publishes it to TechVerse's database (meta/switch, readable by anyone); OFF stops the cloud
  too (checked every 5 minutes).
* Each GitHub run may last 6 hours: after AURIC_MINUTES (default 270) Auric stops starting new work, so the run ends
  cleanly and saves everything; the next run (every 6 hours) continues.
* No graphics card here, so there's nothing to share and no other jobs.
"""
import json
import os
import time
import urllib.request

URL = "https://firestore.googleapis.com/v1/projects/techverse-saad/databases/(default)/documents/meta/switch"
DEADLINE = time.time() + float(os.environ.get("AURIC_MINUTES", "270")) * 60
_last = [0.0, True]


def is_on():
    if time.time() > DEADLINE:
        return False                                  # this run's time is over: finish cleanly
    if time.time() - _last[0] > 300:
        try:
            with urllib.request.urlopen(URL, timeout=10) as r:
                f = json.loads(r.read()).get("fields", {})
            _last[1] = f.get("on", {}).get("booleanValue", True)
        except Exception:
            pass                                      # (no answer: keep the last known state)
        _last[0] = time.time()
    return _last[1]


def acquire_gpu(name):
    return is_on()


def release_gpu():
    pass


def jobs():
    return {}


def running():
    return {}


def _kill(procs):
    pass


def _set_job(name, **kw):
    pass
