"""Detailed application stage ("进度" column) — how far each application got, and how it ended.

The coarse Status column (Applied / Confirmed / Interview / Offer / Rejected / Withdrawn / Skipped) stays for the dashboard.
Stage says exactly where it stands, e.g. 已参加一面, 二面邀请后撤回, 参加二面后被拒. Status is derived from Stage (status_of).

Stages
  pre:        待定 (shortlisted, not decided) · 放弃投递 (never applied) · 投递失败 (platform could not deliver)
  applied:    已投递 · 已确认收到 · 补交材料 (documents requested, no interview yet)
  assessment: 测评中 (online test / coding task / case before any interview) · 测评后被拒 · 测评后撤回
  interviews: N面邀请 (invited, not held yet) · 已参加N面 · N面邀请后撤回 · N面后撤回 · 参加N面后被拒   (N = 一 二 三 四 …)
  ends:       简历被拒 (rejected without any interview) · 投递后撤回 · 收到Offer · 接受Offer · 拒绝Offer

Events (one per classified email, oldest first) move the stage forward with next_stage(). Keys used from an event:
  category  application_sent | ats_confirmation | interview | rejection | offer | withdrawn | delivery_failed | own_message
  step      for interview: invite | scheduling | assessment | documents | feedback; for own_message: accept | reschedule | withdraw | documents | other
  round     explicit round number from the email (int) or None ("final" → None)
  interview_date  ISO date of the scheduled interview, if the email gives one
  after_interview for rejection: 'yes' (mentions the interview held) | 'no' | ''
  day       datetime.date of the email

usage (self-test): python3 tools/stage.py
"""
import re
from datetime import date

CN = {1: '一', 2: '二', 3: '三', 4: '四', 5: '五', 6: '六'}
NUM = {v: k for k, v in CN.items()}
STAGES = (['待定', '放弃投递', '投递失败', '已投递', '已确认收到', '补交材料', '测评中', '测评后被拒', '测评后撤回', '简历被拒', '投递后撤回']
          + [s.format(CN[n]) for n in range(1, 5) for s in ('{}面邀请', '已参加{}面', '{}面邀请后撤回', '{}面后撤回', '参加{}面后被拒')]
          + ['收到Offer', '接受Offer', '拒绝Offer'])
COLORS = {'待定': 'yellow', '放弃投递': 'default', '投递失败': 'default', '已投递': 'blue', '已确认收到': 'purple', '补交材料': 'orange',
          '测评中': 'orange', '收到Offer': 'green', '接受Offer': 'green', '拒绝Offer': 'brown'}


def rname(n): return f'{CN.get(n, str(n))}面'


def color(stage):
    if stage in COLORS: return COLORS[stage]
    if '被拒' in stage: return 'red'
    if '撤回' in stage: return 'brown'
    return 'orange'   # interview stages


def parse(stage):
    """stage label → dict(phase, round, attended). phase: pre | skipped | failed | applied | confirmed | docs | assess | interview |
    offer | rejected | withdrawn."""
    s = stage or ''
    m = re.search(r'([一二三四五六\d])面', s)
    n = (NUM.get(m.group(1)) or int(m.group(1))) if m else 0
    if not s: return dict(phase='', round=0, attended=False)
    if s == '待定': return dict(phase='pre', round=0, attended=False)
    if s == '放弃投递': return dict(phase='skipped', round=0, attended=False)
    if s == '投递失败': return dict(phase='failed', round=0, attended=False)
    if s == '已投递': return dict(phase='applied', round=0, attended=False)
    if s == '已确认收到': return dict(phase='confirmed', round=0, attended=False)
    if s == '补交材料': return dict(phase='docs', round=0, attended=False)
    if s == '测评中': return dict(phase='assess', round=0, attended=False)
    if 'Offer' in s: return dict(phase='offer', round=n, attended=True)
    if '被拒' in s: return dict(phase='rejected', round=n, attended=n > 0 or s.startswith('测评'))
    if '撤回' in s: return dict(phase='withdrawn', round=n, attended='邀请' not in s)
    if s.startswith('已参加'): return dict(phase='interview', round=n, attended=True)
    if s.endswith('面邀请'): return dict(phase='interview', round=n, attended=False)
    return dict(phase='', round=0, attended=False)


def from_status(status):
    """Starting stage for a row that has no stage yet."""
    return {'Shortlisted': '待定', 'Seen': '待定', 'Skipped': '放弃投递', 'Applied': '已投递', 'Confirmed': '已确认收到',
            'Interview': '一面邀请', 'Offer': '收到Offer', 'Rejected': '简历被拒', 'Withdrawn': '投递后撤回'}.get(status, '')


def status_of(stage):
    p = parse(stage)['phase']
    return {'pre': 'Shortlisted', 'skipped': 'Skipped', 'failed': 'Skipped', 'applied': 'Applied', 'confirmed': 'Confirmed',
            'docs': 'Confirmed', 'assess': 'Interview', 'interview': 'Interview', 'offer': 'Offer', 'rejected': 'Rejected',
            'withdrawn': 'Withdrawn'}.get(p, '')


def withdrawn_stage(stage):
    """The user withdrew (reply template 3, or told us). Which withdrawal label fits the current stage."""
    p = parse(stage)
    if p['phase'] in ('withdrawn', 'rejected', 'skipped'): return stage
    if p['phase'] == 'pre': return '放弃投递'
    if p['phase'] == 'assess': return '测评后撤回'
    if p['round']: return f"{rname(p['round'])}后撤回" if p['attended'] else f"{rname(p['round'])}邀请后撤回"
    return '投递后撤回'


def held(stage, interview_date, today):
    """N面邀请 whose interview date has passed → 已参加N面 (the user withdraws explicitly otherwise)."""
    p = parse(stage)
    if p['phase'] == 'interview' and not p['attended'] and interview_date and interview_date < str(today):
        return f"已参加{rname(p['round'])}"
    return stage


def next_stage(stage, e, interview_date=''):
    """Apply one event. Returns (new_stage, new_interview_date)."""
    p = parse(stage); cat = e.get('category'); step = e.get('step') or ''; day = str(e.get('day') or '')
    n, att, ph = p['round'], p['attended'], p['phase']
    if ph == 'interview' and not att and interview_date and day and interview_date < day:
        att = True; stage = f'已参加{rname(n)}'                                      # the interview took place before this email
    terminal = ph in ('rejected', 'withdrawn', 'offer')
    if cat == 'offer':
        return ('收到Offer' if ph != 'offer' else stage), interview_date
    if terminal:
        return stage, interview_date                                                  # older or follow-up mail never reopens an ended process
    if cat == 'application_sent':
        return ('已投递' if ph in ('', 'pre', 'skipped', 'failed') else stage), interview_date
    if cat == 'ats_confirmation':
        return ('已确认收到' if ph in ('', 'pre', 'skipped', 'failed', 'applied') else stage), interview_date
    if cat == 'delivery_failed':
        return ('投递失败' if ph in ('', 'pre', 'applied') else stage), interview_date
    if cat == 'interview' or (cat == 'own_message' and step == 'accept'):
        if cat == 'own_message':
            return stage, interview_date
        idate = e.get('interview_date') or ''
        if step == 'documents':
            return ('补交材料' if ph in ('', 'pre', 'applied', 'confirmed', 'skipped') else stage), interview_date
        if step == 'assessment':
            return ('测评中' if n == 0 else stage), interview_date
        if step == 'feedback':
            return (f'已参加{rname(n)}' if n else stage), interview_date
        if step == 'invite':
            r = e.get('round') if isinstance(e.get('round'), int) else None
            if r is None:
                r = n + 1 if (n == 0 or att) else n
            if r < n or (r == n and att):
                return stage, interview_date                                          # a late mail about a round already held
            return f'{rname(r)}邀请', (idate or (interview_date if r == n else ''))
        # scheduling / reminder: same round, maybe a date
        if n == 0 and ph not in ('assess',):
            return '一面邀请', idate or interview_date                                 # first sign of an interview is a scheduling mail
        return stage, (idate or interview_date)
    if cat == 'rejection':
        if n:
            return f'参加{rname(n)}后被拒', interview_date
        if ph == 'assess': return '测评后被拒', interview_date
        if e.get('after_interview') == 'yes': return '参加一面后被拒', interview_date   # interview arranged outside the mailbox
        return '简历被拒', interview_date
    if cat == 'withdrawn' or (cat == 'own_message' and step == 'withdraw'):
        return withdrawn_stage(stage), interview_date
    return stage, interview_date


if __name__ == '__main__':
    d = lambda s: date.fromisoformat(s)
    ev = [dict(category='application_sent', day=d('2026-10-01')), dict(category='ats_confirmation', day=d('2026-10-01')),
          dict(category='interview', step='invite', interview_date='2026-10-08', day=d('2026-10-03')),
          dict(category='interview', step='scheduling', day=d('2026-10-07')),
          dict(category='interview', step='invite', day=d('2026-10-10')),
          dict(category='rejection', day=d('2026-10-20'))]
    s, idt = '', ''
    for e in ev:
        s, idt = next_stage(s, e, idt); print(e['category'], e.get('step', ''), '→', s, idt)
    assert s == '参加二面后被拒', s
    assert withdrawn_stage('二面邀请') == '二面邀请后撤回' and withdrawn_stage('已参加一面') == '一面后撤回' and withdrawn_stage('已确认收到') == '投递后撤回'
    assert held('一面邀请', '2026-11-01', d('2026-11-10')) == '已参加一面'
    assert status_of('参加一面后被拒') == 'Rejected' and status_of('补交材料') == 'Confirmed' and status_of('二面邀请') == 'Interview'
    assert all(parse(x)['phase'] for x in STAGES), [x for x in STAGES if not parse(x)['phase']]
    print('ok,', len(STAGES), 'stages')
