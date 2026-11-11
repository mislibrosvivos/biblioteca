# Mis Libros Vivos

Traducciones completas y gratuitas al español de libros clásicos, para familias
que educan en casa. Los libros se leen y se descargan en
**[mislibrosvivos.com](https://mislibrosvivos.com)**.

---

## Maintaining the site

The site is built by `build.py` and published to GitHub Pages by
`.github/workflows/pages.yml` on every push to `main`. The EPUBs are not in
the repo: each edition is a GitHub Release with the EPUB attached.

**Preview locally**

    python -m venv .venv
    .venv\Scripts\pip install -r requirements.txt
    .venv\Scripts\python build.py --serve

Then open http://localhost:8000. The build lists anything still missing.

**Add a book**

1. Create `libros/<slug>/` with `libro.toml` (copy an existing one),
   `descripcion.md`, `padres.md` and `portada.jpg`.
2. Upload the EPUB:
   `gh release create <slug>-v1 <slug>.epub --title "<Título> (edición beta)"`
3. Put the tag and file name in `libro.toml` (`release`, `archivo`) and push.

A new edition is a new release (`<slug>-v2`). Point `release` at it; the old
one stays downloadable.

**Site-wide links** (newsletter, tip jar, feedback form, license) are in
`sitio.toml`.
