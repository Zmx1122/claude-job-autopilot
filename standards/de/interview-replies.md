# Replying to interview invitations · 回复面试邀请

Three short answers cover almost every invitation. Claude drafts one, **shows the exact text, and sends it only after the user says yes**.
三种短回复覆盖几乎所有邀请。Claude 先起草、给你看完整原文，**你说"发"才会发出去**。

| # | When · 什么时候用 | Meaning · 含义 |
|---|---|---|
| **1 · Accept** | the proposed time works · 邀请里的时间可以 | thanks, time is fine · 感谢邀请，时间合适 |
| **2 · Reschedule** | the time does not work · 时间不行 | thanks, cannot make it, propose other times + the user's availability (**asked from the user**, never invented) · 感谢邀请，时间不行，建议换到 …，附上你的空闲时间（由你提供，不编造） |
| **3 · Withdraw** | the user no longer wants this process · 不想继续这个流程 | thanks, several other applications reached a late stage, withdraws the application · 感谢邀请，因为近几天别的多个申请已进入后期阶段，撤回申请 |

Booking-link invitations ("pick a slot here: calendly / Outlook bookwithme"): Claude never clicks links in emails and cannot choose a slot for you.
Offer: **you book the slot yourself**, or template 2 / 3 as a written reply. 带预约链接的邀请：Claude 不会点邮件里的链接、也不能替你选时间。你自己预约，或者用模板 2 / 3 写回复。

## Rules · 规则
- Reply in the **language of the invitation**, with the salutation the sender used (Sehr geehrte Frau …, Hallo …, Hi …). Keep it to 3–5 lines.
- Use only what the user gave: the times in template 2 are the user's, the reasons are the user's wording. Never add reasons, numbers or promises.
- Reply in the **same channel**: an email invitation gets an email reply (from the application inbox), a LinkedIn message gets a LinkedIn reply.
- After sending, log it in Notion (`log_application.py … --notes "replied <date>: template N"`; template 3 also `--status Withdrawn`).
- Never reply to offers, rejections, newsletters or automatic mails. Never reply to a signed-offer company's process unless the user asks.

## English
**1 · Accept**
> Dear {Name},
> thank you very much for the invitation. The proposed time ({date, time}) works for me, and I am looking forward to our conversation.
> Best regards
> {Full name}

**2 · Reschedule**
> Dear {Name},
> thank you very much for the invitation. Unfortunately the proposed time does not work for me. Could we move it to {proposed time}? My availability: {availability}.
> Best regards
> {Full name}

**3 · Withdraw**
> Dear {Name},
> thank you very much for the invitation. Because several other applications have reached a late stage in the past few days, I would like to withdraw my application. I wish you every success with filling the position.
> Best regards
> {Full name}

## Deutsch
**1 · Zusage**
> Sehr geehrte/r {Name},
> vielen Dank für Ihre Einladung. Der vorgeschlagene Termin ({Datum, Uhrzeit}) passt für mich, ich freue mich auf das Gespräch.
> Viele Grüße
> {Vorname Nachname}

**2 · Terminverschiebung**
> Sehr geehrte/r {Name},
> vielen Dank für Ihre Einladung. Leider passt der vorgeschlagene Termin bei mir nicht. Könnten wir stattdessen {Alternativtermin} vereinbaren? Ich bin zu folgenden Zeiten verfügbar: {Verfügbarkeit}.
> Viele Grüße
> {Vorname Nachname}

**3 · Rücknahme der Bewerbung**
> Sehr geehrte/r {Name},
> vielen Dank für Ihre Einladung. Da mehrere andere Bewerbungsprozesse in den letzten Tagen in eine späte Phase gekommen sind, ziehe ich meine Bewerbung hiermit zurück. Ich wünsche Ihnen viel Erfolg bei der Besetzung der Stelle.
> Viele Grüße
> {Vorname Nachname}
