"""Keep a local copy of a job posting (job description) — postings disappear after a few weeks, interviews come later.

usage:
  python3 tools/jd_snapshot.py --url URL --company "ACME AG" --title "AI Engineer" [--date YYYY-MM-DD]
                               [--text-file pane.txt] [--platform LinkedIn] [--force]
  python3 tools/jd_snapshot.py --backfill [--status Applied,Confirmed,Interview,Offer] [--delay 20] [--limit N]

One folder per application, the same one the writer uses for tailored documents:
  data/applications/<YYYY-MM-DD>_<Company>_<Title>/
    jd.md       clean text with a header (URL, company, title, captured at, how, online/closed)
    jd.pdf      readable PDF of that text (always produced; what you open before an interview)
    page.pdf    print of the live page as the site shows it (kept only when it really shows the posting)
    page.html   the page's DOM as loaded (raw evidence)
--text-file: text you already read from the posting in the built-in browser (get_page_text) — best source, because the
browser is logged in; the headless print is a second, anonymous copy. Without it the text is taken from the page's DOM.
--backfill: every Notion row with a job URL and one of --status, whose folder has no jd.md yet, one at a time with a pause
(LinkedIn answers bulk requests with HTTP 429 — keep --delay ≥ 15). With --force it also redoes snapshots that hit a login
wall. Prints one line per job and a summary.
LinkedIn URLs are read through LinkedIn's public job card (no login): the anonymous page itself turns into a login wall
after a few requests. page.pdf is kept only when the printed page really shows the posting.
Folders live under data/ (git-ignored) and are copied by tools/backup.py.
"""
import argparse, datetime, html, os, re, shutil, subprocess, sys, tempfile, time
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
APPS = os.path.join(ROOT, 'data', 'applications')
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36'
# containers that hold the posting on common boards; the first one found wins, else the whole <main>/<body>
CONTAINERS = [r'show-more-less-html__markup', r'description__text', r'jobs-description', r'job-ad-display',
              r'job-ad-content', r'jobsearch-JobComponent-description', r'jobDescriptionText', r'job-description',
              r'job__description', r'posting-page', r'ashby-job-posting', r'content-intro', r'jobad']
CLOSED = [r'no longer accepting applications', r'nimmt keine bewerbungen mehr an', r'closed-job', r'no longer available', r'job (?:has )?expired', r'position (?:has been )?filled',
          r'nicht mehr verfügbar', r'nicht mehr online', r'stellenanzeige ist abgelaufen', r'bewerbungsfrist ist abgelaufen',
          r'diese stelle ist (?:leider )?(?:bereits )?besetzt', r'page (?:was )?not found', r'seite wurde nicht gefunden']
BLOCKED = [r'authwall', r'linkedin login', r'einloggen \| linkedin', r'sign in \| linkedin', r'sign in to view',
           r'captcha', r'access denied', r'are you a robot', r'unusual activity', r'passwort vergessen', r'forgot password']
VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'source', 'track', 'wbr'}
BLOCK = {'p', 'div', 'li', 'ul', 'ol', 'br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'section', 'article', 'tr', 'table', 'header', 'footer'}


def slug(s, n=40):
    s = re.sub(r'\((?:[mwfd]/[mwfd](?:/[mwfd])?|all genders?)\)', '', s or '', flags=re.I)
    s = re.sub(r'[^A-Za-z0-9ÄÖÜäöüß]+', '-', s).strip('-')
    s = s.translate(str.maketrans({'Ä': 'Ae', 'Ö': 'Oe', 'Ü': 'Ue', 'ä': 'ae', 'ö': 'oe', 'ü': 'ue', 'ß': 'ss'}))
    return s[:n].rstrip('-') or 'x'


def folder(date, company, title):
    return os.path.join(APPS, f'{date}_{slug(company, 30)}_{slug(title)}')


class Text(HTMLParser):
    """DOM → text with line breaks at block elements; collects the text of the first container that matches CONTAINERS."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip = 0; self.all = []; self.box = None; self.depth = 0; self.box_depth = None; self.title = ''
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ('script', 'style', 'noscript', 'svg', 'template'):
            self.skip += 1; return
        if tag == 'title':
            self._in_title = True
        if tag in VOID:  # no end tag follows: must not change the depth that tells where the container ends
            if tag == 'br': self._emit('\n')
            return
        self.depth += 1
        cls = ' '.join(filter(None, [a.get('class'), a.get('id'), a.get('data-at'), a.get('data-testid')]))
        if self.box is None and cls and any(re.search(p, cls, re.I) for p in CONTAINERS):
            self.box = []; self.box_depth = self.depth
        if tag in BLOCK: self._emit('\n')
        if tag == 'li': self._emit('• ')

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript', 'svg', 'template'):
            self.skip = max(0, self.skip - 1); return
        if tag == 'title': self._in_title = False
        if tag in VOID: return
        if tag in BLOCK: self._emit('\n')
        if self.box_depth is not None and self.depth == self.box_depth:
            self.box_depth = -1  # container closed; keep what it collected
        self.depth -= 1

    def handle_data(self, d):
        if self.skip: return
        if self._in_title: self.title += d
        self._emit(d)

    def _emit(self, s):
        self.all.append(s)
        if self.box is not None and self.box_depth not in (None, -1): self.box.append(s)


def clean(s):
    s = re.sub(r'[ \t ]+', ' ', s)
    s = re.sub(r' *\n *', '\n', s)
    s = re.sub(r'(?im)^(?:show (?:more|less)|mehr anzeigen|weniger anzeigen|… ?mehr|see more)$', '', s)
    return re.sub(r'\n{3,}', '\n\n', s).strip()


def chrome(args, timeout=60):
    from doc_render import browser
    with tempfile.TemporaryDirectory() as tmp:
        cmd = [browser(), '--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check', '--hide-scrollbars',
               f'--user-data-dir={os.path.join(tmp, "p")}', f'--user-agent={UA}', '--lang=de-DE,en-US',
               '--virtual-time-budget=9000', '--run-all-compositor-stages-before-draw'] + args
        r = subprocess.run(cmd, capture_output=True, timeout=timeout)
        return r.stdout.decode('utf-8', 'replace')


def text_pdf(md_path, pdf_path, meta, body):
    """Readable PDF of the captured text (same headless browser that prints the CVs)."""
    rows = ''.join(f'<tr><th>{html.escape(k)}</th><td>{html.escape(str(v))}</td></tr>' for k, v in meta.items() if v)
    paras = ''.join(f'<p>{html.escape(p)}</p>' for p in body.split('\n\n'))
    doc = (f'<!doctype html><meta charset="utf-8"><title>{html.escape(meta.get("title", "Job description"))}</title><style>'
           '@page{size:A4;margin:16mm}body{font:10pt/1.45 Arial,Helvetica,sans-serif;color:#1d1d1f}'
           'h1{font-size:15pt;margin:0 0 2mm}table{border-collapse:collapse;margin:0 0 5mm;font-size:8.5pt;color:#555}'
           'th{text-align:left;padding:0 4mm 0 0;font-weight:600}td{word-break:break-all}p{margin:0 0 2.5mm;white-space:pre-wrap}'
           f'</style><h1>{html.escape(meta.get("title", ""))} — {html.escape(meta.get("company", ""))}</h1><table>{rows}</table>{paras}')
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, 'jd.html'); open(src, 'w').write(doc)
        chrome(['--no-pdf-header-footer', f'--print-to-pdf={pdf_path}', 'file://' + src])
    return os.path.exists(pdf_path)


def status_of(text, title):
    """online | closed | blocked (login wall, CAPTCHA, or a page that does not mention the job at all)."""
    low = text.lower()
    if any(re.search(p, low[:4000]) for p in BLOCKED) or len(text) < 400:
        return 'blocked'
    if any(re.search(p, low) for p in CLOSED):
        return 'closed'
    return 'online'


def linkedin_id(url):
    m = re.search(r'linkedin\.com/.*?(?:jobs/view/(?:[^/?]*-)?|currentJobId=)(\d{6,})', url or '')
    return m.group(1) if m else None


def linkedin_public(job_id, tries=3):
    """LinkedIn's public job card (no login): top card + full description. Waits and retries on HTTP 429."""
    import requests
    for i in range(tries):
        r = requests.get(f'https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}',
                         headers={'User-Agent': UA, 'Accept-Language': 'de-DE,de;q=0.9,en;q=0.8'}, timeout=30)
        if r.status_code == 200:
            return r.text
        if r.status_code == 404:
            return '<div class="closed-job">no longer available (404)</div>'
        time.sleep(60 * (i + 1))
    return ''


def pdf_text(path):
    try:
        from pypdf import PdfReader
        return ' '.join((p.extract_text() or '') for p in PdfReader(path).pages[:3])
    except Exception:
        return ''


def snapshot(url, company, title, date, text_file=None, platform='', force=False):
    out = folder(date, company, title)
    os.makedirs(out, exist_ok=True)
    md = os.path.join(out, 'jd.md')
    if os.path.exists(md) and not force:
        return out, 'exists'
    dom, source = '', 'headless browser (anonymous), page DOM'
    lid = linkedin_id(url)
    try:
        if lid:  # the anonymous LinkedIn page soon turns into a login wall; the public job card does not
            dom, source = linkedin_public(lid), 'LinkedIn public job card (anonymous)'
        if not dom:
            dom = chrome(['--dump-dom', url], timeout=90)
    except Exception as e:  # network / timeout: the pane text may still be there
        print(f'  ! page load failed: {e}', file=sys.stderr)
    if dom:
        open(os.path.join(out, 'page.html'), 'w').write(dom)
    p = Text()
    try: p.feed(dom)
    except Exception: pass
    page_text = clean(''.join(p.box) if p.box and len(clean(''.join(p.box))) > 300 else ''.join(p.all))
    if text_file:
        body, how = clean(open(text_file).read()), 'built-in browser (logged in), get_page_text'
    else:
        body, how = page_text, source
    st = status_of(body if text_file else page_text, title)
    if st == 'online' and lid and 'closed-job' in dom:
        st = 'closed'  # LinkedIn still serves the full text of a closed posting; only this class says it is closed
    if text_file and st == 'blocked':
        st = 'online'  # the pane text is the posting itself even when the anonymous copy hit a login wall
    now = datetime.datetime.now().astimezone().isoformat(timespec='seconds')
    meta = {'title': title, 'company': company, 'url': url, 'platform': platform, 'applied': date,
            'captured_at': now, 'captured_with': how, 'page_status': st}
    head = '\n'.join(f'{k}: {v}' for k, v in meta.items() if v)
    open(md, 'w').write(f'---\n{head}\n---\n\n{body}\n')
    text_pdf(md, os.path.join(out, 'jd.pdf'), meta, body)
    page_pdf = os.path.join(out, 'page.pdf')
    if st == 'online':
        try:
            chrome(['--no-pdf-header-footer', f'--print-to-pdf={page_pdf}', url], timeout=90)
        except Exception as e:
            print(f'  ! page print failed: {e}', file=sys.stderr)
        pt = pdf_text(page_pdf) if os.path.exists(page_pdf) else ''
        words = [w.lower() for w in re.findall(r'[A-Za-zÄÖÜäöüß]{4,}', title or '')][:3]
        if pt and (status_of(pt, title) != 'online' or not any(w in pt.lower() for w in words)):
            os.remove(page_pdf)  # a login wall or an empty page, not the posting
    elif os.path.exists(page_pdf) and force:
        os.remove(page_pdf)
    return out, st


def needs_snapshot(r, redo):
    md = os.path.join(folder(r.get('applied') or r.get('first_seen') or 'undated', r['company'], r['title']), 'jd.md')
    if not os.path.exists(md):
        return True
    head = open(md).read(3000)
    return redo and ('page_status: blocked' in head or any(re.search(p, head.lower()) for p in BLOCKED))


def backfill(statuses, delay, limit, redo=False):
    from common import load_env, notion_rows
    rows = [r for r in notion_rows(load_env()) if r.get('url') and r.get('status') in statuses]
    todo = [r for r in rows if needs_snapshot(r, redo)]
    print(f'{len(rows)} rows with a URL in {sorted(statuses)}; {len(todo)} without a snapshot')
    tally = {}
    for i, r in enumerate(todo[:limit] if limit else todo):
        date = r.get('applied') or r.get('first_seen') or 'undated'
        out, st = snapshot(r['url'], r['company'], r['title'], date, platform=r.get('platform', ''), force=redo)
        tally[st] = tally.get(st, 0) + 1
        print(f'{st:8} {r["company"][:28]:28} {r["title"][:50]:50} → {os.path.relpath(out, ROOT)}', flush=True)
        if i + 1 < len(todo): time.sleep(delay)
    print('summary:', ', '.join(f'{k} {v}' for k, v in sorted(tally.items())) or 'nothing to do')
    print('online = full copy · closed = posting already gone (header/text kept) · blocked = login wall; '
          'for blocked ones open the URL in the built-in browser and rerun with --text-file --force')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--url'); ap.add_argument('--company'); ap.add_argument('--title'); ap.add_argument('--platform', default='')
    ap.add_argument('--date', default=str(datetime.date.today())); ap.add_argument('--text-file'); ap.add_argument('--force', action='store_true')
    ap.add_argument('--backfill', action='store_true')
    ap.add_argument('--status', default='Applied,Confirmed,Interview,Offer')
    ap.add_argument('--delay', type=float, default=20); ap.add_argument('--limit', type=int, default=0)
    a = ap.parse_args()
    if a.backfill:
        backfill(set(a.status.split(',')), a.delay, a.limit, redo=a.force)
    elif a.url and a.company and a.title:
        out, st = snapshot(a.url, a.company, a.title, a.date, a.text_file, a.platform, a.force)
        files = ', '.join(sorted(f for f in os.listdir(out) if f.startswith(('jd', 'page'))))
        print(f'{st} → {os.path.relpath(out, ROOT)}  ({files})')
    else:
        raise SystemExit(__doc__)
