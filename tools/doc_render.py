"""Render a CV or cover letter from a YAML content file to a text-based, one-column PDF (headless Chrome / Edge / Brave),
then verify it: page count, every line present in the PDF text layer in reading order, and a PNG preview for the visual check.

usage:
  python3 tools/doc_render.py cv     <cv.yaml>     --out <file.pdf> [--max-pages 1] [--register ID --use-for "kw1,kw2" --title "..."]
  python3 tools/doc_render.py letter <letter.yaml> --out <file.pdf>
--register adds or updates the generated CV in knowledge/manifest.yaml (kind cv) so the scan-apply skill can pick it.
Set CHROME_PATH to use a specific Chromium-based browser.

cv.yaml:
  lang: en | de                       # section headings default to this language
  name: Jane Doe
  headline: AI Engineer — Conversational Agents
  contact: ["Munich, Germany", "+49 …", "jane@example.com", {text: "linkedin.com/in/jane", url: "https://linkedin.com/in/jane"}]
  languages: "German C1 · English C1"
  photo: ""                           # optional image path (not expected in Germany)
  summary: "3–4 lines"
  sections:
    - kind: entries                   # experience / education
      title: Experience
      items:
        - {what: "Role · Organisation", when: "04/2025 – present", where: "Munich", note: "one-line org description",
           bullets: ["…", {text: "…", fact: achievement-id}]}
    - kind: skills
      title: Skills
      groups: [{label: "LLM & Agents", items: ["RAG", "Tool calling"]}]
    - kind: list
      title: Selected achievements
      items: ["…"]
    - kind: text
      title: Publications
      text: "…"
letter.yaml:
  lang, name, contact (same as the CV), date, recipient: "Company\\nTeam\\nStreet\\nCity", subject, salutation,
  paragraphs: [...], closing: "Kind regards", signature: "Jane Doe"
"""
import argparse, glob, hashlib, html, os, re, shutil, subprocess, sys, tempfile
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSS = os.path.join(ROOT, 'templates', 'document.css')
E = lambda s: html.escape(str(s or ''))
BROWSERS = ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
            '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
            '/Applications/Brave Browser.app/Contents/MacOS/Brave Browser',
            '/Applications/Chromium.app/Contents/MacOS/Chromium']


def browser():
    for b in [os.environ.get('CHROME_PATH', '')] + BROWSERS + [shutil.which(n) or '' for n in ('google-chrome', 'chromium', 'chromium-browser', 'msedge')]:
        if b and os.path.exists(b):
            return b
    raise SystemExit('No Chromium-based browser found to print the PDF. Install Google Chrome (free), or set CHROME_PATH.')


def contact_line(items):
    out = []
    for c in items or []:
        if isinstance(c, dict):
            out.append(f'<a href="{E(c.get("url"))}">{E(c.get("text"))}</a>' if c.get('url') else E(c.get('text')))
        else:
            out.append(E(c))
    return ' · '.join(out)


def btext(b): return b.get('text') if isinstance(b, dict) else b


def cv_html(d):
    head = f'<h1>{E(d["name"])}</h1>'
    if d.get('headline'): head += f'<div class="headline">{E(d["headline"])}</div>'
    head += f'<div class="contact">{contact_line(d.get("contact"))}</div>'
    if d.get('languages'): head += f'<div class="langs">{E(d["languages"])}</div>'
    photo = f'<img class="photo" src="file://{os.path.abspath(d["photo"])}">' if d.get('photo') else ''
    body = [f'<header class="top"><div>{head}</div>{photo}</header>']
    if d.get('summary'): body.append(f'<div class="summary">{E(d["summary"])}</div>')
    for s in d.get('sections', []):
        body.append(f'<h2>{E(s.get("title"))}</h2>')
        k = s.get('kind')
        if k == 'entries':
            for it in s.get('items', []):
                when = ' · '.join(x for x in (it.get('when'), it.get('where')) if x)
                h = f'<div class="entry"><div class="row"><span class="what">{E(it.get("what"))}</span><span class="when">{E(when)}</span></div>'
                if it.get('note'): h += f'<div class="note">{E(it["note"])}</div>'
                if it.get('bullets'): h += '<ul>' + ''.join(f'<li>{E(btext(b))}</li>' for b in it['bullets']) + '</ul>'
                body.append(h + '</div>')
        elif k == 'skills':
            body.append('<div class="skills">' + ''.join(
                f'<div class="row"><span class="label">{E(g.get("label"))}</span><span>{E(" · ".join(g.get("items", [])))}</span></div>'
                for g in s.get('groups', [])) + '</div>')
        elif k == 'list':
            body.append('<ul>' + ''.join(f'<li>{E(btext(x))}</li>' for x in s.get('items', [])) + '</ul>')
        else:
            body.append(f'<div>{E(s.get("text"))}</div>')
    return body


def letter_html(d):
    head = f'<h1>{E(d["name"])}</h1><div class="contact">{contact_line(d.get("contact"))}</div>'
    body = [f'<div class="letter"><header>{head}</header>',
            f'<div class="meta"><div class="recipient">{E(d.get("recipient"))}</div><div>{E(d.get("date"))}</div></div>']
    if d.get('subject'): body.append(f'<div class="subject">{E(d["subject"])}</div>')
    body.append(f'<p>{E(d.get("salutation"))}</p>')
    body += [f'<p>{E(p)}</p>' for p in d.get('paragraphs', [])]
    body.append(f'<div class="closing">{E(d.get("closing"))}<br><br>{E(d.get("signature") or d.get("name"))}</div></div>')
    return body


def expected_lines(kind, d):
    """Strings that must appear, in this order, in the PDF text layer."""
    if kind == 'letter':
        return [d['name'], d.get('subject'), d.get('salutation')] + list(d.get('paragraphs', [])) + [d.get('closing')]
    out = [d['name'], d.get('headline'), d.get('summary')]
    for s in d.get('sections', []):
        out.append(s.get('title'))
        for it in s.get('items', []) if s.get('kind') in ('entries', 'list') else []:
            if isinstance(it, dict) and 'what' in it:
                out.append(it.get('what')); out += [btext(b) for b in it.get('bullets', [])]
            else:
                out.append(btext(it))
    return [x for x in out if x]


def norm(s):
    import unicodedata
    return re.sub(r'[^a-z0-9äöüß]+', '', unicodedata.normalize('NFKC', str(s)).lower())


def verify(pdf, kind, d, max_pages):
    from pypdf import PdfReader
    r = PdfReader(pdf)
    text = norm(''.join(p.extract_text() or '' for p in r.pages))
    problems, pos = [], 0
    for line in expected_lines(kind, d):
        key = norm(line)[:60]
        i = text.find(key, pos)
        if i < 0:
            problems.append(('missing' if text.find(key) < 0 else 'out of reading order') + f': "{str(line)[:70]}"')
        else:
            pos = i
    if max_pages and len(r.pages) > max_pages:
        problems.append(f'{len(r.pages)} pages, limit is {max_pages} — shorten (CV rule 1 / letter rule 1)')
    return len(r.pages), problems


def preview(pdf):
    if not shutil.which('pdftoppm'):
        return []
    base = os.path.join(os.path.dirname(pdf), '.preview', os.path.splitext(os.path.basename(pdf))[0])
    os.makedirs(os.path.dirname(base), exist_ok=True)
    for old in glob.glob(base + '-*.png'): os.remove(old)
    subprocess.run(['pdftoppm', '-r', '80', '-png', pdf, base], check=True)
    return sorted(glob.glob(base + '-*.png'))


def register(pdf, a, d):
    man_path = os.path.join(ROOT, 'knowledge', 'manifest.yaml')
    man = yaml.safe_load(open(man_path)) if os.path.exists(man_path) else {'version': 1, 'documents': [], 'sources': []}
    from pypdf import PdfReader
    entry = {'id': a.register, 'kind': 'cv', 'title': a.title or f"CV — {d.get('headline', '')} ({d.get('lang', 'en').upper()})",
             'issuer': 'self', 'date': str(__import__('datetime').date.today())[:7], 'language': d.get('lang', 'en'),
             'summary': 'Generated by job-application-writer from knowledge/career/facts.yaml.',
             'file': os.path.relpath(os.path.abspath(pdf), ROOT), 'pages': len(PdfReader(pdf).pages),
             'size_kb': os.path.getsize(pdf) // 1024, 'generated_from': os.path.relpath(os.path.abspath(a.src), ROOT),
             'facts': {}, 'proves': [], 'use_for': [x.strip() for x in (a.use_for or '').split(',') if x.strip()],
             'visual_notes': 'generated one-column text PDF', 'sensitive': False,
             'sha256': hashlib.sha256(open(pdf, 'rb').read()).hexdigest()}
    docs = man.setdefault('documents', [])
    old = next((x for x in docs if x['id'] == a.register), None)
    if old:
        entry['proves'] = old.get('proves') or []; entry['facts'] = old.get('facts') or {}
        docs[docs.index(old)] = entry
    else:
        docs.append(entry)
    yaml.safe_dump(man, open(man_path, 'w'), allow_unicode=True, sort_keys=False, width=120)
    print(f"registered {a.register} in knowledge/manifest.yaml ({'updated' if old else 'new'})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('kind', choices=['cv', 'letter'])
    ap.add_argument('src'); ap.add_argument('--out', required=True)
    ap.add_argument('--max-pages', type=int, default=None)
    ap.add_argument('--register'); ap.add_argument('--use-for'); ap.add_argument('--title')
    a = ap.parse_args()
    d = yaml.safe_load(open(a.src))
    parts = cv_html(d) if a.kind == 'cv' else letter_html(d)
    doc = (f'<!doctype html><html lang="{E(d.get("lang", "en"))}"><head><meta charset="utf-8"><title>{E(d["name"])}</title>'
           f'<style>{open(CSS).read()}</style></head><body>' + '\n'.join(parts) + '</body></html>')
    out = os.path.abspath(a.out); os.makedirs(os.path.dirname(out), exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, 'doc.html'); open(src, 'w').write(doc)
        cmd = [browser(), '--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
               f'--user-data-dir={os.path.join(tmp, "profile")}', '--no-pdf-header-footer', f'--print-to-pdf={out}', 'file://' + src]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if not os.path.exists(out):
            raise SystemExit(f'PDF not written. Browser said: {(r.stderr or r.stdout)[-400:]}')
    max_pages = a.max_pages or (2 if a.kind == 'cv' else 1)
    pages, problems = verify(out, a.kind, d, max_pages)
    print(f'{a.kind} → {out} ({pages} page{"s" if pages > 1 else ""}, {os.path.getsize(out) // 1024} KB)')
    for p in problems: print('❌', p)
    if not problems: print('✅ text layer complete and in reading order')
    for png in preview(out): print('preview (look at it — dual review):', png)
    if a.register and not problems:
        register(out, a, d)
    sys.exit(1 if problems else 0)


if __name__ == '__main__':
    main()
