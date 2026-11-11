#!/usr/bin/env python3
"""Build the Mis Libros Vivos site into dist/.

    python build.py          build the site
    python build.py --serve  build, then preview at http://localhost:8000

Each book is a folder under libros/ holding libro.toml (metadata),
descripcion.md, padres.md and portada.jpg. Site-wide links live in
sitio.toml. A book whose libro.toml says `publicado = false` is skipped.
"""
from __future__ import annotations

import html
import shutil
import sys
import tomllib
from pathlib import Path

import markdown

RAIZ = Path(__file__).resolve().parent
DIST = RAIZ / "dist"
PENDIENTE = "#pendiente"

avisos: list[str] = []


def e(texto) -> str:
    return html.escape(str(texto), quote=True)


def leer_md(ruta: Path) -> str:
    if not ruta.exists():
        return ""
    return markdown.markdown(ruta.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- datos


def cargar_sitio() -> dict:
    with open(RAIZ / "sitio.toml", "rb") as f:
        sitio = tomllib.load(f)
    enlaces = sitio.setdefault("enlaces", {})
    for clave in ("kit_form_id", "kofi", "tally", "licencia"):
        if not enlaces.get(clave):
            avisos.append(f"sitio.toml: enlaces.{clave} está vacío")
    return sitio


def cargar_libros() -> list[dict]:
    libros = []
    for carpeta in sorted((RAIZ / "libros").iterdir()):
        meta = carpeta / "libro.toml"
        if not meta.exists():
            continue
        with open(meta, "rb") as f:
            libro = tomllib.load(f)
        if libro.get("publicado", True) is False:
            continue
        libro["slug"] = carpeta.name
        libro["carpeta"] = carpeta
        libro["descripcion_html"] = leer_md(carpeta / "descripcion.md")
        libro["padres_html"] = leer_md(carpeta / "padres.md")
        libro["disponible"] = bool(libro.get("release") and libro.get("archivo"))
        if not (carpeta / "portada.jpg").exists():
            avisos.append(f"{carpeta.name}: falta portada.jpg")
        if not libro["padres_html"]:
            avisos.append(f"{carpeta.name}: falta padres.md")
        libros.append(libro)
    libros.sort(key=lambda l: (l.get("orden", 999), l["titulo"]))
    return libros


# ---------------------------------------------------------------- piezas


def enlace(url: str) -> tuple[str, str]:
    """href and extra class for a link that may not exist yet."""
    return (url, "") if url else (PENDIENTE, " pendiente")


def url_descarga(sitio: dict, libro: dict) -> str:
    return (
        f"https://github.com/{sitio['repo']}/releases/download/"
        f"{libro['release']}/{libro['archivo']}"
    )


def url_correccion(sitio: dict, libro: dict | None = None) -> str:
    base = sitio["enlaces"].get("tally", "")
    if not base:
        return ""
    if libro is None:
        return base
    return f"{base}?libro={libro['slug']}&edicion={libro.get('edicion', 'beta')}"


def estado_libro(libro: dict) -> tuple[str, str]:
    if not libro["disponible"]:
        return "Próximamente", "sello-pronto"
    if libro.get("edicion") == "revisada":
        return "Edición revisada", "sello-revisada"
    return "Edición beta", "sello-beta"


def form_suscribir(sitio: dict, n: int) -> str:
    form_id = sitio["enlaces"].get("kit_form_id", "")
    accion = f"https://app.kit.com/forms/{e(form_id)}/subscriptions" if form_id else PENDIENTE
    clase = "" if form_id else " pendiente"
    return f"""
<form class="suscribir{clase}" action="{accion}" method="post">
  <label for="correo-{n}">Su correo electrónico</label>
  <div class="suscribir-fila">
    <input type="email" id="correo-{n}" name="email_address" required
           autocomplete="email" placeholder="nombre@ejemplo.com">
    <button type="submit" class="boton">Avisarme</button>
  </div>
  <p class="nota">Un correo cuando salga un libro nuevo, como mucho uno al mes.
  Puede darse de baja cuando quiera.</p>
</form>"""


def banda_suscribir(sitio: dict, n: int) -> str:
    return f"""
<section class="banda" aria-labelledby="suscribir-t-{n}">
  <div class="contenedor banda-fila">
    <div>
      <h2 id="suscribir-t-{n}">¿Le aviso cuando salga el próximo libro?</h2>
      <p>Publico al menos un libro nuevo cada mes. Los suscriptores también
      me ayudan a encontrar errores en las ediciones beta.</p>
    </div>
    {form_suscribir(sitio, n)}
  </div>
</section>"""


def pagina(
    sitio: dict,
    *,
    titulo: str,
    descripcion: str,
    cuerpo: str,
    raiz: str,
    ruta: str,
    imagen: str = "",
    tipo: str = "website",
) -> str:
    nombre = sitio["nombre"]
    base = sitio["url"].rstrip("/")
    titulo_completo = nombre if titulo == nombre else f"{titulo} · {nombre}"
    if not imagen and (RAIZ / "estatico" / "compartir.jpg").exists():
        imagen = "compartir.jpg"
    og_imagen = (
        f'<meta property="og:image" content="{base}/{imagen}">\n' if imagen else ""
    )
    gc = sitio["enlaces"].get("goatcounter", "")
    analitica = (
        f'<script data-goatcounter="{e(gc)}" async src="//gc.zgo.at/count.js"></script>'
        if gc
        else ""
    )
    kofi, kofi_cls = enlace(sitio["enlaces"].get("kofi", ""))
    corr, corr_cls = enlace(url_correccion(sitio))
    lic_url = sitio["enlaces"].get("licencia", "")
    lic_nombre = sitio["enlaces"].get("licencia_nombre", "")
    licencia = (
        f'Las traducciones se publican bajo la licencia <a href="{e(lic_url)}" rel="license">{e(lic_nombre)}</a>.'
        if lic_url
        else '<span class="pendiente">Licencia pendiente.</span>'
    )
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(titulo_completo)}</title>
<meta name="description" content="{e(descripcion)}">
<link rel="canonical" href="{base}/{ruta}">
<meta property="og:site_name" content="{e(nombre)}">
<meta property="og:locale" content="es_LA">
<meta property="og:type" content="{tipo}">
<meta property="og:title" content="{e(titulo)}">
<meta property="og:description" content="{e(descripcion)}">
<meta property="og:url" content="{base}/{ruta}">
{og_imagen}<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="{raiz}favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="{raiz}estilo.css">
{analitica}
</head>
<body>
<a class="saltar" href="#contenido">Saltar al contenido</a>
<header class="cabecera">
  <div class="contenedor cabecera-fila">
    <a class="marca" href="{raiz}">Mis <b>Libros Vivos</b></a>
    <nav aria-label="Principal">
      <a href="{raiz}#libros">Libros</a>
      <a href="{raiz}acerca/">Acerca</a>
      <a class="nav-apoyar{kofi_cls}" href="{e(kofi)}">Apoyar</a>
    </nav>
  </div>
</header>
<main id="contenido">
{cuerpo}
</main>
<footer class="pie">
  <div class="contenedor pie-fila">
    <div>
      <p class="marca">Mis <b>Libros Vivos</b></p>
      <p>Traducciones gratuitas de libros clásicos, para leer en familia.</p>
    </div>
    <ul class="pie-enlaces">
      <li><a href="{raiz}acerca/">Acerca de estas traducciones</a></li>
      <li><a class="{corr_cls.strip()}" href="{e(corr)}">Enviar una corrección</a></li>
      <li><a class="{kofi_cls.strip()}" href="{e(kofi)}">Apoyar con un donativo</a></li>
      <li><a href="mailto:{e(sitio['correo'])}">{e(sitio['correo'])}</a></li>
    </ul>
  </div>
  <div class="contenedor pie-legal">
    <p>{licencia} Las obras originales son de dominio público.</p>
  </div>
</footer>
</body>
</html>
"""


# ---------------------------------------------------------------- páginas


def tarjeta(libro: dict, raiz: str) -> str:
    estado, clase = estado_libro(libro)
    slug = libro["slug"]
    return f"""
<li class="tarjeta">
  <a href="{raiz}libros/{slug}/">
    <img src="{raiz}libros/{slug}/portada.jpg" alt="" loading="lazy">
    <span class="sello {clase}">{estado}</span>
    <span class="tarjeta-titulo">{e(libro['titulo'])}</span>
    <span class="tarjeta-autor">{e(libro['autor'])}</span>
  </a>
</li>"""


def pagina_inicio(sitio: dict, libros: list[dict]) -> str:
    tarjetas = "".join(tarjeta(l, "./") for l in libros)
    cuerpo = f"""
<section class="portada-sitio">
  <div class="contenedor">
    <h1>Libros vivos para leer en familia, en español y gratis</h1>
    <p class="entrada">Traducciones completas de libros clásicos —cuentos,
    historia, biografías y ciencia— para familias que educan en casa.
    Descárguelos, léalos en voz alta y compártalos.</p>
    <p class="cita">«Libros vivos», como los llamaba Charlotte Mason: libros
    escritos por alguien que conoce y ama su tema, y que lo cuenta de modo que
    el lector también llegue a amarlo.</p>
  </div>
</section>

<section class="contenedor seccion" id="libros" aria-labelledby="libros-t">
  <h2 id="libros-t">Los libros</h2>
  <ul class="rejilla">{tarjetas}
  </ul>
</section>

<section class="contenedor seccion como" aria-labelledby="como-t">
  <h2 id="como-t">Cómo son estas ediciones</h2>
  <dl class="como-lista">
    <div><dt>Completas</dt>
      <dd>El texto íntegro del autor, sin abreviar ni adaptar.</dd></div>
    <div><dt>Traducidas con ayuda de inteligencia artificial</dt>
      <dd>Cada libro se traduce con ayuda de la IA y luego se revisa y se corrige
      a mano. <a href="acerca/">Así se hace</a>.</dd></div>
    <div><dt>Con notas para los padres</dt>
      <dd>Cada libro dice qué conviene saber antes de leerlo con los niños.</dd></div>
    <div><dt>Mejoradas por los lectores</dt>
      <dd>Las ediciones beta todavía no se han leído completas. Si encuentra un
      error, avíseme y publico una edición corregida.</dd></div>
  </dl>
</section>
{banda_suscribir(sitio, 1)}"""
    return pagina(
        sitio,
        titulo=sitio["nombre"],
        descripcion="Traducciones completas y gratuitas de libros clásicos para familias que educan en casa.",
        cuerpo=cuerpo,
        raiz="./",
        ruta="",
    )


def pagina_libro(sitio: dict, libro: dict) -> str:
    raiz = "../../"
    estado, clase = estado_libro(libro)
    ficha = []
    if libro.get("titulo_original"):
        anio = f" ({libro['anio_original']})" if libro.get("anio_original") else ""
        ficha.append(("Título original", f"<i>{e(libro['titulo_original'])}</i>{anio}"))
    if libro.get("traductor"):
        ficha.append(("Traducción", e(libro["traductor"])))
    if libro.get("ilustraciones"):
        ficha.append(("Ilustraciones", e(libro["ilustraciones"])))
    if libro.get("edades"):
        ficha.append(("Edades", e(libro["edades"])))
    ficha_html = "".join(f"<div><dt>{k}</dt><dd>{v}</dd></div>" for k, v in ficha)

    if libro["disponible"]:
        descarga = f"""
      <a class="boton boton-grande" href="{e(url_descarga(sitio, libro))}">Descargar gratis (EPUB)</a>
      <p class="descarga-ayuda"><a href="{raiz}acerca/#epub">¿Cómo abro un archivo EPUB?</a></p>"""
    else:
        descarga = """
      <p class="boton boton-grande boton-inactivo" aria-disabled="true">Próximamente</p>
      <p class="descarga-ayuda">Suscríbase abajo y le aviso el día que salga.</p>"""

    padres = libro["padres_html"] or (
        '<p class="pendiente">Pendiente: se redactará a partir de la revisión familiar del libro.</p>'
    )
    corr, corr_cls = enlace(url_correccion(sitio, libro))
    if libro.get("edicion") == "revisada":
        aviso = """
    <section class="aviso">
      <h2>Edición revisada</h2>
      <p>Este libro se leyó completo después de la traducción. Aun así, si
      encuentra un error, le agradezco que me lo diga.</p>"""
    else:
        aviso = """
    <section class="aviso aviso-beta">
      <h2>Edición beta</h2>
      <p>Este libro todavía no se ha leído completo después de la traducción.
      Si encuentra un error —una palabra rara, una frase que no se entiende,
      una errata—, avíseme: lo corrijo y publico una edición nueva.</p>"""
    aviso += f"""
      <p><a class="boton boton-claro{corr_cls}" href="{e(corr)}">Enviar una corrección</a></p>
    </section>"""

    autor_extra = (
        f'<span class="libro-autor-extra">{e(libro["autor_extra"])}</span>'
        if libro.get("autor_extra")
        else ""
    )
    cuerpo = f"""
<article class="contenedor libro">
  <p class="migas"><a href="{raiz}#libros">← Todos los libros</a></p>
  <div class="libro-cabeza">
    <img class="libro-portada" src="portada.jpg" alt="Portada de {e(libro['titulo'])}">
    <div class="libro-datos">
      <p class="sello {clase}">{estado}</p>
      <h1>{e(libro['titulo'])}</h1>
      <p class="libro-autor">{e(libro['autor'])}{autor_extra}</p>
      <dl class="ficha">{ficha_html}</dl>
      <div class="descarga">{descarga}
      </div>
    </div>
  </div>
  <div class="libro-cuerpo">
    <section class="descripcion">{libro['descripcion_html']}</section>
    <section class="padres" aria-labelledby="padres-t">
      <h2 id="padres-t">Lo que los padres deben saber</h2>
      {padres}
    </section>
    {aviso}
  </div>
</article>
{banda_suscribir(sitio, 1)}"""
    return pagina(
        sitio,
        titulo=libro["titulo"],
        descripcion=libro.get("resumen", ""),
        cuerpo=cuerpo,
        raiz=raiz,
        ruta=f"libros/{libro['slug']}/",
        imagen=f"libros/{libro['slug']}/portada.jpg",
        tipo="book",
    )


def pagina_simple(sitio: dict, fuente: Path) -> tuple[str, str]:
    """A page from paginas/<nombre>.md; the first line is `# Title`."""
    texto = fuente.read_text(encoding="utf-8")
    titulo = texto.splitlines()[0].lstrip("# ").strip()
    contenido = markdown.markdown(texto, extensions=["attr_list"])
    ruta = f"{fuente.stem}/"
    cuerpo = f'<article class="contenedor prosa">{contenido}</article>'
    return ruta, pagina(
        sitio,
        titulo=titulo,
        descripcion=f"{titulo} · {sitio['nombre']}",
        cuerpo=cuerpo,
        raiz="../",
        ruta=ruta,
    )


# ---------------------------------------------------------------- build


def escribir(ruta: Path, texto: str) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(texto, encoding="utf-8")


def construir() -> None:
    sitio = cargar_sitio()
    libros = cargar_libros()
    if DIST.exists():
        shutil.rmtree(DIST)
    shutil.copytree(RAIZ / "estatico", DIST)

    escribir(DIST / "index.html", pagina_inicio(sitio, libros))
    for libro in libros:
        destino = DIST / "libros" / libro["slug"]
        escribir(destino / "index.html", pagina_libro(sitio, libro))
        portada = libro["carpeta"] / "portada.jpg"
        if portada.exists():
            shutil.copy2(portada, destino / "portada.jpg")

    for fuente in sorted((RAIZ / "paginas").glob("*.md")):
        if fuente.stem == "404":
            continue
        ruta, texto = pagina_simple(sitio, fuente)
        escribir(DIST / ruta / "index.html", texto)

    # 404 is served from any depth, so it uses absolute paths.
    no_encontrada = RAIZ / "paginas" / "404.md"
    if no_encontrada.exists():
        _, texto = pagina_simple(sitio, no_encontrada)
        escribir(DIST / "404.html", texto.replace('"../', '"/'))

    print(f"Sitio construido en {DIST} ({len(libros)} libros).")
    for aviso in avisos:
        print(f"  aviso: {aviso}")


def servir() -> None:
    import functools
    import http.server

    manejador = functools.partial(http.server.SimpleHTTPRequestHandler, directory=DIST)
    with http.server.ThreadingHTTPServer(("127.0.0.1", 8000), manejador) as servidor:
        print("Vista previa en http://localhost:8000  (Ctrl+C para salir)")
        servidor.serve_forever()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    construir()
    if "--serve" in sys.argv:
        servir()
