"""Quickdraw: abre un issue y lo cierra en menos de 5 minutos."""

import time

from common import OWNER, REPO, jrequest, session_default


def main():
    s = session_default()
    body = (
        "Autocomprobacion de la API de GitHub.\n\n"
        "Este issue se crea y se cierra de inmediato para comprobar el tiempo de "
        "respuesta de la API y la gestion de incidencias del repositorio. Si lo "
        "ves abierto, esta parte del flujo automatico no funciono.\n"
    )
    issue = jrequest(
        "POST",
        f"/repos/{OWNER}/{REPO}/issues",
        session=s,
        json={
            "title": "Comprobacion de apertura y cierre de incidencias",
            "body": body,
            "labels": [],
        },
    )
    number = issue["number"]
    print(f"Issue #{number} abierto: {issue['html_url']}")

    time.sleep(2)

    closed = jrequest(
        "PATCH",
        f"/repos/{OWNER}/{REPO}/issues/{number}",
        session=s,
        json={"state": "closed", "state_reason": "completed"},
    )
    print(f"Issue #{number} cerrado ({closed['state']}) a las {closed['closed_at']}")
    print("Quickdraw: la insignia deberia aparecer en el perfil en las proximas 24 h.")


if __name__ == "__main__":
    main()
