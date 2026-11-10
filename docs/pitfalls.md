# Pitfalls we hit · 踩过的坑

Each item: what went wrong → what fixed it. 每条：出了什么问题 → 怎么解决的。

## Browser and logins · 浏览器与登录
1. **Wrong browser** — Claude used the Chrome extension while the user had logged in inside Claude's built-in browser. → Always use the built-in pane; logins persist there.
   **用错浏览器**：用户在 Claude 内置浏览器登录，Claude 却去用 Chrome。→ 一律用内置浏览器。
2. **Login check false positive on Indeed** — the quick-apply page looked normal while logged out. → Check for the account menu before starting.
   **Indeed 登录误判**：未登录时页面看起来也正常。→ 先确认右上角账户菜单。
3. **Closing the pane loses form state** — half-filled portal forms are gone. → Reopen, refill, re-tick consent boxes.
   **关闭浏览器面板会丢表单**：重开后重填、重新勾选同意框。

## Submitting · 提交
4. **StepStone "Ich bin interessiert" submits instantly** — one application went out while Claude only wanted to look at the form. → Shortlist → user picks → then click. Written into CLAUDE.md rule 2.
   **StepStone 一键投递**：点了就直接发出。→ 先列清单，用户确认后再点。
5. **React dropdowns ignore scripted values** (StepStone smart-apply) — submit stays disabled. → Real click + keyboard selection.
   **React 下拉框不认脚本赋值**：提交按钮一直灰。→ 真实点击 + 键盘选择。
6. **One-by-one confirmations were tiring** → batch mode: prefill all to the review page, one list, one "submit".
   **逐个确认太累**：改为批量模式，一次确认全部提交。
7. **CAPTCHAs** (Porsche "4+5") — Claude does not solve them by design. → The user types the answer; Claude continues.
   **验证码**：Claude 按规则不做，用户填完 Claude 继续。

## Files and uploads · 文件与上传
8. **The built-in browser cannot upload files**, and SmartRecruiters hides inputs in shadow DOM. → `tools/upload_file.sh` drives the macOS Open dialog (Cmd+Shift+G → path → Return → Return). Windows: Claude in Chrome's `file_upload` or a manual paste (`docs/file-uploads.md`).
8a. **Attaching a file with page JavaScript from a local server does not work** — the built-in browser blocks requests from internet pages to the computer (`ERR_BLOCKED_BY_CLIENT`). That is a security boundary; do not work around it.
    **用页面脚本从本地服务器取文件不可行**：内置浏览器禁止网页访问本机，这是安全边界，不要绕过。
   **内置浏览器不能上传文件**：用脚本驱动系统"打开"对话框。
9. **Permission lost after rebuilding a helper app** — each `osacompile` build is a new identity for macOS privacy settings (three re-authorisations). → Run `osascript` from Claude itself and grant Accessibility to Claude once.
   **自制 app 每次重编译都丢权限**：直接由 Claude 调 osascript，只给 Claude 授权一次。
10. **The dialog was not found** — it is a sheet of the Claude window, not a separate window. → Script waits for `sheet 1 of window 1` of process Claude.
    **找不到对话框**：它是 Claude 窗口的 sheet。
11. **Indeed reused a 10-page merged PDF** (CV + transcripts). → "Andere Datei hochladen" with the single CV; keep one purpose per PDF in the knowledge base.
    **Indeed 默认用了 10 页合并 PDF**：换成单页简历；知识库里一份文件一个用途。
12. **Porsche upload did nothing** — the portal waits for an explicit start and loses its dropdown after the first upload. → Set type, choose file, trigger the start button; reload the page if the dropdown is gone.
    **Porsche 上传没反应**：需要手动触发开始上传；第一次上传后下拉框失效就刷新页面。
13. **Forms that demand documents we do not have** (cover letter, merged certificate PDF). → Skip on cover letter; ask the user for missing certificates; build merged PDFs from unit files with `tools/kb_bundle.py`; never upload something unrelated.
    **表单要求没有的材料**：要求求职信就跳过；缺证书就问用户要；需要合并 PDF 时用单元文件现拼。
13a. **Reading a certificate by its text alone missed a 1st-place medal** — the AWS hackathon certificate says "for successfully participating", the "1st" medal is only in the image. → Dual review: every page is read as text *and* looked at as an image (plus OCR when tesseract is installed); disagreements are recorded.
    **只读文字层漏掉了第一名奖牌**：证书正文写"参加"，"1st"奖牌只在图上。→ 每页都做文字 + 图像双重审核，不一致时记录下来。
13b. **Scanned certificates have no text layer** — text extraction returns nothing, so a script alone cannot tell what a page is. → `kb_extract.py` flags those pages and renders previews; Claude reads them visually before splitting.
    **扫描件没有文字层**：脚本识别不了，标记出来让 Claude 看图判断。

## CVs and cover letters · 简历与求职信
20. **The same fact drifted between documents** — the reference says 01/2022–03/2024 (2 years 3 months); the CV said "2.5 years", the cover letter "two and a half years". → One fact bank (`knowledge/career/facts.yaml`), durations quoted from `tools/facts.py durations`, and `tools/doc_check.py` compares CV, letter and fact bank before anything is sent.
    **同一事实在不同文件里写法不一致**：工作证明是 2 年 3 个月，简历写 2.5 年、求职信写两年半。→ 统一事实库，时长从脚本取，发出前自动比对。
21. **A good-looking PDF can be unreadable for an ATS** — rendered with Helvetica Neue, every bold or italic line came out of the text layer one word per line; a ligature turned "fi" into one character. → Generated documents use Arial, one column, real text; `doc_render.py` checks every line is in the text layer in reading order, `doc_check.py` flags one-word-per-line extraction.
    **好看的 PDF 不一定能被 ATS 读懂**：Helvetica Neue 的粗体/斜体被拆成一词一行，连字把 "fi" 变成一个字符。→ 统一用 Arial、单栏、真文字，生成后自动检查文字层顺序。
22. **The same achievement appeared three times** (experience, achievements, publications). → CV rule 9; `doc_check.py` reports repeated phrases.
    **同一成果出现三次**：每个成果只写一次，脚本会提示重复。
23. **Tailoring every application does not scale, and late applications rarely get interviews.** → Mode per job from posting age × seen before × fit (`standards/de/apply-strategy.md`); tailored CVs only for fresh, high-fit postings and dream companies, capped per day; the dashboard compares interview rates by mode and posting age.
    **每份都精修不现实，老岗位精投也很少有面试**：按新鲜度 × 是否眼熟 × 匹配度决定精投/模版投，每天限量，看板按模式和岗位新鲜度对比面试率。

## Notion and Gmail
14. **Notion parent page "cannot have content"** — a person/profile page was used. → Use a normal page shared with the integration (••• → Connections).
    **Notion 父页面不能放内容**：换普通页面并共享给 integration。
15. **IMAP search errors** with non-ASCII characters and nested quotes in `X-GM-RAW`. → Keep queries ASCII.
    **IMAP 搜索报错**：查询里不要有中文/特殊引号。
16. **Rule-based email parsing was poor.** → LLM classification in chunks of ~40 (subagents in parallel), then deterministic matching.
    **规则解析邮件效果差**：改为 LLM 分块分类 + 确定性匹配。
17. **StepStone/Indeed receipts have no company; generic titles collide** ("AI Engineer" × 5). → Match by platform + exact title + date, prefer rows without evidence; compare company names without spaces ("Auto Scout24" = "AutoScout24"); aliases in `config/overrides.json`.
    **回执没有公司名、通用职位名撞车**：按平台 + 完全相同职位 + 日期匹配；公司名去空格比较；别名表。
18. **Notion cannot embed claude.ai pages.** → PNG charts from `tools/charts_png.py` in Notion, interactive version linked. (Mermaid code blocks were dropped 2026-11-10: Notion shows their source code above every chart.)
    **Notion 不能嵌入 claude.ai 页面**：Notion 里只放脚本生成的 PNG 图，交互版放链接（Mermaid 代码块会显示源码，已删除）。

## Scheduling · 定时
19. Scheduled tasks run only while the Mac is awake and the Claude app is open. Submitting always needs the user anyway.
    定时任务只在电脑唤醒且 Claude 打开时运行；提交始终需要用户在场。

## LinkedIn rate limit when reading many postings (2026-11-05)
Fetching ~20 postings back-to-back via `/jobs-guest/jobs/api/jobPosting/<id>` from the page returned HTTP 429 after the
first batch, and afterwards even normal `/jobs/view/<id>` page loads were 429 for a while. Read list pages with
`get_page_text`, open only the few top candidates one by one with pauses, and never bulk-fetch postings.

## upload_file.sh reports -10000 but the file is attached (2026-11-05)
On an Ashby form the script ended with "System Events … Fehler in der AppleEvent-Routine (-10000)" although the file was
selected and shown on the page. Always verify on the page instead of trusting the script's exit status.

## Consent and declaration checkboxes need the user's explicit word (2026-11-05)
Privacy-notice confirmations, "information is true" declarations and sanctions-screening consents are the user's own
consent. A general "submit directly" was not enough — the permission layer blocked ticking them. When the user then said
explicitly in chat "tick them for me and submit", ticking worked. Default: prefill everything, leave the form on its last
page, list the boxes; tick them only after the user explicitly asks for it for that batch.

## File dialog does not open while the browser pane is hidden (2026-11-05)
Clicking an upload control while the pane is hidden (`tabs_context` says "hidden") opens no file sheet, and
`upload_file.sh` fails with "no file sheet open". Ask the user to show the pane first; afterwards one tab's upload
button stayed dead for a while and the user had to ask for a retry. Check `tabs_context` before every upload.

## Long application forms time out (2026-11-05)
SmartRecruiters closes an idle form ("Aufgrund von Inaktivität … geschlossen") and Phenom (Siemens Healthineers) drops
back to the job page. Forms left for the user lose everything if they wait too long — tell the user to finish them the
same session. Re-uploading a CV re-runs the parser, which may split one job into two entries (delete the duplicate).

## Clicking "Next" by coordinate hit a footer link (2026-11-05)
On Phenom the page shifted after scrolling and a coordinate click landed on "Career Site Cookie Settings", which left
the form and lost step 2. Click form buttons by `ref` (from `find`) after `scroll_to`, not by coordinate.

## Anonymous LinkedIn pages turn into a login wall (2026-11-06)
Snapshotting job descriptions with a headless browser worked for the first few LinkedIn postings, then every further
page came back as "LinkedIn Login, Einloggen" — and the first version of `tools/jd_snapshot.py` stored those walls as
"online". Fix: LinkedIn postings are read through the public job card
`/jobs-guest/jobs/api/jobPosting/<id>` (no login, full description, paced); a page print is kept only when it shows the
job title and no login form. Check a sample of snapshots by size and content after any bulk run.

## Batch applying · 批量投递 (2026-11-06)
- **File dialog does nothing in a background tab** — `upload_file.sh` fails with "no file sheet open". → `tabs_select` the tab first, then click the choose-file control, then run the script.
  **后台标签页无法弹出文件选择框**：先把该标签页切到前台。
- **LinkedIn "Bewerben" opens a new tab, which the pane blocks** — read the target from the link: `a[href*="safety/go"]` → decode its `url=` parameter, then `navigate` there.
  **LinkedIn 外链被拦截**：从链接 `safety/go?url=` 里解出真实地址再打开。
- **LinkedIn job id**: after searching, the URL's `currentJobId` is the first card; `https://www.linkedin.com/jobs/view/<id>/` is the direct link.
- **StepStone `ag=` takes 1, 3, 7, 14** (`age_2` is silently ignored and returns everything).
- **Cloudflare Turnstile ("Bestätigen Sie, dass Sie ein Mensch sind")** on Personio forms keeps the send button grey → the user ticks it; leave the tab open.
- **Company portals that only offer a login** (BCG studenttalent.bcg.com) → user logs in or creates the account; mark the job *waiting on you*.
- **Ashby (OpenAI)**: the start-date field is a date picker — click it, type `MM/DD/YYYY`; location is a combobox (type, then click the option). Declaration checkbox + "Submit Application"; success text "Your application was successfully submitted". OpenAI allows at most 5 applications per 180 days.
- **Company career pages that embed Ashby (BLP)**: the page itself shows no form. Hosted form = `https://jobs.ashbyhq.com/<company-slug>/<ashby_jid>/application`; try the company name with and without hyphens (`blp-digital` worked, `blp` and `BLP` gave 404).
- **Free-text screening questions** (e.g. "ERP experience?"): answer only from `knowledge/career/facts.yaml`; if the fact is absent say so plainly and name the nearest real experience.
- **StepStone "Ich bin interessiert" is not always one-click.** Three outcomes: (a) smart-apply form on stepstone.de (`/application/smart-apply`) — fill it, "Bewerbung abschicken", success = "Deine Bewerbung ist auf dem Weg"; (b) external job: lands on "Hat mit deiner Bewerbung alles geklappt?" — click **Unternehmenswebsite** to reach the company's own form (do NOT claim it is applied); (c) instant send.
- **React forms ignore plain `.value=`**: use the native setter (`Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(el,v)`; for `<select>` use `HTMLSelectElement.prototype`) then dispatch `input`, `change`, `blur`. Worked on StepStone smart-apply (salary number, currency select, text questions). Checkboxes/radios: a real click.
- **StepStone keeps your documents**: "Zusätzliche Dateien → Hinzufügen" lists the Notenspiegel / Arbeitszeugnis / Abschlusszeugnis already in the account — tick them instead of uploading.
- **Recruitee** (`*.recruitee.com/o/<job>`): form is under the "Bewerben" tab (`/c/new`; filling before opening that tab is lost). Success = URL ends `/applied`, title "Beworben".
- **Staffing-agency postings** (e.g. anteira, AÜG) often have no real application form — only a contact form. Skip and tell the user.
- **Indeed smartapply** (`smartapply.indeed.com`): the "Schnellbewerbung" link on `viewjob?jk=…` gives the form URL. Plain JS `button.click()` on "Weiter" / "Bewerbung absenden" works; coordinate clicks need a fresh screenshot first. Employer questions use text inputs (set with the native setter), radios (`.click()`), and a `role=combobox` whose `role=option` items you `.click()`. Employer document slots (Arbeitszeugnis*, Urkunde*) → real click on "Datei hochladen", then `upload_file.sh`. Success: "Ihre Bewerbung wurde gesendet". The "Job-E-Mails" checkbox on the review page stays unticked.
- **Ashby choice questions** (radio/checkbox groups): the visible text is a `<label>`; click the label (or a real coordinate click) — `input.click()` often does nothing. After submit, Ashby lists "Missing entry for required field: …" — fix and resubmit. Ashby company slug usually equals the brand (`moss`, `blp-digital`, `openai`); `getmoss`/`BLP` gave 404.
- **`upload_file.sh` reports an AppleEvent error (-10000) but the file is attached** — look at the page (file name shown?) before running it again; a second run opens a second dialog. → `docs/macos-permissions.md`.

## Found on 2026-11-09 · 2026-11-09 新发现
- **Hidden browser pane = no file dialog.** `tabs_context` ends with "The Browser pane is currently hidden" and `upload_file.sh` fails with "no file sheet open", even right after a real click. `show_pane preview` cannot help when the session is not open in any window. → Ask the user to open the session window with the browser pane visible; until then do only jobs that need no upload (LinkedIn Easy Apply with a library CV, StepStone smart-apply, Xing easy apply) and leave upload forms prefilled.
- **LinkedIn Easy Apply modal in a short pane**: the lower part is cut off. The blue button at the bottom right on the question page is "Feedback geben" (feedback), not Next — the real Next / review button is clicked at the same spot only after the page has loaded; scroll inside the modal (`computer scroll` at the modal) to reach the "Folgen Sie …" checkbox (untick) and "Bewerbung senden". Screenshots lag 1–2 s behind clicks: take a second one before deciding a click failed. Success dialog: "Ihre Bewerbung wurde an <Firma> gesendet".
- **Join (join.com) ATS through LinkedIn Easy Apply** (e.g. XALT): 4 pages — contact (prefilled), resume (pick from the LinkedIn library), questions (work authorisation, start date, "JOIN Terms & Conditions … Yes" is required), review.
- **SAP SuccessFactors / j2w career sites (`/talentcommunity/apply/<id>`, `/default/content/apply/`: jobs.sap.com, jobs.adesso-group.com, jobs.bayernlb.de)** — do NOT skip them. The deep link `…/talentcommunity/apply/<id>` redirects to the home page, and the real apply page is blank for 30–60 s with the form inside a frame the page scripts cannot read. Start from the job detail page, decide cookies, **really click** "Jetzt bewerben", wait up to 60 s and look at a **screenshot**; fill with real clicks and typing. Only a page that says the position is filled/closed (SAP: "Sorry, this position has been filled") is a valid skip. Full root cause and procedure: job-scan-apply skill, section "Never skip a job because of a technical problem". (Earlier advice here to skip these sites was wrong: it made the 2026-11-09 scan drop two BayernLB roles.)
- **LinkedIn "Bewerben" can lead to a scraper site** (e.g. `divulgavagas.com.br`) instead of the employer. Do not apply there; skip and log.
- **The Gmail connector in the Claude app may be a different mailbox** (the work account, not the application inbox). The application inbox is only reachable through `tools/gmail_*.py` (IMAP) and `tools/send_reply.py` (SMTP). Check `IMAP_USER` before using any other Gmail tool.
- **LinkedIn messaging shows every conversation** (friends, groups). When scanning for invitations read only recruiter threads; do not summarize or reuse the rest.


## Cloudflare Turnstile fails in the built-in browser (Personio, Dover) · 2026-11-09
Personio career pages (`*.jobs.personio.de`) and Dover (`jobs.dover.com`) show a Cloudflare "confirm you are human" box above the submit button.
In the built-in browser it ends in "Überprüfung fehlgeschlagen" even when the user clicks it by hand, and the portal then reports "Fehler beim Senden der Bewerbung".
Do not try to get around it. Prefill is wasted effort there: probe the page first (scroll to the bottom, look for the Cloudflare box) and list the job as "needs the user's normal browser" before filling anything.
