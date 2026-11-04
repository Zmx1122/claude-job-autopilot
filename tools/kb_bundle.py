"""Step 3 (at application time): turn knowledge-base documents into exactly the files a form asks for.

usage:
  python3 tools/kb_bundle.py --list
  python3 tools/kb_bundle.py --merge cv-ai,degree-msc,transcript-msc --name Doe_Jane_Unterlagen [--max-mb 5]
  python3 tools/kb_bundle.py --separate cv-ai,degree-msc --prefix Doe_Jane [--max-mb 5]
  add --allow-sensitive to include documents marked sensitive (ID, residence permit) — only when the form asks for them.
--merge     one PDF in the given order, with a bookmark per document → data/bundles/<name>.pdf
--separate  one upload-ready copy per document, named <prefix>_<Kind>[_n].pdf → data/bundles/
--max-mb    if a file is larger, images are recompressed (JPEG, max 1700 px) until it fits or cannot shrink further.
Prints every output file with pages and size, ready to pass to tools/upload_file.sh.
"""
import argparse, io, os, sys
import yaml
from pypdf import PdfReader, PdfWriter
from common import ROOT, DATA

MAN = os.path.join(ROOT, 'knowledge', 'manifest.yaml'); OUT = os.path.join(DATA, 'bundles')
KIND_LABEL = {'cv': 'Lebenslauf', 'cover_letter': 'Anschreiben', 'degree': 'Abschlusszeugnis', 'transcript': 'Notenspiegel',
              'work_reference': 'Arbeitszeugnis', 'certificate': 'Zertifikat', 'language_certificate': 'Sprachzertifikat',
              'award': 'Auszeichnung', 'publication': 'Publikation', 'reference_letter': 'Empfehlung', 'id_document': 'Ausweis', 'other': 'Dokument'}


def load():
    if not os.path.exists(MAN): raise SystemExit('knowledge/manifest.yaml not found — build the knowledge base first.')
    m = yaml.safe_load(open(MAN)) or {}
    return {d['id']: d for d in m.get('documents', [])}


def shrink(path, max_mb):
    if not max_mb or os.path.getsize(path) <= max_mb * 1024 * 1024: return
    from PIL import Image
    for quality, edge in ((75, 1700), (60, 1400), (45, 1100)):
        w = PdfWriter(clone_from=path)
        for page in w.pages:
            for img in page.images:
                try:
                    im = img.image.convert('RGB'); im.thumbnail((edge, edge))
                    img.replace(im, quality=quality)
                except Exception: pass
        try: w.compress_identical_objects(remove_duplicates=True, remove_unreferenced=True)
        except TypeError: w.compress_identical_objects(remove_identicals=True, remove_orphans=True)
        tmp = path + '.tmp'
        with open(tmp, 'wb') as f: w.write(f)
        os.replace(tmp, path)
        if os.path.getsize(path) <= max_mb * 1024 * 1024: return
    print(f'  ! still {os.path.getsize(path) / 1048576:.1f} MB after compression (limit {max_mb} MB) — split the upload or drop a document')


def report(path):
    print(f'{os.path.relpath(path, ROOT)}  ·  {len(PdfReader(path).pages)} pages  ·  {os.path.getsize(path) / 1048576:.2f} MB')
    print(f'  absolute: {path}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--list', action='store_true'); ap.add_argument('--merge'); ap.add_argument('--separate')
    ap.add_argument('--name', default='Bewerbungsunterlagen'); ap.add_argument('--prefix', default='')
    ap.add_argument('--max-mb', type=float, default=0); ap.add_argument('--allow-sensitive', action='store_true')
    a = ap.parse_args(); docs = load(); os.makedirs(OUT, exist_ok=True)
    if a.list or not (a.merge or a.separate):
        print(f"{'id':34} {'kind':20} {'pages':>5} {'KB':>6}  lang  title")
        for d in docs.values():
            print(f"{d['id'][:34]:34} {d['kind']:20} {d['pages']:>5} {d.get('size_kb', 0):>6}  {d.get('language', ''):4}  {d.get('title', '')}" + ('  [sensitive]' if d.get('sensitive') else ''))
        return
    ids = [i.strip() for i in (a.merge or a.separate).split(',') if i.strip()]
    unknown = [i for i in ids if i not in docs]
    if unknown: raise SystemExit(f'unknown ids: {unknown}. Run --list.')
    blocked = [i for i in ids if docs[i].get('sensitive') and not a.allow_sensitive]
    if blocked: raise SystemExit(f'sensitive documents need --allow-sensitive (only if the form explicitly asks): {blocked}')
    if a.merge:
        w = PdfWriter()
        for i in ids:
            start = len(w.pages)
            for p in PdfReader(os.path.join(ROOT, docs[i]['file'])).pages: w.add_page(p)
            w.add_outline_item(docs[i].get('title') or KIND_LABEL[docs[i]['kind']], start)
        w.add_metadata({'/Title': a.name.replace('_', ' ')})
        out = os.path.join(OUT, a.name if a.name.endswith('.pdf') else a.name + '.pdf')
        with open(out, 'wb') as f: w.write(f)
        shrink(out, a.max_mb); report(out)
    else:
        seen = {}
        for i in ids:
            label = KIND_LABEL[docs[i]['kind']]; seen[label] = seen.get(label, 0) + 1
            name = '_'.join(x for x in (a.prefix, label + (f'_{seen[label]}' if seen[label] > 1 else '')) if x) + '.pdf'
            out = os.path.join(OUT, name)
            w = PdfWriter(clone_from=os.path.join(ROOT, docs[i]['file']))
            with open(out, 'wb') as f: w.write(f)
            shrink(out, a.max_mb); report(out)


if __name__ == '__main__':
    main()
