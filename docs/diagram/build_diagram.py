"""Build the README flow diagram as an editable draw.io file and a matching SVG from one layout spec.

usage: python3 docs/diagram/build_diagram.py   → docs/diagram/flow.drawio + docs/diagram/flow.svg
Open flow.drawio in draw.io / diagrams.net to edit by hand; re-running this script overwrites both files.
"""
import os, html
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))
W, LEFT = 1120, 150                     # canvas width, phase-label column
LANES = {'you': (LEFT + 20, 280), 'claude': (LEFT + 360, 320), 'svc': (LEFT + 740, 220)}   # x, width
LANE_TITLE = {'you': ('You', '你'), 'claude': ('Claude (desktop app)', 'Claude 桌面端'), 'svc': ('Services', '外部服务')}
STYLE = {  # fill, stroke, title colour
    'you': ('#FFF5E6', '#E3A13B', '#7A4B00'),
    'claude': ('#FBEDE6', '#D97757', '#7A3418'),
    'svc': ('#EEF3FA', '#5B7DB1', '#23426E'),
    'gate': ('#E9F6EE', '#2E9650', '#145A2B'),
}
PHASES = [  # title_en, title_zh, y0, y1
    ('Set up once', '一次性配置', 64, 352),
    ('Every morning, automatic', '每天早上 · 自动', 364, 548),
    ('Apply session, with you', '投递 · 你在场', 560, 936),
    ('Every week', '每周', 948, 1040),
]
NODES = [  # id, lane, y-centre, english, chinese, kind
    ('kb_u', 'you', 113, 'Drop CVs + certificates,\nanswer the questionnaire', '上传简历证书，回答问卷', 'you'),
    ('kb_c', 'claude', 113, 'Build knowledge base\n+ config/profile.yaml', '建立知识库与个人档案', 'claude'),
    ('cred_u', 'you', 208, 'Create Notion token +\nGmail app password', '创建 Notion token 与 Gmail 应用密码', 'you'),
    ('cred_c', 'claude', 208, 'Create tracker database,\nGmail label "applications"', '建 Notion 表、Gmail 标签', 'claude'),
    ('cred_s', 'svc', 208, 'Notion · Gmail', '', 'svc'),
    ('login_u', 'you', 303, 'Log in to job sites in\nClaude\'s browser, allow uploads', '在 Claude 浏览器登录各平台，开上传权限', 'you'),
    ('login_c', 'claude', 303, 'Check setup, schedule\ndaily + weekly tasks', '检查配置，创建定时任务', 'claude'),
    ('mail_c', 'claude', 411, 'Mail sync: classify emails,\nupdate status, add label', '邮件同步：分类、更新状态、打标签', 'claude'),
    ('mail_s', 'svc', 411, 'Gmail → Notion', '确认信 · 面试 · 拒信', 'svc'),
    ('scan_c', 'claude', 502, 'Scan · dedupe · filter\n(company size, cover letter …)', '扫描、去重、按规则筛选', 'claude'),
    ('scan_s', 'svc', 502, 'LinkedIn · StepStone\nIndeed · Xing', '', 'svc'),
    ('short_c', 'claude', 610, 'Shortlist table in chat', '聊天里给出精选岗位表', 'claude'),
    ('pick_u', 'you', 610, 'Pick jobs  ("1, 3, 5")', '选择要投的岗位', 'you'),
    ('fill_c', 'claude', 703, 'Prefill each job to its review\npage: CV choice, answers, uploads', '逐个填到确认页：选简历、答题、上传', 'claude'),
    ('hand_u', 'you', 703, 'CAPTCHA · account · missing file', '验证码 / 注册 / 缺材料 → 你来', 'you'),
    ('ready_c', 'claude', 796, 'Ready list', '待提交清单', 'claude'),
    ('ok_u', 'you', 796, 'Confirm once  ✓', '确认一次', 'gate'),
    ('send_c', 'claude', 886, 'Submit all, log each row', '全部提交并逐条记录', 'claude'),
    ('send_s', 'svc', 886, 'Platforms + company portals\nNotion tracker', '平台与公司官网 · Notion', 'svc'),
    ('dash_c', 'claude', 994, 'Refresh Notion charts +\ninteractive dashboard', '刷新 Notion 图表与交互看板', 'claude'),
    ('dash_s', 'svc', 994, 'Notion page · claude.ai', '', 'svc'),
]
EDGES = [  # from, to, label, dashed
    ('kb_u', 'kb_c', '', False), ('cred_u', 'cred_c', '', False), ('cred_c', 'cred_s', '', False), ('login_u', 'login_c', '', False),
    ('kb_c', 'cred_c', '', False), ('cred_c', 'login_c', '', False),
    ('login_c', 'mail_c', 'schedule', True),
    ('mail_c', 'mail_s', '', False), ('mail_c', 'scan_c', '', False), ('scan_s', 'scan_c', '', False),
    ('scan_c', 'short_c', '', False), ('short_c', 'pick_u', '', False), ('pick_u', 'fill_c', '', False),
    ('fill_c', 'hand_u', 'if needed', True), ('fill_c', 'ready_c', '', False), ('ready_c', 'ok_u', '', False),
    ('ok_u', 'send_c', '', False), ('send_c', 'send_s', '', False), ('dash_c', 'dash_s', '', False),
]
H_ONE, H_TWO = 50, 62
N = {}
for nid, lane, y, en, zh, kind in NODES:
    x, w = LANES[lane]
    h = H_TWO if '\n' in en or (zh and len(en) > 0 and '\n' in en) else H_ONE
    if '\n' in en and zh: h = 70
    N[nid] = dict(x=x, y=y - h / 2, w=w, h=h, cx=x + w / 2, cy=y, en=en, zh=zh, kind=kind, lane=lane)

def anchor(a, b):
    """Edge endpoints: side-to-side when lanes differ, bottom-to-top within a lane; returns path points."""
    A, B = N[a], N[b]
    if A['lane'] == B['lane']:
        return [(A['cx'], A['y'] + A['h']), (B['cx'], B['y'])]
    ax = A['x'] + A['w'] if B['cx'] > A['cx'] else A['x']
    bx = B['x'] if B['cx'] > A['cx'] else B['x'] + B['w']
    if abs(A['cy'] - B['cy']) < 1:
        return [(ax, A['cy']), (bx, B['cy'])]
    # L-shape: leave sideways, go vertically in the gap, enter sideways
    mx = (ax + bx) / 2
    down = B['cy'] > A['cy']
    ya, yb = A['cy'] + (14 if down else -14), B['cy'] - (14 if down else -14)   # keep clear of straight arrows at centre height
    return [(ax, ya), (mx, ya), (mx, yb), (bx, yb)]

H = PHASES[-1][3] + 30

# ---------------- SVG ----------------
F = "font-family=\"-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,'PingFang SC','Microsoft YaHei',sans-serif\""
svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" {F}>',
       '<defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
       '<path d="M0,0 L10,5 L0,10 z" fill="#6B6862"/></marker></defs>',
       f'<rect x="0" y="0" width="{W}" height="{H}" rx="18" fill="#FFFFFF"/>']
for lane, (x, w) in LANES.items():
    en, zh = LANE_TITLE[lane]; c = STYLE[lane][2]
    svg.append(f'<text x="{x + w / 2}" y="34" text-anchor="middle" font-size="15" font-weight="700" fill="{c}">{escape(en)} <tspan font-weight="400" fill="#8A867F">· {zh}</tspan></text>')
for i, (en, zh, y0, y1) in enumerate(PHASES):
    fill = '#FAF9F7' if i % 2 == 0 else '#F4F2EE'
    svg.append(f'<rect x="12" y="{y0}" width="{W - 24}" height="{y1 - y0}" rx="12" fill="{fill}"/>')
    svg.append(f'<text x="28" y="{y0 + 30}" font-size="14" font-weight="700" fill="#3B3934">{i + 1}</text>')
    yy = y0 + 52
    for j, part in enumerate(en.split(', ')):
        svg.append(f'<text x="28" y="{yy + j * 17}" font-size="13" font-weight="600" fill="#3B3934">{escape(part)}</text>')
    svg.append(f'<text x="28" y="{yy + len(en.split(", ")) * 17 + 4}" font-size="12" fill="#8A867F">{zh}</text>')
for a, b, label, dashed in EDGES:
    pts = anchor(a, b)
    d = 'M' + ' L'.join(f'{x:.0f},{y:.0f}' for x, y in pts)
    svg.append(f'<path d="{d}" fill="none" stroke="#6B6862" stroke-width="1.6"{" stroke-dasharray=\"5 4\"" if dashed else ""} marker-end="url(#arr)"/>')
    if label:
        (x1, y1), (x2, y2) = pts[0], pts[-1]
        lx, ly = ((x1 + x2) / 2, (y1 + y2) / 2 + 17) if len(pts) == 2 else (pts[1][0] + 6, (pts[1][1] + pts[2][1]) / 2)
        anchor_ = 'middle' if len(pts) == 2 and abs(y1 - y2) < 1 else 'start'
        if len(pts) == 2 and abs(x1 - x2) < 1: lx, ly, anchor_ = x1 + 8, (y1 + y2) / 2 + 4, 'start'
        svg.append(f'<text x="{lx:.0f}" y="{ly:.0f}" font-size="11" fill="#6B6862" text-anchor="{anchor_}" font-style="italic">{escape(label)}</text>')
for nid, n in N.items():
    fill, stroke, tc = STYLE[n['kind']]
    sw = 2.4 if n['kind'] == 'gate' else 1.4
    svg.append(f'<rect x="{n["x"]}" y="{n["y"]:.0f}" width="{n["w"]}" height="{n["h"]:.0f}" rx="10" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
    lines = n['en'].split('\n'); total = len(lines) + (1 if n['zh'] else 0)
    y = n['cy'] - (total - 1) * 8 + 4
    for ln in lines:
        svg.append(f'<text x="{n["cx"]}" y="{y:.0f}" text-anchor="middle" font-size="13" font-weight="600" fill="{tc}">{escape(ln)}</text>'); y += 16
    if n['zh']:
        svg.append(f'<text x="{n["cx"]}" y="{y + 1:.0f}" text-anchor="middle" font-size="11.5" fill="#6F6B64">{escape(n["zh"])}</text>')
svg.append('</svg>')
open(os.path.join(HERE, 'flow.svg'), 'w').write('\n'.join(svg))

# ---------------- draw.io ----------------
cells = ['<mxCell id="0"/>', '<mxCell id="1" parent="0"/>']
k = 0
def cid():
    global k; k += 1; return f'c{k}'
for i, (en, zh, y0, y1) in enumerate(PHASES):
    v = html.escape(f'<b>{i + 1} · {en}</b><br><font color="#8A867F">{zh}</font>')
    cells.append(f'<mxCell id="{cid()}" value="{v}" style="rounded=1;arcSize=4;whiteSpace=wrap;html=1;fillColor={"#FAF9F7" if i % 2 == 0 else "#F4F2EE"};strokeColor=none;align=left;verticalAlign=top;spacingLeft=14;spacingTop=10;fontSize=13;" vertex="1" parent="1"><mxGeometry x="12" y="{y0}" width="{W - 24}" height="{y1 - y0}" as="geometry"/></mxCell>')
for lane, (x, w) in LANES.items():
    en, zh = LANE_TITLE[lane]
    v = html.escape(f'<b>{en}</b> · {zh}')
    cells.append(f'<mxCell id="{cid()}" value="{v}" style="text;html=1;align=center;fontSize=15;fontColor={STYLE[lane][2]};" vertex="1" parent="1"><mxGeometry x="{x}" y="14" width="{w}" height="30" as="geometry"/></mxCell>')
for nid, n in N.items():
    fill, stroke, tc = STYLE[n['kind']]
    v = html.escape(f'<b>{n["en"].replace(chr(10), "<br>")}</b>' + (f'<br><font style="font-size:11px" color="#6F6B64">{n["zh"]}</font>' if n['zh'] else ''))
    cells.append(f'<mxCell id="{nid}" value="{v}" style="rounded=1;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};strokeWidth={2.4 if n["kind"] == "gate" else 1.4};fontColor={tc};fontSize=13;" vertex="1" parent="1"><mxGeometry x="{n["x"]}" y="{n["y"]:.0f}" width="{n["w"]}" height="{n["h"]:.0f}" as="geometry"/></mxCell>')
for a, b, label, dashed in EDGES:
    cells.append(f'<mxCell id="{cid()}" value="{html.escape(label)}" style="edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;strokeColor=#6B6862;strokeWidth=1.6;endArrow=block;endFill=1;fontSize=11;fontStyle=2;{"dashed=1;" if dashed else ""}" edge="1" parent="1" source="{a}" target="{b}"><mxGeometry relative="1" as="geometry"/></mxCell>')
xml = (f'<mxfile host="build_diagram.py"><diagram name="Job Autopilot flow" id="flow"><mxGraphModel dx="{W}" dy="{H}" grid="1" gridSize="10" '
       f'guides="1" page="1" pageWidth="{W}" pageHeight="{H}" background="#FFFFFF"><root>' + ''.join(cells) + '</root></mxGraphModel></diagram></mxfile>')
open(os.path.join(HERE, 'flow.drawio'), 'w').write(xml)
print('wrote flow.svg and flow.drawio')
