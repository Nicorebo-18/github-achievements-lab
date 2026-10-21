# GitHub Achievements Lab

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
git clone https://github.com/Nicorebo-18/github-achievements-lab.git
cd github-achievements-lab
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

Coordinacion: Nicorebo-18 <nicorebo18@gmail.com>
Co-autores habitual: @Icass1 <i.cassdolopez@gmail.com>
