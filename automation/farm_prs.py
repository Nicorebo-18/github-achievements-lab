"""Crea pull requests reales (rama + commit + PR + merge) sin revision.

Modos por PR:
  solo      -> commit del usuario, sin trailer de co-autor            (Pull Shark)
  pair      -> commit del co-autor + trailer "Co-authored-by: usuario" (Pair Extraordinaire)
  pair_rev  -> commit del usuario + trailer "Co-authored-by: co-autor" (Pair Extraordinaire)

Todos los PR se abren con el token del usuario, asi que el autor del PR y quien
fusiona es siempre la misma cuenta: eso cumple tambien el requisito de YOLO
(fusionar tu propio PR sin revision aprobada).
"""

import argparse
import time

from common import (
    COAUTHOR_EMAIL,
    COAUTHOR_LOGIN,
    COAUTHOR_NAME,
    OWNER,
    REPO,
    USER_EMAIL,
    USER_NAME,
    default_branch,
    jrequest,
    request,
    session_default,
)

NOTES = {
    "pair": (
        "Revision en pareja: cada PR de esta serie la escribe el co-autor y la "
        "revierte el titular del repositorio antes de fusionarla.",
        "## Revision en pareja\n\n"
        "Serie de pull requests escritas con coautoria explicita. Cada una de "
        "ellas:\n\n"
        "1. se abre desde una rama dedicada sobre la rama por defecto,\n"
        "2. incluye un commit con dos autores declarados mediante el trailer "
        "`Co-authored-by:`,\n"
        "3. se fusiona con estrategia `merge`, que conserva el commit original "
        "y su atribucion en el historial.\n\n"
        "El objetivo es comprobar que la atribucion de coautores sobrevive a la "
        "fusion y queda visible en el commit del historial permanente.",
    ),
    "pair_rev": (
        "Coautoria bidireccional: la nota la escribe el titular y el co-autor "
        "figura en el trailer del commit.",
        "## Coautoria bidireccional\n\n"
        "Este documento forma parte de la serie en la que el titular del "
        "repositorio escribe la nota y el co-autor aparece en el trailer "
        "`Co-authored-by:` del commit.\n\n"
        "Comprobamos que el commit aparece en el historial con ambos autores "
        "asociados a sus cuentas de GitHub, y que la pull request queda "
        "fusionada sin revision aprobada.",
    ),
    "solo": (
        "Pull request individual con una unica nota de documentacion.",
        "## Nota individual\n\n"
        "Registro de una pull request independiente, creada desde su propia rama "
        "y fusionada directamente sobre la rama por defecto.\n\n"
        "Cada entrada de esta serie anade un documento nuevo al directorio "
        "`docs/notes/`, de forma que el diff de cada pull request es pequeno, "
        "claro y facil de revisar.",
    ),
}


def create_pr(session, mode, index, base_sha, branch):
    note_body = NOTES[mode]
    path = f"docs/notes/{index:03d}-{mode}.md"
    content = f"{note_body[1]}\n\nSerie: {mode} · entrada {index:03d}\n"

    blob = jrequest(
        "POST",
        f"/repos/{OWNER}/{REPO}/git/blobs",
        session=session,
        json={"content": content, "encoding": "utf-8"},
    )
    base_commit = jrequest(
        "GET", f"/repos/{OWNER}/{REPO}/git/commits/{base_sha}", session=session
    )
    tree = jrequest(
        "POST",
        f"/repos/{OWNER}/{REPO}/git/trees",
        session=session,
        json={
            "base_tree": base_commit["tree"]["sha"],
            "tree": [
                {
                    "path": path,
                    "mode": "100644",
                    "type": "blob",
                    "sha": blob["sha"],
                }
            ],
        },
    )

    if mode == "pair":
        author = {"name": COAUTHOR_NAME, "email": COAUTHOR_EMAIL}
        message = (
            f"docs: anade la nota {index:03d} de la serie de coautoria\n\n"
            f"Co-authored-by: {USER_NAME} <{USER_EMAIL}>\n"
        )
    elif mode == "pair_rev":
        author = {"name": USER_NAME, "email": USER_EMAIL}
        message = (
            f"docs: anade la nota {index:03d} con coautoria registrada\n\n"
            f"Co-authored-by: {COAUTHOR_LOGIN} <{COAUTHOR_EMAIL}>\n"
        )
    else:
        author = {"name": USER_NAME, "email": USER_EMAIL}
        message = f"docs: anade la nota {index:03d} de la serie individual\n"

    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    commit = jrequest(
        "POST",
        f"/repos/{OWNER}/{REPO}/git/commits",
        session=session,
        json={
            "message": message,
            "tree": tree["sha"],
            "parents": [base_sha],
            "author": {**author, "date": now},
            "committer": {**author, "date": now},
        },
    )
    jrequest(
        "POST",
        f"/repos/{OWNER}/{REPO}/git/refs",
        session=session,
        json={"ref": f"refs/heads/{branch}", "sha": commit["sha"]},
    )
    return commit["sha"], path, message


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, required=True)
    ap.add_argument("--mode", choices=["solo", "pair", "pair_rev"], required=True)
    ap.add_argument("--delay", type=float, default=6.0)
    ap.add_argument("--prefix", default=None)
    args = ap.parse_args()

    s = session_default()
    branch_name, _ = default_branch(s)
    prefix = args.prefix or args.mode
    made = 0
    index = 0

    for i in range(args.count):
        index += 1
        branch = f"{prefix}-{index:03d}"
        base = jrequest(
            "GET", f"/repos/{OWNER}/{REPO}/git/ref/heads/{branch_name}", session=s
        )["object"]["sha"]
        try:
            sha, path, message = create_pr(s, args.mode, index, base, branch)
        except Exception as exc:  # noqa: BLE001
            print(f"[{index}/{args.count}] ERROR creando rama: {exc}")
            time.sleep(10)
            continue

        pr = jrequest(
            "POST",
            f"/repos/{OWNER}/{REPO}/pulls",
            session=s,
            json={
                "title": f"docs: nota {index:03d} de la serie {prefix}",
                "head": branch,
                "base": branch_name,
                "body": (
                    f"Anade `{path}` a la serie `{prefix}`.\n\n"
                    "Cambio pequeno y autocontenido, pensado para revisar el diff "
                    "de un vistazo y fusionar sin bloqueos.\n\n"
                    f"- Commit: `{sha[:7]}`\n"
                    f"- Rama: `{branch}` -> `{branch_name}`\n"
                ),
                "maintainer_can_modify": True,
            },
        )
        number = pr["number"]
        merge = request(
            "PUT",
            f"/repos/{OWNER}/{REPO}/pulls/{number}/merge",
            session=s,
            json={
                "merge_method": "merge",
                "commit_title": f"Merge pull request #{number} from {branch}",
                "commit_message": message.split("\n")[0],
            },
        )
        if merge.status_code == 200 and merge.json().get("merged"):
            made += 1
            print(f"[{index}/{args.count}] PR #{number} fusionado -> {pr['html_url']}")
        else:
            print(
                f"[{index}/{args.count}] PR #{number} NO fusionado: "
                f"{merge.status_code} {merge.text[:200]}"
            )
        time.sleep(args.delay)

    print(f"\nTotal PR fusionados en esta tanda: {made}")


if __name__ == "__main__":
    main()
