"""Check a CV and (optionally) a cover letter against the country standard and against each other.

usage: python3 tools/doc_check.py --cv CV.pdf [--letter LETTER.pdf] [--keywords "LLM|large language model,RAG,Python"]
                                  [--facts knowledge/career/facts.yaml] [--max-pages 1] [--company ACME] [--cv-yaml cv.yaml]
Reports (❌ = fix before sending, ⚠️ = look at it):
  CV      text layer present (ATS), page limit, dates to the month, hollow skill qualifiers, the same achievement repeated
  CV      with --cv-yaml (the content file the PDF was rendered from), the screener-wording rules 19–20:
          bare model names / algorithms / codenames without a plain-language descriptor, and technical terms repeated
          across the bullets of one position (lift them into one lead line)
  letter  300–450 words, generic opening, filler words, dashes, subject line
  both    durations that disagree with the fact bank (e.g. "two and a half years" vs 01/2022–03/2024 = 2 years 3 months),
          the same noun with different numbers, numbers in the letter that the CV does not show, keyword coverage
"""
import argparse, difflib, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
WORDNUM = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
           'eleven': 11, 'twelve': 12, 'ein': 1, 'eine': 1, 'einem': 1, 'zwei': 2, 'drei': 3, 'vier': 4, 'fünf': 5, 'sechs': 6,
           'sieben': 7, 'acht': 8, 'neun': 9, 'zehn': 10, 'anderthalb': 1.5, 'eineinhalb': 1.5, 'zweieinhalb': 2.5, 'dreieinhalb': 3.5}
NUM = r'(\d+(?:[.,]\d+)?|' + '|'.join(sorted(WORDNUM, key=len, reverse=True)) + r')'
FILLER = ['passionate', 'thrilled', 'excited to', 'delve', 'leverage', 'synergy', 'dynamic environment', 'team player',
          'hands-on mentality', 'i am writing to apply', 'hiermit bewerbe ich mich', 'mit großem interesse', 'with great interest',
          'leidenschaftlich', 'teamplayer', 'spannende herausforderung', 'exciting challenge']
HOLLOW = re.compile(r'\((?:professional|proficient|expert|advanced|sehr gut|fortgeschritten|verhandlungssicher)\)|\b(?:proficient in|expert in|fundierte kenntnisse)\b', re.I)
SALUT = re.compile(r'^(dear|sehr geehrte|hallo|liebe|guten tag)', re.I)
CLOSE = re.compile(r'^(kind regards|best regards|sincerely|yours|mit freundlichen grüßen|viele grüße|beste grüße)', re.I)


def text_of(pdf):
    from pypdf import PdfReader
    import unicodedata
    r = PdfReader(pdf)
    return [unicodedata.normalize('NFKC', p.extract_text() or '') for p in r.pages]   # NFKC: ligatures like "ﬁ" → "fi"


def val(tok):
    t = tok.lower()
    return WORDNUM[t] if t in WORDNUM else float(t.replace(',', '.'))


def flow(text):
    """PDF text → running text: re-join words hyphenated across lines, turn line breaks into spaces."""
    return re.sub(r'\s*\n\s*', ' ', re.sub(r'(\w)-\n(\w)', r'\1-\2', text))


def durations_in(text):
    """[(months, phrase, sentence)] for duration phrases in EN and DE."""
    out = []
    for sent in re.split(r'(?<=[.!?;])\s+', flow(text)):
        if re.search(r'kündigungsfrist|notice period|probezeit|probation|befristet|fixed-term', sent, re.I):
            continue   # notice periods and contract terms are not work durations
        s = sent
        for m in re.finditer(r'(\d+)\s+(?:years?|jahre?n?)\s+(?:and\s+|und\s+)?(\d+)\s+(?:months?|monate?n?)', s, re.I):
            out.append((int(m.group(1)) * 12 + int(m.group(2)), m.group(0), sent)); s = s.replace(m.group(0), ' ')
        for m in re.finditer(NUM + r'(\s+and\s+a\s+half)?\s*(\+)?\s+(?:years?|jahre?n?)\b', s, re.I):
            v = val(m.group(1)) + (0.5 if m.group(2) else 0)
            out.append((round(v * 12), m.group(0) + (' (at least)' if m.group(3) else ''), sent))
        for m in re.finditer(r'half\s+a\s+year|ein\s+halbes\s+jahr', s, re.I):
            out.append((6, m.group(0), sent))
        for m in re.finditer(NUM + r'\s+(?:months?|monate?n?)\b', s, re.I):
            out.append((round(val(m.group(1))), m.group(0), sent))
    return out


def numbers_in(text):
    """{noun: {number}} — numbers with the noun that follows them (skipping one modifier), e.g. 5 publications."""
    pairs = {}
    for m in re.finditer(NUM + r'(%|\+)?\s+([\w\-/]+)(?:\s+([\w\-/]+))?', text, re.I):
        n = m.group(1).lower()
        if re.fullmatch(r'(19|20)\d\d', n):
            continue   # a year, not a quantity
        try:
            v = val(n)
        except ValueError:
            continue
        for w in (m.group(3), m.group(4)):
            if w and len(w) > 3 and w.isalpha():
                noun = w.lower().rstrip('s')
                if noun in ('year', 'month', 'jahr', 'jahre', 'monat', 'monate'):
                    break
                pairs.setdefault(noun, set()).add(v)
                break
    return pairs


def repeated_phrases(lines, min_tokens=5):
    toks = [re.findall(r'[\w/\-]+', l.lower()) for l in lines]
    found = []
    for i in range(len(toks)):
        for j in range(i + 1, len(toks)):
            sm = difflib.SequenceMatcher(None, toks[i], toks[j], autojunk=False)
            m = sm.find_longest_match(0, len(toks[i]), 0, len(toks[j]))
            if m.size >= min_tokens:
                phrase = ' '.join(toks[i][m.a:m.a + m.size])
                if not any(phrase in f or f in phrase for f in found):
                    found.append(phrase)
    return found


# ---------- screener wording (CV rules 19–20); heuristics, always ⚠️ ----------
OPEN = re.compile(r'open[- ]?(?:source|weights?)|open[- ]weight', re.I)
MODEL = re.compile(r'\b(?:Qwen|Llama|Mistral|Mixtral|Gemma|Phi|DeepSeek|Falcon|Yi|Granite)[-\s]?[\w.]*?\d[\w.]*\b', re.I)
# algorithm / method names → the plain-language words that count as a descriptor in the same line
ALGOS = {
    r'\b(?:Double |Dueling |Deep )?DQN\b|\bPPO\b|\bSAC\b|\bTD3\b|\bDDPG\b|\bA3C\b|\bTRPO\b': r'reinforcement|RL\b',
    r'\bQ?LoRA\b|\bPEFT\b': r'fine-?tun|parameter-efficient',
    r'\bDPO\b|\bGRPO\b|\bRLHF\b|\bKTO\b': r'align|preference|reinforcement|fine-?tun',
    r'\bGANs?\b|\bVAEs?\b': r'generative|neural|image',
    r'\bGNNs?\b': r'graph',
    r'\bLSTMs?\b|\bGRUs?\b|\bCRFs?\b': r'neural|recurrent|sequence|time[- ]series|tagging',
    r'\bMoE\b': r'mixture|expert|model',
}
KIND = re.compile(r'\b(?:language|project|programme|program|framework|method|algorithm|platform|tool|system|guideline|standard|model|paper|dataset|benchmark|twin|pipeline)\b', re.I)
CODENAME = re.compile(r'\b(?!GPT|CI\b)(?=[A-Za-z0-9]*\d)(?=[A-Za-z0-9]*[A-Z][^A-Z]*[A-Z])[A-Za-z0-9]{7,}\b')
TERM = re.compile(r'\b(?:[A-Z]{2,}[A-Za-z0-9]*(?:[-/][A-Za-z0-9]+)*|[A-Z][a-z]+[A-Z][A-Za-z0-9]*|[A-Za-z]+-as-[a-z]+|[a-z]+-calling|[A-Z][A-Za-z0-9]*\d[A-Za-z0-9.]*)\b')
TERM_SKIP = {'CV', 'EU', 'USA', 'DE', 'EN', 'PDF', 'ARR', 'KPI', 'KPIs', 'PoC', 'PoCs', 'MSc', 'BSc', 'TUM', 'TU', 'DFG', 'VDI', 'VDE', 'GmbH', 'AG', 'SE', 'API', 'APIs', 'REST', 'IT',
             'LLM', 'LLMs', 'AI', 'ML', 'NLP', 'GenAI'}  # generic category words double as descriptors (CV rule 19): they may repeat


def units_of(item):
    """Every text unit of a position: the 'what' line is skipped; each bullet and each sub-bullet is one unit."""
    out = []
    def walk(b):
        if isinstance(b, dict):
            out.append(b.get('text') or '')
            for x in b.get('sub') or []: walk(x)
        else:
            out.append(str(b))
    for b in item.get('bullets') or []: walk(b)
    return [u for u in out if u]


def screener_wording(cv_yaml):
    """⚠️ strings for CV rules 19–20 from the cv.yaml the PDF was rendered from."""
    import yaml
    d = yaml.safe_load(open(cv_yaml)) or {}
    warn = []
    texts = [('summary', [d.get('summary') or ''])]
    for sec in d.get('sections', []):
        if sec.get('kind') == 'entries':
            for it in sec.get('items', []):
                texts.append((it.get('what', '?').split('·')[-1].strip() or it.get('what', '?'), units_of(it)))
        elif sec.get('kind') == 'list':
            texts.append((sec.get('title', 'list'), [str(x.get('text') if isinstance(x, dict) else x) for x in sec.get('items', [])]))
    seen_gloss = set()
    for where, units in texts:
        for u in units:
            for m in MODEL.finditer(u):
                if not OPEN.search(u) and m.group(0).lower() not in seen_gloss:
                    seen_gloss.add(m.group(0).lower())
                    warn.append(f'{where}: model name "{m.group(0)}" without "open-source/open-weight LLM" next to it (CV rule 19)')
            for pat, ok in ALGOS.items():
                for m in re.finditer(pat, u):
                    if not re.search(ok, u, re.I) and m.group(0).lower() not in seen_gloss:
                        seen_gloss.add(m.group(0).lower())
                        warn.append(f'{where}: "{m.group(0)}" has no general term next to it (e.g. "reinforcement learning (…)", CV rule 19)')
            for m in CODENAME.finditer(u):
                if m.group(0).lower() not in seen_gloss and not KIND.search(u):
                    seen_gloss.add(m.group(0).lower())
                    warn.append(f'{where}: "{m.group(0)}" has no category next to it — keep the name and add what it is, e.g. "{m.group(0)}, a … language / project / method" (CV rule 19)')
        if where == 'summary' or len(units) < 2:
            continue
        count = {}
        for i, u in enumerate(units):
            for t in {m.group(0) for m in TERM.finditer(u)} - TERM_SKIP:
                count.setdefault(t, set()).add(i)
        rep = sorted(t for t, ix in count.items() if len(ix) >= 2)
        if rep:
            warn.append(f'{where}: {", ".join(rep[:8])} repeated across bullets — name each term once in a lead line, sub-bullets carry only use case and result (CV rule 20)')
    return warn


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cv', required=True); ap.add_argument('--letter'); ap.add_argument('--keywords', default='')
    ap.add_argument('--facts'); ap.add_argument('--max-pages', type=int, default=None); ap.add_argument('--company'); ap.add_argument('--cv-yaml')
    a = ap.parse_args()
    bad, warn, good = [], [], []

    pages = text_of(a.cv); cv = '\n'.join(pages)
    if any(len(p.strip()) < 200 for p in pages):
        bad.append('CV: a page has (almost) no text layer — ATS cannot read it (CV rule 4). Re-export as a text PDF.')
    else:
        good.append(f'CV text layer readable ({len(pages)} page(s), {len(cv)} characters)')
    limit = a.max_pages or 2
    if len(pages) > limit:
        bad.append(f'CV has {len(pages)} pages, limit {limit} (CV rule 1)')
    raw = [l for l in cv.splitlines() if l.strip()]
    if raw and sum(len(l.split()) == 1 for l in raw) / len(raw) > 0.25:
        bad.append('CV text extracts one word per line in places — ATS parsers will garble it. Usually a font embedding issue: '
                   're-export with a standard font (Arial) — see docs/pitfalls.md')
    yr_only = re.findall(r'(?<![/\w(])((?:19|20)\d\d)\s*[–-]\s*((?:19|20)\d\d|present|heute)\s*$', cv, re.M)
    if yr_only:
        warn.append('CV dates without month: ' + ', '.join(f'{x}–{y}' for x, y in yr_only[:5]) + ' — give MM/YYYY (CV rule 1)')
    for m in HOLLOW.finditer(cv):
        warn.append(f'CV hollow qualifier "{m.group(0)}" — let the bullets show the level (CV rule 8)')
    lines = [l.strip() for l in cv.splitlines() if len(l.split()) >= 4]
    for ph in repeated_phrases(lines):
        warn.append(f'CV repeats "{ph}" in more than one place — each achievement once (CV rule 9)')
    if a.cv_yaml and os.path.exists(a.cv_yaml):
        warn += screener_wording(a.cv_yaml)
    if a.company:
        fn = os.path.basename(a.cv)
        if not re.fullmatch(r'[A-Z][\w]*-[A-Z][\w\-]*-CV-.+\.pdf', fn):
            warn.append(f'CV file name "{fn}" — use FirstName-LastName-CV-{a.company}.pdf (CV rule 4)')

    letter = ''
    if a.letter:
        letter = '\n'.join(text_of(a.letter))
        ls = [l.strip() for l in letter.splitlines()]
        si = next((i for i, l in enumerate(ls) if SALUT.match(l)), None)
        ci = next((i for i, l in enumerate(ls) if CLOSE.match(l)), None)
        body = ' '.join(ls[(si + 1 if si is not None else 0):(ci if ci is not None else len(ls))])
        words = len(re.findall(r'\w+', body))
        (good if 300 <= words <= 450 else warn).append(f'letter body {words} words (target 300–450, letter rule 1)')
        if si is None: warn.append('letter: no salutation line found (letter rule 4)')
        if ci is None: warn.append('letter: no sign-off found (letter rule 9)')
        head = '\n'.join(ls[:si] if si else ls[:8])
        if not re.search(r'bewerbung als|application for|betreff|subject|ref\.|kennziffer', head, re.I):
            warn.append('letter: no subject line (Bewerbung als … / Application for …) above the salutation (letter rule 3)')
        first = body[:160].lower()
        for f in FILLER:
            if f in body.lower():
                (bad if f in first else warn).append(f'letter uses "{f}" (letter rules 5/11)')
        dashes = len(re.findall(r'\s[—–]\s|—', body))
        if dashes > 2: warn.append(f'letter has {dashes} dashes — use fewer (letter rule 11)')

    # durations vs fact bank
    if a.facts and os.path.exists(a.facts):
        import yaml
        from facts import months, say
        F = yaml.safe_load(open(a.facts)) or {}
        ents = [e for e in F.get('entries', []) if months(e)]
        def aliases(e):
            al = [e.get('org') or ''] + list(e.get('aliases') or [])
            return [x.lower() for x in al if x]
        for name, txt in (('CV', cv), ('letter', letter)):
            for mo, phrase, sent in durations_in(txt):
                # attribute the duration to the organisation named closest to it (within 120 characters)
                p = sent.lower().find(phrase.lower().strip())
                low = sent.lower(); tail = low[p + len(phrase.strip()):p + len(phrase.strip()) + 40]
                after = sorted((tail.find(x), id(e), e) for e in ents for x in aliases(e)
                               if x in tail and re.search(r'\b(at|bei|with|in|for|für|an der|am)\s+(the\s+)?$', tail[:tail.find(x)]))
                near = after or sorted((abs(low.find(x) - p), id(e), e) for e in ents for x in aliases(e)
                                       if x in low and abs(low.find(x) - p) <= 120)
                for _, _, e in near[:1]:
                    true = months(e)
                    at_least = '(at least)' in phrase
                    # "about / rund / ca. 2.5 years" is an approximation: allow ±3 months; the entry's own duration_wording is always fine
                    approx = re.search(r'\b(about|around|approximately|roughly|nearly|almost|over|more than|rund|etwa|ca\.?|circa|knapp|über|mehr als)\s*$',
                                       low[max(0, p - 20):p])
                    chosen = [str(w).lower() for w in (e.get('duration_wording') or {}).values()]
                    if any(w and w in low for w in chosen):
                        continue
                    if (at_least and true < mo) or (not at_least and abs(true - mo) >= (4 if approx else 2)):
                        bad.append(f'{name} says "{phrase.strip()}" about {e.get("org")}, fact bank: {e.get("start")}–{e.get("end")} = '
                                   f'{say(true)[0]} — use ' + (' / '.join(f'"{w}"' for w in (e.get('duration_wording') or {}).values()) or 'the exact duration') + ' (letter rule 12 / CV rule 16)')
    # numbers CV vs letter
    if letter:
        nc, nl = numbers_in(flow(cv)), numbers_in(flow(letter))
        cv_values = set().union(*nc.values()) if nc else set()
        for noun, vals in nl.items():
            if noun in nc and not vals & nc[noun] and not vals & cv_values:
                bad.append(f'letter says {sorted(vals)} {noun}(s), CV says {sorted(nc[noun])} — make them identical')
        dl = {round(m) for m, _, _ in durations_in(letter)}; dc = {round(m) for m, _, _ in durations_in(cv)}
        for m in sorted(dl - dc):
            warn.append(f'letter mentions a duration of {m} months that the CV does not state — check it')
    # keywords
    for kw in [k for k in a.keywords.split(',') if k.strip()]:
        alts = [x.strip().lower() for x in kw.split('|')]
        inc = any(x in cv.lower() for x in alts); inl = any(x in letter.lower() for x in alts) if letter else None
        where = f"CV {'✓' if inc else '✗'}" + (f", letter {'✓' if inl else '✗'}" if letter else '')
        (good if inc and (inl is None or inl) else bad).append(f'keyword "{alts[0]}": {where} (letter rule 13)')

    for x in good: print('✅', x)
    for x in warn: print('⚠️ ', x)
    for x in bad: print('❌', x)
    print(f'\n{len(bad)} to fix, {len(warn)} to look at.')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
