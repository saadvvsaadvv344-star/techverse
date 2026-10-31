"""TechVerse's link to its own Firebase project (techverse-saad, separate from auric-saad).

The PC writes with the Firebase tool's own login (tools/node, signed in by Saad): the tool refreshes it, this file only
reads the short-lived access token from the tool's settings. No password or key is ever written in code or in the
database. Firestore is used through its REST API.

    t = TechCloud(); t.put("articles", "binary-numbers", {...}); t.get("articles", "binary-numbers"); t.list("queue")
"""
import json
import os
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT = "techverse-saad"
NODE = ROOT / "tools" / "node"
CONFIGSTORE = Path(os.environ.get("USERPROFILE", "~")).expanduser() / ".config" / "configstore" / "firebase-tools.json"
BASE = f"https://firestore.googleapis.com/v1/projects/{PROJECT}/databases/(default)/documents"
CLOUD = bool(os.environ.get("AURIC_CLOUD"))          # on GitHub's free computers (see .github/workflows/auric.yml)
FIREBASE_DIR = Path(os.environ.get("AURIC_FIREBASE_DIR") or ROOT / "TechVerse")


def flags():
    """Windows: no console window for child programs. (Elsewhere the option doesn't exist.)"""
    return {"creationflags": 0x08000000} if os.name == "nt" else {}


def firebase(*args, cwd=None, timeout=600):
    if CLOUD:                                        # the firebase tool installed with npm, signed in by the service account
        cmd, env = ["firebase", *args], dict(os.environ)
    else:
        cmd, env = [str(NODE / "firebase.cmd"), *args], {**os.environ, "PATH": str(NODE) + os.pathsep + os.environ.get("PATH", "")}
    r = subprocess.run(cmd, cwd=cwd or FIREBASE_DIR, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=env, timeout=timeout, **flags())
    return r.returncode, (r.stdout + r.stderr)


_sa = None


def access_token():
    """On the PC: the Firebase tool's current access token (the tool refreshes it). In the cloud: the service account
    given by GitHub's secret storage (GOOGLE_APPLICATION_CREDENTIALS)."""
    global _sa
    if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        import google.auth.transport.requests
        from google.oauth2 import service_account
        if _sa is None:
            _sa = service_account.Credentials.from_service_account_file(
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"], scopes=["https://www.googleapis.com/auth/cloud-platform"])
        if not _sa.valid:
            _sa.refresh(google.auth.transport.requests.Request())
        return _sa.token
    for attempt in range(2):
        try:
            tok = json.loads(CONFIGSTORE.read_text(encoding="utf-8"))["tokens"]
            if tok.get("expires_at", 0) / 1000 - time.time() > 300:
                return tok["access_token"]
        except (OSError, ValueError, KeyError):
            pass
        firebase("projects:list", "--json", timeout=120)          # the tool refreshes and saves its login
    raise RuntimeError("the Firebase tool isn't signed in: run tools\\node\\firebase.cmd login")


def call(method, url, body=None, timeout=30):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"Bearer {access_token()}", "Content-Type": "application/json", "x-goog-user-project": PROJECT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        if e.code == 404 and method == "GET":
            return None
        raise RuntimeError(f"{method} {url.split('/documents')[-1]}: HTTP {e.code} {e.read()[:300]!r}")


# ---- Firestore values <-> Python ----------------------------------------------------------------------------
def enc(v):
    if v is None:
        return {"nullValue": None}
    if isinstance(v, bool):
        return {"booleanValue": v}
    if isinstance(v, int):
        return {"integerValue": str(v)}
    if isinstance(v, float):
        return {"doubleValue": v}
    if isinstance(v, str):
        return {"stringValue": v}
    if isinstance(v, (list, tuple)):
        return {"arrayValue": {"values": [enc(x) for x in v]}}
    if isinstance(v, dict):
        return {"mapValue": {"fields": {k: enc(x) for k, x in v.items()}}}
    return {"stringValue": str(v)}


def dec(v):
    (kind, x), = v.items()
    if kind == "nullValue":
        return None
    if kind == "integerValue":
        return int(x)
    if kind == "arrayValue":
        return [dec(i) for i in x.get("values", [])]
    if kind == "mapValue":
        return {k: dec(i) for k, i in x.get("fields", {}).items()}
    return x


class TechCloud:
    def put(self, coll, doc_id, data):
        return call("PATCH", f"{BASE}/{coll}/{urllib.parse.quote(doc_id, safe='')}",
                    {"fields": {k: enc(v) for k, v in data.items()}})

    def get(self, coll, doc_id):
        d = call("GET", f"{BASE}/{coll}/{urllib.parse.quote(doc_id, safe='')}")
        return {k: dec(v) for k, v in d.get("fields", {}).items()} if d else None

    def delete(self, coll, doc_id):
        return call("DELETE", f"{BASE}/{coll}/{urllib.parse.quote(doc_id, safe='')}")

    def list(self, coll, page=300):
        out, token = {}, ""
        while True:
            d = call("GET", f"{BASE}/{coll}?pageSize={page}" + (f"&pageToken={token}" if token else "")) or {}
            for doc in d.get("documents", []):
                out[doc["name"].rsplit("/", 1)[-1]] = {k: dec(v) for k, v in doc.get("fields", {}).items()}
            token = d.get("nextPageToken")
            if not token:
                return out


def enable_api(service):
    """Turns on a Google API for the project (Firestore needs this once on a new project)."""
    return call("POST", f"https://serviceusage.googleapis.com/v1/projects/{PROJECT}/services/{service}:enable", {}, timeout=120)
