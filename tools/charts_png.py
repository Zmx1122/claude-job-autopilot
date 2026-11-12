"""Render pie, flow and weekly charts as PNGs with Pillow (no matplotlib needed) from dashboard/data.json."""
import json, os, sys, math
from PIL import Image, ImageDraw, ImageFont
from common import DATA
OUT = os.path.join(DATA, 'dashboard'); os.makedirs(OUT, exist_ok=True)
d = json.load(open(sys.argv[1] if len(sys.argv) > 1 else os.path.join(OUT, 'data.json'))); S = 2  # supersample
def font(sz, bold=False):
    for f in (['/System/Library/Fonts/Supplemental/Arial Bold.ttf'] if bold else []) + ['/System/Library/Fonts/Supplemental/Arial.ttf', '/System/Library/Fonts/Helvetica.ttc', '/Library/Fonts/Arial.ttf']:
        if os.path.exists(f):
            try: return ImageFont.truetype(f, sz * S)
            except Exception: pass
    return ImageFont.load_default()
BG = (255, 255, 255); FG = (31, 30, 28); MUTED = (120, 116, 110); GRID = (229, 226, 221)
COL = {'Applied': (96, 125, 189), 'Confirmed': (84, 160, 143), 'Interview': (222, 150, 58), 'Offer': (46, 150, 78), 'Rejected': (196, 78, 70), 'Withdrawn': (170, 166, 160), 'Skipped': (170, 166, 160),
       'LinkedIn': (96, 125, 189), 'StepStone': (84, 160, 143), 'Indeed': (222, 150, 58), 'Xing': (139, 110, 190), 'Other': (170, 166, 160)}
def new(w, h): return Image.new('RGB', (w * S, h * S), BG), ImageDraw.Draw(Image.new('RGB', (1, 1)))
def save(img, name): img.resize((img.width // S, img.height // S), Image.LANCZOS).save(os.path.join(OUT, name), optimize=True); print('wrote', name)
def text(dr, xy, s, sz=13, fill=FG, bold=False, anchor='la'): dr.text((xy[0] * S, xy[1] * S), s, font=font(sz, bold), fill=fill, anchor=anchor)

# ---- pie ----
order = ['Applied', 'Confirmed', 'Interview', 'Offer', 'Rejected', 'Withdrawn', 'Skipped']
bs = d['by_status']; total = d['total']
if not total: raise SystemExit('No applications yet; nothing to chart.')
img = Image.new('RGB', (760 * S, 360 * S), BG); dr = ImageDraw.Draw(img)
cx, cy, R, r = 180, 180, 150, 88; a = -90
for s in order:
    n = bs.get(s, 0)
    if not n: continue
    sweep = 360 * n / total
    dr.pieslice([(cx - R) * S, (cy - R) * S, (cx + R) * S, (cy + R) * S], a, a + sweep, fill=COL[s], outline=BG, width=3 * S)
    if n / total >= 0.08:
        mid = math.radians(a + sweep / 2); text(dr, (cx + math.cos(mid) * (R + r) / 2, cy + math.sin(mid) * (R + r) / 2), str(n), 15, BG, True, 'mm')
    a += sweep
dr.ellipse([(cx - r) * S, (cy - r) * S, (cx + r) * S, (cy + r) * S], fill=BG)
text(dr, (cx, cy - 10), str(total), 34, FG, False, 'mm'); text(dr, (cx, cy + 22), 'jobs tracked', 13, MUTED, False, 'mm')
_bs = d['by_status']; _sent = sum(_bs.values()) - _bs.get('Skipped', 0) - _bs.get('Shortlisted', 0) - _bs.get('Seen', 0)
text(dr, (380, 40), f"Total applications: {_sent}", 17, FG, True)
y = 80
for s in order:
    n = bs.get(s, 0)
    if not n: continue
    dr.rounded_rectangle([380 * S, y * S, 394 * S, (y + 14) * S], radius=3 * S, fill=COL[s]); text(dr, (404, y - 1), f'{s}  {n}  ({n / total:.0%})', 14)
    y += 28
text(dr, (380, y + 8), 'Applied = platform receipt only. Confirmed = company acknowledged.', 11, MUTED)
save(img, 'pie.png')

# ---- flow (stacked children under each stage, like the dashboard) ----
links = d['sankey']; W, H = 960, 420; padL, padR, padT, padB, nodeW, gap = 20, 230, 40, 20, 12, 8
total = sum(l['value'] for l in links if l['source'] == 'Applied'); scale = (H - padT - padB - gap * 4) / total
stages = ['Applied', 'Confirmed', 'Interview', 'Offer']
def kind(name): return 'progress' if name in stages else 'waiting' if name.startswith('Waiting') else 'rejected' if name == 'Rejected' else 'withdrawn'
# split terminal nodes per source
rows = []
for l in links:
    tgt = l['target'] if l['target'] in stages or l['target'].startswith('Waiting') else f"{l['target']} after {l['source'].lower()}"
    rows.append(dict(source=l['source'], target=tgt, value=l['value'], kind=kind(l['target']), column=stages.index(l['source']) + 1))
rank = {'progress': 0, 'waiting': 1, 'rejected': 2, 'withdrawn': 3}; rows.sort(key=lambda l: (l['column'], rank[l['kind']]))
nodes = {'Applied': dict(col=0, kind='progress', y=padT, h=total * scale, out=0)}
for l in rows: n = nodes.setdefault(l['target'], dict(col=l['column'], kind=l['kind'], h=0, out=0)); n['h'] += l['value'] * scale
for s in stages[:3]:
    src = nodes.get(s); y = src['y'] if src else None
    for l in [l for l in rows if l['source'] == s]: nodes[l['target']]['y'] = y; y += nodes[l['target']]['h'] + gap
# Later columns hold few applications and would bunch up at the top: keep the stage node (Interview, Offer) at the top and
# spread the exits (waiting / rejected / withdrawn) evenly down to the bottom edge. Band widths stay proportional.
MINH = 4
for c in (2, 3):
    col = [n for n in nodes.values() if n['col'] == c]
    prog = [n for n in col if n['kind'] == 'progress']; rest = sorted([n for n in col if n['kind'] != 'progress'], key=lambda n: n['y'])
    if not rest: continue
    top = (prog[0]['y'] + max(prog[0]['h'], MINH) + gap * 3) if prog else padT
    free = (H - padB) - top - sum(max(n['h'], MINH) for n in rest)
    step = free / (len(rest) - 1) if len(rest) > 1 else 0
    if free <= 0: continue
    y = top if len(rest) > 1 else top + free / 2
    for n in rest: n['y'] = y; y += max(n['h'], MINH) + step
colX = lambda c: padL + c * ((W - padL - padR - nodeW) / 3)
KC = {'progress': COL['Applied'], 'waiting': (200, 196, 190), 'rejected': COL['Rejected'], 'withdrawn': (170, 166, 160)}
img = Image.new('RGB', (W * S, H * S), BG); dr = ImageDraw.Draw(img)
def bezier(x0, y0, x1, y1, steps=40):
    xm = (x0 + x1) / 2; pts = []
    for i in range(steps + 1):
        t = i / steps; x = (1-t)**3*x0 + 3*(1-t)**2*t*xm + 3*(1-t)*t**2*xm + t**3*x1; yy = (1-t)**3*y0 + 3*(1-t)**2*t*y0 + 3*(1-t)*t**2*y1 + t**3*y1; pts.append((x, yy))
    return pts
overlay = Image.new('RGBA', img.size, (0, 0, 0, 0)); od = ImageDraw.Draw(overlay)
for l in rows:
    s, t = nodes[l['source']], nodes[l['target']]; w = l['value'] * scale
    x0, x1 = colX(s['col']) + nodeW, colX(t['col']); y0 = s['y'] + s['out'] + w / 2; s['out'] += w; y1 = t['y'] + max(t['h'], MINH) / 2
    top = bezier(x0, y0 - w / 2, x1, y1 - w / 2); bot = bezier(x0, y0 + w / 2, x1, y1 + w / 2)
    od.polygon([(x * S, y * S) for x, y in top + bot[::-1]], fill=KC[l['kind']] + (110 if l['kind'] == 'progress' else 80,))
img.paste(Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')); dr = ImageDraw.Draw(img)
for name, n in nodes.items():
    x = colX(n['col']); dr.rounded_rectangle([x * S, n['y'] * S, (x + nodeW) * S, (n['y'] + max(MINH, n['h'])) * S], radius=2 * S, fill=KC[n['kind']])
    cnt = round(n['h'] / scale)
    if n['kind'] == 'progress': text(dr, (x, n['y'] - 22), f'{name}  {cnt}', 14, FG, True)
# side labels with collision push
for c in (1, 2, 3):
    last = -1e9
    for name, n in sorted([(k, v) for k, v in nodes.items() if v['col'] == c and v['kind'] != 'progress'], key=lambda kv: kv[1]['y']):
        ly = max(n['y'] + max(MINH, n['h']) / 2, last + 16); last = ly; text(dr, (colX(c) + nodeW + 8, ly), f"{name}  {round(n['h'] / scale)}", 12, MUTED, False, 'lm')
save(img, 'flow.png')

# ---- weekly stacked bars ----
wk = d['weekly']; plats = [p for p in ['LinkedIn', 'StepStone', 'Indeed', 'Xing', 'Other'] if any(w.get(p) for w in wk)]
W, H = 960, 300; mL, mR, mT, mB = 40, 20, 30, 50
img = Image.new('RGB', (W * S, H * S), BG); dr = ImageDraw.Draw(img)
ymax = max(w['total'] for w in wk) or 1; ymax = math.ceil(ymax / 5) * 5
for t in range(0, ymax + 1, 5):
    yy = mT + (H - mT - mB) * (1 - t / ymax); dr.line([mL * S, yy * S, (W - mR) * S, yy * S], fill=GRID, width=S); text(dr, (mL - 8, yy), str(t), 11, MUTED, False, 'rm')
bw = (W - mL - mR) / len(wk); bar = bw * 0.7
for i, w in enumerate(wk):
    x0 = mL + i * bw + (bw - bar) / 2; y = mT + (H - mT - mB)
    for p in plats:
        n = w.get(p, 0)
        if not n: continue
        h = (H - mT - mB) * n / ymax; dr.rounded_rectangle([x0 * S, (y - h) * S, (x0 + bar) * S, y * S], radius=2 * S, fill=COL[p]); y -= h + 1
    text(dr, (x0 + bar / 2, H - mB + 14), 'W' + w['week'][6:], 11, MUTED, False, 'mm')
x = mL
for p in plats:
    dr.rounded_rectangle([x * S, (H - 18) * S, (x + 12) * S, (H - 6) * S], radius=2 * S, fill=COL[p]); lbl = f"{p} {sum(w.get(p, 0) for w in wk)}"; text(dr, (x + 18, H - 12), lbl, 12, MUTED, False, 'lm'); x += 18 + len(lbl) * 8 + 16
text(dr, (mL, 8), 'Applications per week by platform', 15, FG, True)
save(img, 'weekly.png')
