"""Step 1 of the knowledge base: inventory new files page by page so Claude can identify every document inside them.

usage: python3 tools/kb_extract.py [file or folder ...]      default: knowledge/inbox/
Accepts PDF and images (jpg/png/heic are converted to one-page PDFs first).
Writes data/kb/extract.json:
  [{source, sha256, pages: [{n, chars, text, needs_visual, preview}]}]
- text: first 700 characters of the page's text layer.
- needs_visual: the page has (almost) no text layer — a scan or photo. Claude must look at it:
  Read the preview PNG if one was rendered, otherwise Read the PDF with pages="<n>".
- preview: data/kb/preview/<file>-p<n>.png, rendered when poppler's pdftoppm is installed (brew install poppler).
Files whose sha256 already appears in knowledge/manifest.yaml are skipped, so re-running is cheap.
"""
import hashlib, json, os, shutil, subprocess, sys
from common import ROOT, DATA

KB = os.path.join(ROOT, 'knowledge')
OUT = os.path.join(DATA, 'kb'); PREV = os.path.join(OUT, 'preview')
os.makedirs(PREV, exist_ok=True)


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''): h.update(chunk)
    return h.hexdigest()


def known_hashes():
    p = os.path.join(KB, 'manifest.yaml')
    if not os.path.exists(p): return set()
    import yaml
    m = yaml.safe_load(open(p)) or {}
    return {s.get('sha256') for s in m.get('sources', [])}


def image_to_pdf(path):
    from PIL import Image
    try:
        import pillow_heif; pillow_heif.register_heif_opener()
    except ImportError: pass
    out = os.path.splitext(path)[0] + '.pdf'
    Image.open(path).convert('RGB').save(out, 'PDF', resolution=150)
    return out


def targets(args):
    roots = args or [os.path.join(KB, 'inbox')]
    for r in roots:
        if os.path.isdir(r):
            for dp, _, fs in os.walk(r):
                for f in sorted(fs):
                    if not f.startswith('.'): yield os.path.join(dp, f)
        else:
            yield r


def main():
    from pypdf import PdfReader
    have = known_hashes(); out = []; pdftoppm = shutil.which('pdftoppm')
    for path in targets(sys.argv[1:]):
        ext = os.path.splitext(path)[1].lower()
        if ext in ('.jpg', '.jpeg', '.png', '.heic', '.tif', '.tiff'):
            path = image_to_pdf(path); ext = '.pdf'
        if ext != '.pdf':
            print('skip (not a PDF or image):', os.path.relpath(path, ROOT)); continue
        h = sha(path)
        if h in have:
            print('already in knowledge base:', os.path.relpath(path, ROOT)); continue
        r = PdfReader(path); pages = []
        stem = os.path.splitext(os.path.basename(path))[0].replace(' ', '_')
        for i, pg in enumerate(r.pages, 1):
            t = ' '.join((pg.extract_text() or '').split())
            prev = ''
            if len(t) < 80 and pdftoppm:
                base = os.path.join(PREV, f'{stem}-p{i}')
                subprocess.run([pdftoppm, '-png', '-r', '80', '-f', str(i), '-l', str(i), '-singlefile', path, base], capture_output=True)
                if os.path.exists(base + '.png'): prev = os.path.relpath(base + '.png', ROOT)
            pages.append(dict(n=i, chars=len(t), text=t[:700], needs_visual=len(t) < 80, preview=prev))
        out.append(dict(source=os.path.relpath(path, ROOT), sha256=h, size_kb=os.path.getsize(path) // 1024, pages=pages))
        vis = sum(p['needs_visual'] for p in pages)
        print(f"{os.path.relpath(path, ROOT)}: {len(pages)} pages, {vis} need a visual read")
    json.dump(out, open(os.path.join(OUT, 'extract.json'), 'w'), ensure_ascii=False, indent=1)
    print(f'{len(out)} new file(s) → data/kb/extract.json' + ('' if pdftoppm else '  (no pdftoppm: Read scanned pages directly from the PDF)'))


if __name__ == '__main__':
    main()
