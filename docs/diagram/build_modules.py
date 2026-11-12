"""Build the README module map ("what is inside") as an editable draw.io file and a matching SVG, in the style of flow.svg.

usage: python3 docs/diagram/build_modules.py   → docs/diagram/modules.drawio + docs/diagram/modules.svg
Grid: four areas (columns) × four layers (rows): skills → scripts and rules → files on your computer → online services.
"""
import os, html
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))
W, LEFT, GAP = 1120, 160, 14
COLS = [('Your documents', '你的材料'), ('Applying', '投递'), ('Tracking', '跟踪'), ('Setup & safety', '配置与安全')]
CW = (W - LEFT - 20 - GAP * (len(COLS) - 1)) / len(COLS)
STYLE = {  # fill, stroke, title colour
    'skill': ('#FBEDE6', '#D97757', '#7A3418'),
    'tool': ('#F3F2EF', '#9B968C', '#3B3934'),
    'data': ('#FFF5E6', '#E3A13B', '#7A4B00'),
    'svc': ('#EEF3FA', '#5B7DB1', '#23426E'),
    'you': ('#E9F6EE', '#2E9650', '#145A2B'),
}
# rows: key, title_en, title_zh, style, height, cells (one per column: title, lines, zh) — None = empty
ROWS = [
    ('skill', 'Skills', '技能 · .claude/skills', 'skill', 112, [
        ('job-knowledge-base\njob-career-coach\njob-application-writer', 'documents → unit files;\nno CV → interview; CVs + letters', '材料拆分 · 求职教练 · 简历与求职信'),
        ('job-scan-apply', 'scan → shortlist (tailored / template)\n→ you pick → prefill → you confirm', '扫描、精选、预填、确认后提交'),
        ('job-mail-sync\njob-dashboard', 'emails → statuses + label;\ncharts every week', '邮件同步与打标签 · 看板'),
        ('job-autopilot-setup', 'zero to running: questionnaire,\ntokens, logins, schedule, backup', '从零配置'),
    ]),
    ('tool', 'Scripts and rules', '脚本与规则 · tools/ · standards/', 'tool', 128, [
        ('kb_extract · kb_build\nkb_bundle · facts\ndoc_render · doc_check', 'standards/de: CV, Anschreiben,\nwhen to tailor, market notes', '拆分合并 PDF · 事实库 · 生成与检查'),
        ('dedupe · log_application\nupload_file · copy_path', 'mode per job, daily cap,\nNotion row per action, uploads', '去重筛选 · 记录 · 文件上传'),
        ('gmail_dump · sync_mail\nlabel_mail · dashboard_data\ncharts_png · notion_page', 'classify, match, label;\nweekly charts', '邮件分类匹配 · 看板数据'),
        ('check_setup · backup\ncheck_public', 'health check, backup and restore,\nprivacy guard before commits', '健康检查 · 备份恢复 · 隐私保护'),
    ]),
    ('data', 'On your computer', '你的电脑 · 不进 git', 'data', 112, [
        ('knowledge/', 'library/ · manifest · PROFILE.md\ncareer/: fact bank, interviews, CVs', '证书材料 · 事实库 · 简历内容'),
        ('data/applications/', 'tailored CV + letter per posting\napplied.csv log', '每个精投岗位的简历与求职信'),
        ('data/mail · data/dashboard', 'mail dumps, classifications,\ndashboard data (rebuildable)', '邮件与看板缓存'),
        ('config/profile.yaml · .env', 'your answers; tokens (never copied)\n→ backup folder in Documents', '问卷答案 · 密钥 · 本地备份'),
    ]),
    ('svc', 'Online services', '在线服务', 'svc', 86, [
        None,
        ('LinkedIn · StepStone · Indeed · Xing', 'company career portals', '招聘平台 · 公司官网'),
        ('Gmail · Notion · claude.ai', 'label "applications", tracker,\ninteractive dashboard', '邮箱 · 申请表 · 交互看板'),
        ('GitHub (shared repo)', 'code, skills, rules, empty templates —\nno personal data', '共享仓库：只有代码和模板'),
    ]),
]
TOP_Y, TOP_H, ROW_GAP = 64, 58, 22
F = "font-family=\"-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,'PingFang SC','Microsoft YaHei',sans-serif\""

# layout
y = TOP_Y + TOP_H + 34
ROWPOS = []
for key, en, zh, st, h, cells in ROWS:
    ROWPOS.append((y, h)); y += h + ROW_GAP
H = y + 6
def cx(i): return LEFT + 10 + i * (CW + GAP)

svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" {F}>',
       '<defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
       '<path d="M0,0 L10,5 L0,10 z" fill="#6B6862"/></marker></defs>',
       f'<rect x="0" y="0" width="{W}" height="{H}" rx="18" fill="#FFFFFF"/>']
# column titles
for i, (en, zh) in enumerate(COLS):
    svg.append(f'<text x="{cx(i) + CW / 2:.0f}" y="38" text-anchor="middle" font-size="15" font-weight="700" fill="#3B3934">{escape(en)} '
               f'<tspan font-weight="400" fill="#8A867F">· {zh}</tspan></text>')
# top banner: you talk to Claude
fill, stroke, tc = STYLE['you']
bx, bw = LEFT + 10, W - LEFT - 30
svg.append(f'<rect x="{bx}" y="{TOP_Y}" width="{bw}" height="{TOP_H}" rx="10" fill="{fill}" stroke="{stroke}" stroke-width="1.6"/>')
svg.append(f'<text x="{bx + bw / 2}" y="{TOP_Y + 24}" text-anchor="middle" font-size="13" font-weight="600" fill="{tc}">'
           'You talk to Claude: "show today\'s jobs" · "tailor my CV for this link" · "I have no CV" · "sync my mail" · "back up my data"</text>')
svg.append(f'<text x="{bx + bw / 2}" y="{TOP_Y + 44}" text-anchor="middle" font-size="11.5" fill="#6F6B64">'
           '你只需要和 Claude 说话："看看今天的岗位" · "按这个链接改简历" · "我没有简历" · "同步邮件" · "备份我的数据"</text>')
svg.append(f'<text x="28" y="{TOP_Y + 26}" font-size="13" font-weight="600" fill="#3B3934">You</text>'
           f'<text x="28" y="{TOP_Y + 44}" font-size="12" fill="#8A867F">你</text>')
ARROWS = []
for i in range(len(COLS)):   # banner → skills
    x = cx(i) + CW / 2
    ARROWS.append(f'<path d="M{x:.0f},{TOP_Y + TOP_H} L{x:.0f},{ROWPOS[0][0]}" stroke="#6B6862" stroke-width="1.6" marker-end="url(#arr)"/>')
drawio_cells = []
for r, ((key, en, zh, st, h, cells), (y0, rh)) in enumerate(zip(ROWS, ROWPOS)):
    fill, stroke, tc = STYLE[st]
    band = '#FAF9F7' if r % 2 == 0 else '#F4F2EE'
    svg.append(f'<rect x="12" y="{y0 - 10}" width="{W - 24}" height="{rh + 20}" rx="12" fill="{band}"/>')
    svg.append(f'<text x="28" y="{y0 + 18}" font-size="13" font-weight="600" fill="#3B3934">{escape(en)}</text>')
    for j, part in enumerate(zh.split(' · ')):
        svg.append(f'<text x="28" y="{y0 + 36 + j * 16}" font-size="12" fill="#8A867F">{escape(part)}</text>')
    for i, c in enumerate(cells):
        if not c:
            continue
        title, lines, czh = c
        x = cx(i)
        svg.append(f'<rect x="{x:.0f}" y="{y0}" width="{CW:.0f}" height="{rh}" rx="10" fill="{fill}" stroke="{stroke}" stroke-width="1.4"/>')
        tl, ll = title.split('\n'), lines.split('\n')
        yy = y0 + 20
        for t in tl:
            svg.append(f'<text x="{x + CW / 2:.0f}" y="{yy}" text-anchor="middle" font-size="12.5" font-weight="700" fill="{tc}">{escape(t)}</text>'); yy += 15
        yy += 3
        for t in ll:
            svg.append(f'<text x="{x + CW / 2:.0f}" y="{yy}" text-anchor="middle" font-size="11.5" fill="#4A4741">{escape(t)}</text>'); yy += 14
        svg.append(f'<text x="{x + CW / 2:.0f}" y="{y0 + rh - 10}" text-anchor="middle" font-size="11" fill="#8A867F">{escape(czh)}</text>')
        drawio_cells.append((x, y0, CW, rh, st, title, lines, czh))
        if r + 1 < len(ROWS) and ROWS[r + 1][5][i] and not (ROWS[r + 1][0] == 'svc' and i == 3):   # no arrow into GitHub: personal data never goes there
            ny = ROWPOS[r + 1][0]
            ARROWS.append(f'<path d="M{x + CW / 2:.0f},{y0 + rh} L{x + CW / 2:.0f},{ny}" stroke="#6B6862" stroke-width="1.6" marker-end="url(#arr)"/>')
svg += ARROWS
svg.append('</svg>')
open(os.path.join(HERE, 'modules.svg'), 'w').write('\n'.join(svg))

# draw.io
cells = ['<mxCell id="0"/>', '<mxCell id="1" parent="0"/>']
for n, (x, y0, w, h, st, title, lines, czh) in enumerate(drawio_cells):
    fill, stroke, tc = STYLE[st]
    v = html.escape(f'<b>{title.replace(chr(10), "<br>")}</b><br><font style="font-size:11px">{lines.replace(chr(10), "<br>")}</font>'
                    f'<br><font style="font-size:11px" color="#8A867F">{czh}</font>')
    cells.append(f'<mxCell id="m{n}" value="{v}" style="rounded=1;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};fontColor={tc};fontSize=12;" '
                 f'vertex="1" parent="1"><mxGeometry x="{x:.0f}" y="{y0}" width="{w:.0f}" height="{h}" as="geometry"/></mxCell>')
for r, (key, en, zh, st, h, row) in enumerate(ROWS):
    y0, rh = ROWPOS[r]
    cells.append(f'<mxCell id="r{r}" value="{html.escape(f"<b>{en}</b><br>{zh}")}" style="text;html=1;align=left;verticalAlign=top;fontSize=12;" '
                 f'vertex="1" parent="1"><mxGeometry x="20" y="{y0}" width="{LEFT - 20}" height="{rh}" as="geometry"/></mxCell>')
cells.append(f'<mxCell id="you" value="{html.escape("<b>You talk to Claude</b> · 你只需要和 Claude 说话")}" style="rounded=1;whiteSpace=wrap;html=1;'
             f'fillColor={STYLE["you"][0]};strokeColor={STYLE["you"][1]};fontColor={STYLE["you"][2]};fontSize=13;" vertex="1" parent="1">'
             f'<mxGeometry x="{LEFT + 10}" y="{TOP_Y}" width="{W - LEFT - 30}" height="{TOP_H}" as="geometry"/></mxCell>')
xml = (f'<mxfile host="build_modules.py"><diagram name="Job Autopilot modules" id="modules"><mxGraphModel dx="{W}" dy="{H}" grid="1" gridSize="10" '
       f'guides="1" page="1" pageWidth="{W}" pageHeight="{H}" background="#FFFFFF"><root>' + ''.join(cells) + '</root></mxGraphModel></diagram></mxfile>')
open(os.path.join(HERE, 'modules.drawio'), 'w').write(xml)
print('wrote modules.svg and modules.drawio')
