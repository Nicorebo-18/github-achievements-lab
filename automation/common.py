import json
import os
import time
import urllib.parse

import requests

TOKEN_FILE = os.path.expanduser("~/.config/github-achievements/token")
API = "https://api.github.com"
OWNER = "Nicorebo-18"
USER_NAME = "Nicorebo-18"
USER_EMAIL = "nicorebo18@gmail.com"
COAUTHOR_LOGIN = "Icass1"
COAUTHOR_NAME = "Ignacio Casado"
COAUTHOR_EMAIL = "i.cassdolopez@gmail.com"


def token():
    with open(TOKEN_FILE) as fh:
        return fh.read().strip()


def session():
    s = requests.Session()
    s.headers.update(
        {
            "Authorization": f"Bearer {token()}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
    )
    return s


def request(method, path, session=None, **kwargs):
    s = session or session_default()
    url = path if path.startswith("http") else f"{API}{path}"
    for attempt in range(6):
        r = s.request(method, url, timeout=45, **kwargs)
        if r.status_code in (403, 429) and "rate limit" in r.text.lower():
            wait = int(r.headers.get("Retry-After") or 10) * (attempt + 1)
            print(f"    [rate limit] esperando {wait}s")
            time.sleep(wait)
            continue
        if r.status_code >= 500:
            time.sleep(5 * (attempt + 1))
            continue
        return r
    return r


def session_default():
    global _SESSION
    if _SESSION is None:
        _SESSION = session()
    return _SESSION


_SESSION = None


def jrequest(method, path, session=None, **kwargs):
    r = request(method, path, session=session, **kwargs)
    if r.status_code >= 400:
        raise RuntimeError(f"{method} {path} -> {r.status_code}: {r.text[:400]}")
    return r.json()


def graphql(query, variables=None, session=None):
    s = session or session_default()
    payload = {"query": query, "variables": variables or {}}
    for attempt in range(5):
        r = s.post(f"{API}/graphql", json=payload, timeout=45)
        if r.status_code != 200:
            raise RuntimeError(f"graphql http {r.status_code}: {r.text[:300]}")
        data = r.json()
        if "errors" in data:
            msg = "; ".join(e.get("message", "") for e in data["errors"])
            if "rate limit" in msg.lower() or "was submitted too quickly" in msg.lower():
                time.sleep(10 * (attempt + 1))
                continue
            raise RuntimeError(f"graphql error: {msg}")
        return data["data"]
    raise RuntimeError("graphql: demasiados reintentos")


def default_branch(session=None):
    repo = jrequest("GET", f"/repos/{OWNER}/{REPO}", session=session)
    return repo["default_branch"], repo["id"]


REPO = os.environ.get("TARGET_REPO", "github-achievements-lab")
