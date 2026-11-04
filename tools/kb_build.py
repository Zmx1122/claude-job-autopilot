"""Step 2 of the knowledge base: split source files into one clean PDF per document and update knowledge/manifest.yaml.

usage: python3 tools/kb_build.py data/kb/plan.json [--keep-inbox]
plan.json is written by Claude after reading data/kb/extract.json (and the scanned pages):
{"sources": [{"source": "knowledge/inbox/scan.pdf",
              "discard_pages": [5],                      # blank or duplicate pages
              "documents": [{"id": "degree-msc-tu-x", "pages": [1, 2], "kind": "degree",
                             "title": "M.Sc. certificate (Urkunde)", "issuer": "TU X", "date": "2021-10",
                             "language": "de", "summary": "...", "facts": {"grade": "1.8"},
                             "proves": ["Master-level engineering degree", "grade 1.8"],
                             "use_for": [], "sensitive": false,
                             "filename": "Degree_TU-X_MSc-Urkunde_2021.pdf"}]}]}
kinds: cv, cover_letter, degree, transcript, work_reference, certificate, language_certificate, award, publication,
       reference_letter, id_document, other
Every page of every source must be in exactly one document or in discard_pages.
Documents go to knowledge/library/<kind>/<filename>; originals move from knowledge/inbox/ to knowledge/originals/.
"""
import datetime, hashlib, json, os, re, shutil, sys
import yaml
from pypdf import PdfReader, PdfWriter
from common import ROOT

KB = os.path.join(ROOT, 'knowledge'); LIB = os.path.join(KB, 'library'); ORIG = os.path.join(KB, 'originals')
MAN = os.path.join(KB, 'manifest.yaml')
KINDS = {'cv', 'cover_letter', 'degree', 'transcript', 'work_reference', 'certificate', 'language_certificate', 'award',
         'publication', 'reference_letter', 'id_document', 'other'}
SENSITIVE_KINDS = {'id_document'}


def sha(path): return hashlib.sha256(open(path, 'rb').read()).hexdigest()
def safe(name): return re.sub(r'[^A-Za-z0-9._-]+', '-', name).strip('-')


def main():
    plan = json.load(open(sys.argv[1])); keep = '--keep-inbox' in sys.argv
    man = yaml.safe_load(open(MAN)) if os.path.exists(MAN) else None
    man = man or {'version': 1, 'documents': [], 'sources': []}
    ids = {d['id'] for d in man['documents']}
    errors = []
    for s in plan['sources']:
        src = os.path.join(ROOT, s['source'])
        n = len(PdfReader(src).pages)
        used = [p for d in s['documents'] for p in d['pages']] + s.get('discard_pages', [])
        missing = sorted(set(range(1, n + 1)) - set(used)); dup = sorted({p for p in used if used.count(p) > 1})
        if missing: errors.append(f"{s['source']}: pages not assigned {missing}")
        if dup: errors.append(f"{s['source']}: pages used twice {dup}")
        for d in s['documents']:
            if d['kind'] not in KINDS: errors.append(f"{d['id']}: unknown kind {d['kind']}")
            if d['id'] in ids: errors.append(f"{d['id']}: id already in manifest (choose another or remove the old entry)")
    if errors:
        raise SystemExit('plan rejected:\n  ' + '\n  '.join(errors))

    for s in plan['sources']:
        src = os.path.join(ROOT, s['source']); reader = PdfReader(src); made = []
        for d in s['documents']:
            folder = os.path.join(LIB, d['kind']); os.makedirs(folder, exist_ok=True)
            fn = safe(d.get('filename') or f"{d['kind']}_{d['id']}.pdf")
            if not fn.lower().endswith('.pdf'): fn += '.pdf'
            out = os.path.join(folder, fn)
            w = PdfWriter()
            for p in d['pages']: w.add_page(reader.pages[p - 1])
            w.add_metadata({'/Title': d.get('title', fn)})
            with open(out, 'wb') as f: w.write(f)
            entry = {k: d.get(k) for k in ('id', 'kind', 'title', 'issuer', 'date', 'language', 'summary') if d.get(k) is not None}
            entry.update(file=os.path.relpath(out, ROOT), pages=len(d['pages']), size_kb=os.path.getsize(out) // 1024,
                         source=None, source_pages=d['pages'], facts=d.get('facts') or {}, proves=d.get('proves') or [], use_for=d.get('use_for') or [],
                         sensitive=bool(d.get('sensitive') or d['kind'] in SENSITIVE_KINDS), sha256=sha(out))
            man['documents'].append(entry); made.append(entry); ids.add(d['id'])
        # move the original out of the inbox so the next run does not see it again
        dest = src
        if os.path.commonpath([src, os.path.join(KB, 'inbox')]) == os.path.join(KB, 'inbox') and not keep:
            os.makedirs(ORIG, exist_ok=True); dest = os.path.join(ORIG, os.path.basename(src))
            shutil.move(src, dest)
        rel = os.path.relpath(dest, ROOT)
        for e in made: e['source'] = rel
        man['sources'].append({'file': rel, 'sha256': sha(dest), 'pages': len(reader.pages),
                               'documents': [e['id'] for e in made], 'discarded_pages': s.get('discard_pages', [])})
        print(f"{s['source']}: {len(made)} document(s) → " + ', '.join(e['file'] for e in made))
    man['updated'] = datetime.date.today().isoformat()
    man['documents'].sort(key=lambda d: (d['kind'], d.get('date') or ''), reverse=False)
    yaml.safe_dump(man, open(MAN, 'w'), allow_unicode=True, sort_keys=False, width=120)
    print(f"manifest: {len(man['documents'])} documents from {len(man['sources'])} source files → knowledge/manifest.yaml")


if __name__ == '__main__':
    main()
