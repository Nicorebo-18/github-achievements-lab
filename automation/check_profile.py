"""Lee la pestana de logros del perfil publico y muestra que insignias hay."""

import re
import sys
import time

import requests

PROFILE = sys.argv[1] if len(sys.argv) > 1 else "Nicorebo-18"
URL = f"https://github.com/{PROFILE}?tab=achievements"

LABELS = {
    "quickdraw": "Quickdraw",
    "pull-shark": "Pull Shark",
    "galaxy-brain": "Galaxy Brain",
    "starstruck": "Starstruck",
    "pair-extraordinaire": "Pair Extraordinaire",
    "yolo": "YOLO",
    "public-sponsor": "Public Sponsor",
    "arctic-code-vault-contributor": "Arctic Code Vault",
    "mars-2020-contributor": "Mars 2020",
}


def main():
    r = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    r.raise_for_status()
    html = r.text

    found = []
    for m in re.finditer(r'aria-label="([^"]*?) details"', html):
        label = m.group(1)
        slug = None
        for s in LABELS:
            if s in label.lower().replace(" ", "-"):
                slug = s
                break
        if slug and slug not in [f[0] for f in found]:
            found.append((slug, label))

    # porcentaje de progreso de cada insignia (GitHub dibuja un anillo con %)
    pcts = re.findall(r'([\d.]+)%', html)

    print(f"Perfil: https://github.com/{PROFILE}?tab=achievements")
    print(f"Insignias detectadas: {len(found)}\n")
    for slug, label in found:
        print(f"  [OK] {LABELS.get(slug, slug)}  ({label})")
    faltantes = [v for k, v in LABELS.items() if k not in [f[0] for f in found]]
    if faltantes:
        print("\nTodavia no visibles (pueden tardar hasta 24 h en procesarse):")
        for f in faltantes:
            print(f"  [ ] {f}")
    print(f"\nPorcentajes de progreso detectados en la pagina: {sorted(set(pcts))}")


if __name__ == "__main__":
    main()
