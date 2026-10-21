"""Verifica el estado de las entradas que generan insignias."""

import sys

from common import OWNER, REPO, graphql, jrequest, session_default


def main():
    s = session_default()
    print(f"=== {OWNER}/{REPO} ===\n")

    # Pulls
    pulls = []
    page = 1
    while True:
        batch = jrequest(
            "GET",
            f"/repos/{OWNER}/{REPO}/pulls?state=closed&per_page=100&page={page}",
            session=s,
        )
        if not batch:
            break
        pulls += [p for p in batch if p.get("merged_at")]
        if len(batch) < 100:
            break
        page += 1
    mine = [p for p in pulls if p["user"]["login"].lower() == OWNER.lower()]
    print(f"PRs mergeados por {OWNER}: {len(mine)}  (Pull Shark: base 2 / bronce 16)")

    # Commits con trailer de co-autor
    commits = jrequest(
        "GET", f"/repos/{OWNER}/{REPO}/commits?per_page=100", session=s
    )
    coauthored = []
    for c in commits:
        msg = c["commit"]["message"]
        if "Co-authored-by:" in msg:
            trailer = [
                l.strip()
                for l in msg.split("\n")
                if l.strip().lower().startswith("co-authored-by:")
            ]
            coauthored.append((c["sha"][:7], trailer, (c.get("author") or {}).get("login")))
    print(f"\nCommits con trailer Co-authored-by: {len(coauthored)}")
    for sha, trailer, login in coauthored[:3]:
        print(f"  {sha} (autor: {login}) -> {trailer}")
    print(f"  ... y {max(0, len(coauthored) - 3)} mas")

    # Issues cerrados
    issues = jrequest(
        "GET", f"/repos/{OWNER}/{REPO}/issues?state=closed&per_page=100", session=s
    )
    closed_fast = []
    for i in issues:
        if "pull_request" in i:
            continue
        if i.get("closed_at") and i.get("created_at"):
            from datetime import datetime

            c = datetime.fromisoformat(i["created_at"].replace("Z", "+00:00"))
            cl = datetime.fromisoformat(i["closed_at"].replace("Z", "+00:00"))
            secs = (cl - c).total_seconds()
            closed_fast.append((i["number"], round(secs)))
    print(f"\nIssues: {len(issues)} en total, cerrados: {len(closed_fast)}")
    for n, secs in closed_fast:
        print(f"  #{n} cerrado en {secs}s (<300s => Quickdraw)")

    # Discussions con respuesta aceptada
    repo = graphql(
        "query($o:String!,$n:String!){ repository(owner:$o,name:$n){ id "
        "discussions(first:100, orderBy:{field:CREATED_AT,direction:ASC}){ nodes{ "
        "number title answer{ id } comments(first:20){ nodes{ id isAnswer } } } } } }",
        {"o": OWNER, "n": REPO},
        session=s,
    )["repository"]
    answered = [d for d in repo["discussions"]["nodes"] if d.get("answer")]
    print(
        f"\nDiscussions con respuesta aceptada: {len(answered)}  "
        "(Galaxy Brain: base 2 / bronce 8)"
    )
    for d in answered:
        print(f"  #{d['number']} {d['title'][:55]}")

    # Reviews en los PRs (YOLO = ninguno)
    reviews = 0
    for p in mine[:5]:
        r = jrequest(
            "GET", f"/repos/{OWNER}/{REPO}/pulls/{p['number']}/reviews", session=s
        )
        reviews += len([x for x in r if x.get("state") == "APPROVED"])
    print(f"\nRevisiones aprobadoras en los 5 primeros PRs: {reviews} (YOLO ok)")


if __name__ == "__main__":
    main()
