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
8. **The built-in browser cannot upload files**, and SmartRecruiters hides inputs in shadow DOM. → `tools/upload_file.sh` drives the macOS Open dialog (Cmd+Shift+G → path → Return → Return).
   **内置浏览器不能上传文件**：用脚本驱动系统"打开"对话框。
9. **Permission lost after rebuilding a helper app** — each `osacompile` build is a new identity for macOS privacy settings (three re-authorisations). → Run `osascript` from Claude itself and grant Accessibility to Claude once.
   **自制 app 每次重编译都丢权限**：直接由 Claude 调 osascript，只给 Claude 授权一次。
10. **The dialog was not found** — it is a sheet of the Claude window, not a separate window. → Script waits for `sheet 1 of window 1` of process Claude.
    **找不到对话框**：它是 Claude 窗口的 sheet。
11. **Indeed reused a 10-page merged PDF** (CV + transcripts). → "Andere Datei hochladen" with the single CV; keep one purpose per PDF in the knowledge base.
    **Indeed 默认用了 10 页合并 PDF**：换成单页简历；知识库里一份文件一个用途。
12. **Porsche upload did nothing** — the portal waits for an explicit start and loses its dropdown after the first upload. → Set type, choose file, trigger the start button; reload the page if the dropdown is gone.
    **Porsche 上传没反应**：需要手动触发开始上传；第一次上传后下拉框失效就刷新页面。
13. **Forms that demand documents we do not have** (cover letter, merged certificate PDF). → Skip on cover letter; ask the user for missing certificates; never upload something unrelated.
    **表单要求没有的材料**：要求求职信就跳过；缺证书就问用户要。

## Notion and Gmail
14. **Notion parent page "cannot have content"** — a person/profile page was used. → Use a normal page shared with the integration (••• → Connections).
    **Notion 父页面不能放内容**：换普通页面并共享给 integration。
15. **IMAP search errors** with non-ASCII characters and nested quotes in `X-GM-RAW`. → Keep queries ASCII.
    **IMAP 搜索报错**：查询里不要有中文/特殊引号。
16. **Rule-based email parsing was poor.** → LLM classification in chunks of ~40 (subagents in parallel), then deterministic matching.
    **规则解析邮件效果差**：改为 LLM 分块分类 + 确定性匹配。
17. **StepStone/Indeed receipts have no company; generic titles collide** ("AI Engineer" × 5). → Match by platform + exact title + date, prefer rows without evidence; compare company names without spaces ("Auto Scout24" = "AutoScout24"); aliases in `config/overrides.json`.
    **回执没有公司名、通用职位名撞车**：按平台 + 完全相同职位 + 日期匹配；公司名去空格比较；别名表。
18. **Notion cannot embed claude.ai pages.** → Native Mermaid charts + PNGs in Notion, interactive version linked.
    **Notion 不能嵌入 claude.ai 页面**：Notion 里用 Mermaid + 图片，交互版放链接。

## Scheduling · 定时
19. Scheduled tasks run only while the Mac is awake and the Claude app is open. Submitting always needs the user anyway.
    定时任务只在电脑唤醒且 Claude 打开时运行；提交始终需要用户在场。
