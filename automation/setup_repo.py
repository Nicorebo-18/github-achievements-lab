"""Crea el repo sandbox, habilita Discussions y escribe un README con contenido real."""

import json
import os
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
    graphql,
    jrequest,
    request,
    session_default,
)

README = """# GitHub Achievements Lab

Sandbox publico para practicar y automatizar flujos de contribucion de GitHub
en condiciones realistas: ramas, pull requests, merges, revisiones y Discussions.

## Por que existe

Este repositorio existe como banco de pruebas. Cada pull request aqui sigue el
mismo ciclo que una real:

1. se crea una rama a partir de la rama por defecto,
2. se anade un commit con autor y co-autor explicitos,
3. se abre una pull request con una descripcion del cambio,
4. se fusiona revisando el diff.

## Como colaborar

```bash
git clone https://github.com/{owner}/{repo}.git
cd {repo}
git switch -c feature/mi-cambio
# ... editar docs/ ...
git commit -m "docs: anade notas de contribucion"
git push -u origin feature/mi-cambio
```

Despues abre la pull request desde GitHub. Si el cambio es pequeno, un unico
commit por pull request mantiene el historial legible.

## Discussion categories

Este repo usa la categoria **Q&A** para preguntas con respuesta aceptada, y
**General** para el resto de conversaciones.

## Contacto

Coordinacion: {user_name} <{user_email}>
Co-autores habitual: @{coauthor} <{coauthor_email}>
""".format(
    owner=OWNER,
    repo=REPO,
    user_name=USER_NAME,
    user_email=USER_EMAIL,
    coauthor=COAUTHOR_LOGIN,
    coauthor_email=COAUTHOR_EMAIL,
)


def main():
    s = session_default()

    # 1. Crear el repo (necesita el scope repo de un classic PAT)
    r = request(
        "POST",
        "/user/repos",
        session=s,
        json={
            "name": REPO,
            "description": "Sandbox for practising GitHub contribution workflows: branches, pull requests, reviews and Discussions.",
            "private": False,
            "auto_init": True,
            "has_issues": True,
            "has_wiki": False,
        },
    )
    if r.status_code == 201:
        print(f"Repo creado: {r.json()['html_url']}")
    elif r.status_code == 422:
        print(f"Repo ya existe: {REPO}")
    else:
        print(f"ERROR creando repo: {r.status_code} {r.text[:300]}")
        raise SystemExit(1)

    # 2. Habilitar Discussions
    time.sleep(1)
    branch, repo_id = default_branch(s)
    try:
        graphql(
            """
            mutation($repoId: ID!) {
              updateRepository(input: {repositoryId: $repoId, hasDiscussionsEnabled: true}) {
                repository { id hasDiscussionsEnabled }
              }
            }
            """,
            {"repoId": repo_id},
            session=s,
        )
        print("Discussions habilitadas")
    except Exception as exc:  # noqa: BLE001
        print(f"Aviso: no se pudo activar Discussions por API: {exc}")

    # 3. Topics
    request(
        "PUT",
        f"/repos/{OWNER}/{REPO}/topics",
        session=s,
        json={"names": ["github-achievements", "sandbox", "learning", "git-workflow"]},
    )

    # 4. Subir el README con contenido real (commit propio, atribuido a la cuenta)
    blob = jrequest(
        "POST",
        f"/repos/{OWNER}/{REPO}/git/blobs",
        session=s,
        json={"content": README, "encoding": "utf-8"},
    )
    base = jrequest(
        "GET", f"/repos/{OWNER}/{REPO}/git/ref/heads/{branch}", session=s
    )["object"]["sha"]
    base_commit = jrequest("GET", f"/repos/{OWNER}/{REPO}/git/commits/{base}", session=s)
    tree = jrequest(
        "POST",
        f"/repos/{OWNER}/{REPO}/git/trees",
        session=s,
        json={
            "base_tree": base_commit["tree"]["sha"],
            "tree": [
                {
                    "path": "README.md",
                    "mode": "100644",
                    "type": "blob",
                    "sha": blob["sha"],
                }
            ],
        },
    )
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    commit = jrequest(
        "POST",
        f"/repos/{OWNER}/{REPO}/git/commits",
        session=s,
        json={
            "message": "docs: describe the contribution workflow of this sandbox",
            "tree": tree["sha"],
            "parents": [base],
            "author": {"name": USER_NAME, "email": USER_EMAIL, "date": now},
            "committer": {"name": USER_NAME, "email": USER_EMAIL, "date": now},
        },
    )
    jrequest(
        "PATCH",
        f"/repos/{OWNER}/{REPO}/git/refs/heads/{branch}",
        session=s,
        json={"sha": commit["sha"], "force": False},
    )
    print(f"README subido (commit {commit['sha'][:7]})")
    print(f"Repo listo: https://github.com/{OWNER}/{REPO}")


if __name__ == "__main__":
    main()
