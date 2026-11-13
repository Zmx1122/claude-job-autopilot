"""Scan filters as run-time inputs: the profile gives the defaults, each run can widen (or tighten) them.

usage:
  python3 tools/filters.py show [--preset wide] [--set search.posted_within_days=10 ...]
  python3 tools/filters.py salary "75.000 € – 90.000 €"        # what the parser reads from a salary string

Why: a user who is not happy with today's list says "show more" / "放宽" and the next run uses a wider net, without
editing config/profile.yaml. dedupe.py takes the same --preset / --set flags; this module is the one place that merges them.

Resolution order (later wins):  config/profile.yaml  →  --preset NAME  →  --set key=value (repeatable)
A key is a dotted path into the profile, the value is YAML:  --set search.company_size=any  --set strategy.fit_medium=55

Presets (built in; the profile may override or add some under `scan_presets:`)
  default     the profile exactly as written
  wide        salary filter off · posting window 7 days · fit_medium 60 · jobs shortlisted on earlier days show again
  everything  wide, plus window 14 days · fit_medium 50 · startups allowed · no seniority hint

Never widened by a preset (only by an explicit --set): blacklist_companies, exclude_titles, skip_title_keywords, skip_agencies,
and jobs already Applied / Rejected / Confirmed in the tracker.

Keys that the filters understand (all optional):
  search.posted_within_days    drop postings older than this (unknown age is kept)
  search.salary_filter         on | off        (off = never drop on salary)
  search.salary_rules          {large_min_eur, small_min_eur, unstated: estimate|skip|keep}   → compared with the top of a stated range
  search.min_salary_eur        flat bar, used when no salary_rules are given (0 = none)
  search.company_size          established → drop size "startup";  any → keep startups
  search.resurface_shortlisted true → jobs the tracker has as Shortlisted (from earlier scans) are shown again
  strategy.fit_medium          drop fit below this
"""
import copy, re, sys

BUILTIN_PRESETS = {
    'default': {},
    'wide': {
        'search.posted_within_days': 7,
        'search.salary_filter': 'off',
        'strategy.fit_medium': 60,
        'search.resurface_shortlisted': True,
    },
    'everything': {
        'search.posted_within_days': 14,
        'search.salary_filter': 'off',
        'strategy.fit_medium': 50,
        'search.company_size': 'any',
        'search.resurface_shortlisted': True,
        'search.seniority': [],
    },
}


def _yaml(v):
    import yaml
    try:
        return yaml.safe_load(v)
    except Exception:
        return v


def set_path(d, dotted, value):
    parts = dotted.split('.')
    for p in parts[:-1]:
        if not isinstance(d.get(p), dict):
            d[p] = {}
        d = d[p]
    d[parts[-1]] = value


def parse_set(arg):
    if '=' not in arg:
        raise SystemExit(f'--set needs key=value, got: {arg}')
    k, v = arg.split('=', 1)
    return k.strip(), _yaml(v.strip())


def presets(profile):
    out = {k: dict(v) for k, v in BUILTIN_PRESETS.items()}
    for name, over in (profile.get('scan_presets') or {}).items():
        out.setdefault(name, {}).update(over or {})
    return out


def effective(profile, preset=None, sets=()):
    """Return (profile_with_overrides, [human readable list of what was changed])."""
    prof = copy.deepcopy(profile)
    changes = []
    if preset and preset != 'default':
        table = presets(profile)
        if preset not in table:
            raise SystemExit(f'unknown preset "{preset}". Known: {", ".join(sorted(table))}')
        for k, v in table[preset].items():
            set_path(prof, k, v)
            changes.append(f'{k}={v}')
    for s in sets or ():
        k, v = parse_set(s)
        set_path(prof, k, v)
        changes.append(f'{k}={v}')
    return prof, changes


# ---------- salary ----------
def parse_salary(text):
    """'75.000 € – 90.000 €' / '60K €/yr – 80K €/yr' / '80-95k' / '110000 EUR' → (low, high) in the written currency, or None."""
    if text in (None, ''):
        return None
    t = str(text)
    has_k = bool(re.search(r'\d\s*[kK]\b', t))
    nums = []
    for m in re.finditer(r'(\d{1,3}(?:[.,]\d{3})+|\d+(?:[.,]\d+)?)\s*([kK])?\b', t):
        raw, k = m.group(1), m.group(2)
        if re.fullmatch(r'\d{1,3}(?:[.,]\d{3})+', raw):
            val = float(re.sub(r'[.,]', '', raw))
        else:
            val = float(raw.replace(',', '.'))
        if k or (has_k and val < 1000):
            val *= 1000
        if val >= 1000:
            nums.append(val)
    if not nums:
        return None
    return min(nums), max(nums)


def salary_decision(job, search):
    """None = keep, else a reason string. Honors search.salary_filter / salary_rules / min_salary_eur."""
    if str(search.get('salary_filter', 'on')).lower() in ('off', 'false', 'no', '0'):
        return None
    rules = search.get('salary_rules') or {}
    large = rules.get('large_min_eur') or search.get('min_salary_eur') or 0
    small = rules.get('small_min_eur') or large
    if not large and not small:
        return None
    text = job.get('salary') or ''
    estimated = job.get('salary_estimated') or re.search(r'gesch(ä|ae)tzt|estimat', str(text), re.I)
    rng = None if estimated else parse_salary(text)
    if rng is None:
        policy = (rules.get('unstated') or 'estimate').lower()
        return 'salary unstated' if policy == 'skip' else None
    bar = small if job.get('size') == 'startup' else large
    return f'salary up to {int(rng[1]):,} < {int(bar):,}' if rng[1] < bar else None


# ---------- platform date parameters ----------
def _bucket(days, buckets):
    for b in buckets:
        if days <= b:
            return b
    return buckets[-1]


def platform_params(days):
    days = max(1, int(days))
    return {
        'linkedin': f'f_TPR=r{days * 86400}',
        'stepstone': f'ag=age_{_bucket(days, [1, 3, 7, 14, 30])}   (age_2 is ignored by StepStone; 1, 3, 7, 14 verified)',
        'indeed': f'fromage={_bucket(days, [1, 3, 7, 14])}',
        'xing': 'no URL parameter: read the "Vor N Tagen" text, or use the sidebar filter (24 h / week / month)',
    }


def show(profile, preset, sets):
    prof, changes = effective(profile, preset, sets)
    s, st = prof.get('search') or {}, prof.get('strategy') or {}
    days = s.get('posted_within_days') or 2
    rules = s.get('salary_rules') or {}
    print(f"preset: {preset or 'default'}" + (f"  overrides: {', '.join(changes)}" if changes else ''))
    print(f"posted within:      {days} days   → " + ' · '.join(f'{k}: {v}' for k, v in platform_params(days).items() if k != 'xing'))
    print(f"                    Xing: {platform_params(days)['xing']}")
    off = str(s.get('salary_filter', 'on')).lower() in ('off', 'false', 'no', '0')
    print('salary:             ' + ('off' if off else (f"large ≥ {rules.get('large_min_eur') or s.get('min_salary_eur') or 0}, small ≥ {rules.get('small_min_eur') or rules.get('large_min_eur') or 0}, unstated: {rules.get('unstated', 'estimate')}")))
    print(f"fit shown from:     {st.get('fit_medium', 60)}")
    print(f"company size:       {s.get('company_size', 'any')}   (established = no startups)")
    print(f"shortlisted before: {'shown again' if s.get('resurface_shortlisted') else 'hidden'}")
    print(f"titles ({len(s.get('titles') or [])}) × locations ({len(s.get('locations') or [])}): "
          f"{', '.join((s.get('titles') or [])[:6])}{' …' if len(s.get('titles') or []) > 6 else ''}  |  {', '.join(s.get('locations') or [])}")
    print('always on:          blacklist, exclude_titles, skip_title_keywords, ' + ('no recruiting agencies, ' if s.get('skip_agencies') else '') + 'already Applied/Rejected in the tracker')


def main(argv):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    a = sub.add_parser('show'); a.add_argument('--preset'); a.add_argument('--set', action='append', default=[])
    b = sub.add_parser('salary'); b.add_argument('text')
    args = ap.parse_args(argv)
    if args.cmd == 'show':
        from common import load_profile
        show(load_profile(), args.preset, args.set)
    else:
        print(parse_salary(args.text))


if __name__ == '__main__':
    main(sys.argv[1:])
