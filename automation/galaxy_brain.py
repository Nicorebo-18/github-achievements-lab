"""Galaxy Brain: crea discusiones en la categoria Q&A y marca la respuesta como aceptada.

Cada iteracion:
  1. crea una discusion en la categoria Q&A (que admite respuestas),
  2. publica una respuesta en esa discusion,
  3. marca esa respuesta como aceptada.
"""

import argparse
import time

from common import OWNER, REPO, graphql, session_default

QA = [
    (
        "Como squash-merge rompe la atribucion de coautores?",
        "He notado que al hacer squash de una rama con `Co-authored-by:` el "
        "atributo aparece como texto plano en el mensaje del commit en vez de "
        "como autor enlazado. Es el comportamiento normal?",
        "Si, es normal y conviene conocerlo: el squash genera un commit nuevo "
        "y reescribe el mensaje original.\n\n"
        "La solucion es usar la estrategia de merge (`git merge --no-ff` o el "
        "boton \"Create a merge commit\" de GitHub), que conserva los commits "
        "originales y con ellos sus trailers `Co-authored-by:`. Si prefieres "
        "squash, revisa el mensaje final y anade a mano los trailers "
        "necesarios antes de fusionar.",
    ),
    (
        "Cual es la diferencia entre un comentario y una revision aprobadora?",
        "En un repositorio con reglas de proteccion alguien dejo un comentario "
        "en mi pull request pero no llego a aprobar. GitHub leeria eso como "
        "revision valida para desbloquear el merge?",
        "No: un comentario de pull request es solo conversacion. Para que las "
        "reglas de proteccion se comprueban hacen falta revisiones con estado "
        "`APPROVED` y, si la rama esta protegida, que la aprobacion venga de "
        "alguien con permiso de escritura.\n\n"
        "Puedes comprobarlo en la pestana \"Files changed\" -> \"Review "
        "history\": ahi se ve quien ha aprobado y quien solo ha comentado.",
    ),
    (
        "Por que GitHub no me muestra las estrellas de mi propio repositorio?",
        "He marcado con estrella un repositorio mio y la insignia "
        "Starstruck sigue sin aparecer. Es un error de mi cuenta?",
        "Es el comportamiento previsto: la estrella que te pones a ti mismo no "
        "cuenta para el logro. Starstruck se calcula con las estrellas que "
        "reciben tus repositorios de otras cuentas.\n\n"
        "La via legitima es compartir el repositorio y conseguir estrellas "
        "reales de otras personas. Comprueba ademas que el repositorio sea "
        "publico y que las contribuciones privadas esten visibles en tu "
        "perfil.",
    ),
    (
        "Como creo una rama y una pull request solo con la API?",
        "Quiero automatizar la creacion de una rama, un commit y su pull "
        "request sin usar la interfaz web. Cual es la secuencia minima de "
        "llamadas?",
        "La secuencia es: blob, tree, commit, ref y pull request.\n\n"
        "1. `POST /repos/{owner}/{repo}/git/blobs` con el contenido del "
        "archivo.\n"
        "2. `POST /repos/{owner}/{repo}/git/trees` usando como `base_tree` el "
        "arbol del commit base, para heredar el resto de archivos.\n"
        "3. `POST /repos/{owner}/{repo}/git/commits` con el arbol, el padre y "
        "el mensaje (aqui van los trailers `Co-authored-by:`).\n"
        "4. `POST /repos/{owner}/{repo}/git/refs` para publicar la rama.\n"
        "5. `POST /repos/{owner}/{repo}/pulls` para abrir la pull request.\n\n"
        "Un detalle importante: en el paso 3 conviene enviar explicitamente "
        "`author` y `committer` con el nombre y el correo de la cuenta, para "
        "que GitHub atribuya el commit a la persona correcta.",
    ),
    (
        "Que evento marca una insignia en el perfil de GitHub?",
        "Hay insiders, stars, un merge... Que actividad concreta hace que "
        "GitHub encienda la insignia en el perfil?",
        "Cada insignia tiene su propio evento de activacion:\n\n"
        "- **Pull Shark**: una pull request tuya se fusiona.\n"
        "- **Quickdraw**: cierras una incidencia o una pull request en menos de "
        "cinco minutos desde que la abriste.\n"
        "- **YOLO**: fusionas tu propia pull request sin revision aprobadora.\n"
        "- **Pair Extraordinaire**: un commit con dos autores, fusionado en una "
        "pull request.\n"
        "- **Galaxy Brain**: una respuesta marcada como aceptada en una "
        "discusion.\n"
        "- **Starstruck**: un repositorio tuyo alcanza 16 estrellas.\n\n"
        "Los eventos se procesan de forma asincrona: pueden tardar horas, "
        "normalmente hasta 24, en reflejarse en el perfil.",
    ),
    (
        "Como acepto una respuesta en una discusion?",
        "He creado una categoria Q&A en mi repositorio pero no encuentro la "
        "opcion de marcar la respuesta como aceptada.",
        "La opcion aparece en la propia respuesta, no en la discusion. Abre la "
        "discusion, expande la respuesta y busca el icono de \"Aceptar "
        "respuesta\" en la parte superior de la misma.\n\n"
        "Solo el autor de la discusion puede aceptar una respuesta, la "
        "categoria debe admitir respuestas (Q&A) y la respuesta debe existir "
        "como comentario de la discusion. Desde la API se corresponde con las "
        "mutaciones `addDiscussionComment` y `markDiscussionCommentAsAnswer`.",
    ),
    (
        "Que cuenta como repositorio propio para Starstruck?",
        "Si creo una organizacion y el repositorio pasa a pertenece a ella, "
        "siguen contando las estrellas que ya tenia?",
        "Las estrellas se cuentan sobre repositorios que tu cuenta ha creado o "
        "administra. Al transferir un repositorio a una organizacion conviene "
        "comprobar como queda la insignia, porque la accion de creacion "
        "original deja de estar asociada a tu cuenta personal.\n\n"
        "En la practica, lo que se vigila es el numero de estrellas publico "
        "del repositorio: 16 para el primer nivel, 128, 512 y 4096 para los "
        "siguientes.",
    ),
    (
        "Es normal que las insignias tarden un dia en aparecer?",
        "He fusionado varias pull requests y los graficos de contribucion ya "
        "los muestran, pero las insignias siguen apagadas.",
        "Si, es lo habitual. Los graficos de contribucion se actualizan casi "
        "en tiempo real, mientras que las insignias las calcula un proceso "
        "diferido que puede tardar horas o hasta un dia.\n\n"
        "Si tras 24-48 horas sigue sin aparecer, revisa estos puntos: que las "
        "contribuciones privadas sean visibles en tu perfil, que la cuenta "
        "tenga la opcion de insignias activada, que la pull request figure "
        "como fusionada y que los correos de coautor esten verificados en las "
        "cuentas correspondientes.",
    ),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=8)
    ap.add_argument("--delay", type=float, default=4.0)
    ap.add_argument("--start", type=int, default=0)
    args = ap.parse_args()

    s = session_default()
    repo = graphql(
        "query($o:String!,$n:String!){ repository(owner:$o,name:$n){ id "
        "discussionCategories(first:25){ nodes{ id name isAnswerable } } } }",
        {"o": OWNER, "n": REPO},
        session=s,
    )["repository"]
    repo_id = repo["id"]
    qa = next(c for c in repo["discussionCategories"]["nodes"] if c["isAnswerable"])
    print(f"Repositorio {repo_id} · categoria '{qa['name']}' ({qa['id']})")

    done = 0
    for i, (title, question, answer) in enumerate(QA[args.start : args.start + args.count], start=args.start + 1):
        disc = graphql(
            "mutation($repoId:ID!,$catId:ID!,$title:String!,$body:String!){ "
            "createDiscussion(input:{repositoryId:$repoId,categoryId:$catId,"
            "title:$title,body:$body}){ discussion{ id number url } } }",
            {
                "repoId": repo_id,
                "catId": qa["id"],
                "title": title,
                "body": question,
            },
            session=s,
        )["createDiscussion"]["discussion"]
        print(f"[{i}/{args.count}] Discusion #{disc['number']}: {disc['url']}")

        comment = graphql(
            "mutation($discId:ID!,$body:String!){ addDiscussionComment("
            "input:{discussionId:$discId,body:$body}){ comment{ id } } }",
            {"discId": disc["id"], "body": answer},
            session=s,
        )["addDiscussionComment"]["comment"]

        graphql(
            "mutation($id:ID!){ markDiscussionCommentAsAnswer(input:{id:$id}){ "
            "discussion{ id } } }",
            {"id": comment["id"]},
            session=s,
        )
        done += 1
        print(f"    respuesta marcada como aceptada ({comment['id'][-8:]})")
        time.sleep(args.delay)

    print(f"\nDiscusiones con respuesta aceptada: {done}")


if __name__ == "__main__":
    main()
