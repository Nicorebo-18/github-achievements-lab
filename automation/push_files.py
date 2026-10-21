"""Sube un directorio local al repositorio mediante una pull request y la fusiona."""

import argparse
import os
import time

from common import (
    OWNER,
    REPO,
    USER_EMAIL,
    USER_NAME,
    default_branch,
    jrequest,
    request,
    session_default,
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--local-dir", required=True)
    ap.add_argument("--target-dir", default="automation")
    ap.add_argument("--branch", default=None)
    ap.add_argument("--title", default="chore: anade el kit de automatizacion")
    ap.add_argument("--message", default=None)
    ap.add_argument("--coauthor", default=None, help="Nombre <email> del co-autor")
    args = ap.parse_args()

    s = session_default()
    branch_name, _ = default_branch(s)
    branch = args.branch or f"automation/{int(time.time())}"

    entries = []
    for root, _dirs, files in os.walk(args.local_dir):
        for name in sorted(files):
            if name.endswith(".pyc") or name.startswith("."):
                continue
            full = os.path.join(root, name)
            rel = os.path.relpath(full, args.local_dir)
            with open(full, encoding="utf-8") as fh:
                content = fh.read()
            blob = jrequest(
                "POST",
                f"/repos/{OWNER}/{REPO}/git/blobs",
                session=s,
                json={"content": content, "encoding": "utf-8"},
            )
            entries.append(
                {
                    "path": f"{args.target_dir}/{rel}",
                    "mode": "100644",
                    "type": "blob",
                    "sha": blob["sha"],
                }
            )
    if not entries:
        print("No hay archivos que subir")
        return

    base = jrequest(
        "GET", f"/repos/{OWNER}/{REPO}/git/ref/heads/{branch_name}", session=s
    )["object"]["sha"]
    base_commit = jrequest("GET", f"/repos/{OWNER}/{REPO}/git/commits/{base}", session=s)
    tree = jrequest(
        "POST",
        f"/repos/{OWNER}/{REPO}/git/trees",
        session=s,
        json={"base_tree": base_commit["tree"]["sha"], "tree": entries},
    )

    message = args.message or (
        f"{args.title}\n\n"
        "Kit de automatizacion usado para practicar el ciclo completo de "
        "contribucion: ramas, commits con coautoria, pull requests, fusiones "
        "y discusiones con respuesta aceptada."
    )
    if args.coauthor:
        message += f"\n\nCo-authored-by: {args.coauthor}\n"

    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    commit = jrequest(
        "POST",
        f"/repos/{OWNER}/{REPO}/git/commits",
        session=s,
        json={
            "message": message,
            "tree": tree["sha"],
            "parents": [base],
            "author": {"name": USER_NAME, "email": USER_EMAIL, "date": now},
            "committer": {"name": USER_NAME, "email": USER_EMAIL, "date": now},
        },
    )
    jrequest(
        "POST",
        f"/repos/{OWNER}/{REPO}/git/refs",
        session=s,
        json={"ref": f"refs/heads/{branch}", "sha": commit["sha"]},
    )

    pr = jrequest(
        "POST",
        f"/repos/{OWNER}/{REPO}/pulls",
        session=s,
        json={
            "title": args.title,
            "head": branch,
            "base": branch_name,
            "body": (
                f"Adds {len(entries)} file(s) under `{args.target_dir}/`.\n\n"
                "These scripts exercise the GitHub contribution loop end to end: "
                "creating branches, commits with explicit co-author trailers, "
                "pull requests, merges without review, issues and Discussions "
                "with accepted answers.\n\n"
                f"- Commit: `{commit['sha'][:7]}`\n"
                f"- Branch: `{branch}` -> `{branch_name}`\n"
            ),
        },
    )
    for attempt in range(5):
        merge = request(
            "PUT",
            f"/repos/{OWNER}/{REPO}/pulls/{pr['number']}/merge",
            session=s,
            json={
                "merge_method": "merge",
                "commit_title": f"Merge pull request #{pr['number']} from {branch}",
            },
        )
        if merge.status_code == 200 and merge.json().get("merged"):
            print(f"PR #{pr['number']} fusionado: {pr['html_url']}")
            print(f"Archivos subidos: {len(entries)}")
            return
        print(f"  merge intento {attempt + 1}: {merge.status_code} {merge.text[:120]}")
        time.sleep(6)
    print("No se pudo fusionar la pull request")


if __name__ == "__main__":
    main()
