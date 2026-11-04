<div align="center">

# Job Autopilot for Claude

**Daily job scan, one-confirmation batch applying, an inbox that updates your tracker, and dashboards —<br>
set up and run by talking to the Claude desktop app. No coding needed.**

**每日扫描岗位 · 一次确认批量投递 · 邮件自动更新申请表 · 可视化看板 ——<br>
全部通过和 Claude 桌面端对话完成，不需要会写代码。**

[English](#english) · [中文](#中文)

<img src="docs/diagram/flow.svg" alt="How you and Claude work together: one-time setup, an automatic morning run, an apply session where you pick and confirm, and a weekly dashboard" width="100%">

<sub>Editable source: <a href="docs/diagram/flow.drawio">docs/diagram/flow.drawio</a> (open in draw.io / diagrams.net)</sub>

</div>

---

## English

### What it does
- **Scans** LinkedIn, StepStone, Indeed and Xing every morning, removes jobs you have already seen, and filters by your rules
  (company size, salary, cover-letter requirement, daily cap).
- **Shows you a shortlist table** in chat. You pick, Claude fills every application up to its review page — including
  company career sites that need file uploads — and **submits only after you confirm once**.
- **Reads your application inbox** daily: confirmations, interview invitations, rejections and offers update a
  **Notion tracker**; every application links to its first email as evidence; every application email gets the Gmail label
  **`applications`**. Applications you sent by hand are detected and Claude asks you to confirm them.
- **Knowledge base**: drop every document you have — scans, merged PDFs, photos. Claude reads each page, splits them into
  one-document unit files, names them, and writes a profile of what each document proves and what is missing.
  At application time it decides per form which files go into which upload slot, merged or separate, in German standard order.
- **Dashboards**: a section on your Notion page (stage pie, stage flow, applications per week) and an interactive
  claude.ai dashboard with the same three charts, refreshed weekly.

### What you need
| | |
|---|---|
| A Mac with the **Claude desktop app** (Code tab) | the built-in browser and the file-upload helper are used |
| A **Gmail** inbox you apply with | read access via an app password; only adds a label |
| A **Notion** account | free plan is fine |
| Accounts on the job sites you use | you log in once inside Claude's browser |
| About 45 minutes once | then a few minutes a day |

### Get started
1. Open the Claude desktop app → **Code** tab, and say:
   > Clone https://github.com/Zmx1122/claude-job-autopilot into my Documents folder, open it, and set up job autopilot.

   (Or download the ZIP from GitHub, unzip it, and open the folder in the Code tab.)
2. Claude walks you through **nine short steps** (the `job-autopilot-setup` skill):
   documents → questionnaire → Notion token → Gmail app password + label → logins → upload permission → dashboards → schedule → final check.
   Every click is explained in [docs/credentials.md](docs/credentials.md) and [docs/macos-permissions.md](docs/macos-permissions.md).
3. From then on, each morning: open Claude and say **"show today's jobs"**.

### A normal day
```text
You     show today's jobs
Claude  Mail: 2 confirmations, 1 interview (Thu 10:00, ACME), 3 rejections. Notion updated, 6 emails labeled.
        Scanned 4 platforms: 41 postings → 7 new matches.
        | # | Company | Title | Platform | How to apply | Needs | Fit |
        | 1 | ACME AG | AI Engineer (m/w/d) | LinkedIn | easy_apply | cv | 88 |
        | 2 | Example SE | ML Engineer | StepStone | one_click | cv | 81 |  …
You     1, 2, 4
Claude  All three are filled in and waiting on their review pages (CV: CV-AI-Engineer.pdf). Submit?
You     submit
Claude  Sent 3/3, logged in Notion. Tomorrow's mail sync will link the confirmations.
```

### Modules
| Module | Where | What |
|---|---|---|
| Knowledge base | `.claude/skills/job-knowledge-base`, `tools/kb_extract.py`, `kb_build.py`, `kb_bundle.py` | inbox → unit files in `knowledge/library/` + `manifest.yaml` + `PROFILE.md`; merge/separate files per upload slot (never committed) |
| Questionnaire | `config/profile.example.yaml` → `config/profile.yaml` | personal data, search, rules, standard answers |
| Scan & apply | `.claude/skills/job-scan-apply`, `tools/dedupe.py`, `tools/log_application.py` | shortlist → pick → prefill → confirm → submit |
| Mail sync & label | `.claude/skills/job-mail-sync`, `tools/gmail_*.py`, `tools/sync_mail.py` | classify emails, update Notion, label `applications`, detect manual applications, backfill |
| Notion tracker | `tools/notion_setup.py` | creates the database ([schema](docs/data-model.md)) |
| Dashboards | `.claude/skills/job-dashboard`, `tools/refresh_dashboards.sh`, `dashboard/index.html` | Notion charts + interactive claude.ai dashboard |
| File uploads | `tools/upload_file.sh` | drives the macOS Open dialog so company portals get your PDFs |
| Health check | `tools/check_setup.py` | one checklist for everything above |

### Dashboards (sample data)
<p>
<img src="docs/img/pie.png" alt="Donut chart: where every application stands" width="49%">
<img src="docs/img/weekly.png" alt="Bar chart: applications per week by platform" width="49%">
</p>
<img src="docs/img/flow.png" alt="Flow chart: applied, confirmed, interview, offer, with rejections and waiting at each stage" width="100%">

### Boundaries
- Nothing is submitted without you. One-click buttons are listed first and clicked only after you pick them.
- You type passwords, solve CAPTCHAs, create portal accounts and click account-creating verification links. Claude does not.
- Only the documents a form requires are uploaded. Jobs that require a cover letter are skipped by default.
- Credentials stay in `.env` on your Mac. Your CVs, answers and logs are git-ignored.
- Job sites' terms often restrict automated use. This project keeps a human choosing and confirming every batch and
  enforces a daily cap; you are responsible for how you use it.

### Lessons learned
Everything that broke while building this — wrong browser, instant one-click submits, React dropdowns, uploads in shadow DOM,
lost macOS permissions, merged PDFs, ambiguous email receipts — and the fix: **[docs/pitfalls.md](docs/pitfalls.md)**.
Platform-by-platform behaviour: **[docs/platforms.md](docs/platforms.md)**.

### Roadmap
- CV tailoring per job (reorder and reword bullet points from the knowledge base, keep a versioned copy per application).
- Anschreiben drafting and editing in the user's own style, for jobs where a letter is required.

### FAQ
- **Windows?** Everything except the file-upload helper (macOS only) works; uploads then need one drag-and-drop from you.
- **Other inboxes than Gmail?** The scripts use IMAP plus Gmail labels; other providers need small changes in `tools/common.py`.
- **Other countries / job sites?** Add search URLs and behaviour to `docs/platforms.md`; the skills read it.

---

## 中文

### 它能做什么
- **每天早上扫描** LinkedIn、StepStone、Indeed、Xing，去掉看过的岗位，按你的规则筛选（公司规模、薪资、是否强制求职信、每日上限）。
- **在聊天里给你一张精选岗位表**。你挑选后，Claude 把每个申请填到最后确认页（包括需要上传文件的公司官网），**你确认一次才统一提交**。
- **每天读取投递邮箱**：确认信、面试邀请、拒信、offer 自动更新 **Notion 申请表**；每条申请链接到第一封投递邮件作为证据；
  所有申请邮件自动打上 Gmail 标签 **`applications`**（没有这个标签会引导你创建）。你自己手动投的申请会被发现，Claude 向你确认。
- **知识库**：把所有材料丢进来（扫描件、合并 PDF、照片都行）。Claude 逐页阅读，拆成"一份文件一个文档"的单元文件并统一命名，
  生成知识库画像：每个文档是什么、证明了哪些能力、还缺什么。投递时按表单的上传入口决定哪些文件合并、哪些分开、按什么顺序。
- **看板**：Notion 页面里的图表区（阶段饼图、阶段流向图、每周投递数）+ 一个 claude.ai 交互看板，版式固定，每周只更新数据。

### 需要准备
| | |
|---|---|
| 一台 Mac + **Claude 桌面端**（Code 标签页） | 用到内置浏览器和文件上传助手 |
| 用于投递的 **Gmail** | 通过应用专用密码只读访问，只会添加标签 |
| **Notion** 账号 | 免费版即可 |
| 各招聘平台账号 | 在 Claude 内置浏览器里登录一次 |
| 一次性约 45 分钟 | 之后每天几分钟 |

### 开始使用
1. 打开 Claude 桌面端 → **Code** 标签页，对它说：
   > 把 https://github.com/Zmx1122/claude-job-autopilot 克隆到我的 Documents 文件夹，打开它，然后帮我配置 job autopilot。

   （也可以在 GitHub 下载 ZIP，解压后在 Code 标签页打开该文件夹。）
2. Claude 会带你走完 **九个小步骤**（`job-autopilot-setup` skill）：
   上传材料 → 回答问卷 → Notion token → Gmail 应用密码和标签 → 登录各平台 → 上传权限 → 看板 → 定时任务 → 最终检查。
   每一步点哪里都写在 [docs/credentials.md](docs/credentials.md) 和 [docs/macos-permissions.md](docs/macos-permissions.md)。
3. 之后每天早上打开 Claude 说 **"看看今天的岗位"** 即可。

### 日常的一天
```text
你      看看今天的岗位
Claude  邮件：2 封确认信，1 个面试（周四 10:00，ACME），3 封拒信。Notion 已更新，6 封邮件已打标签。
        扫描 4 个平台：41 个岗位 → 7 个新匹配。
        | # | 公司 | 职位 | 平台 | 投递方式 | 需要材料 | 匹配度 |  …
你      1、2、4
Claude  三个都已填到确认页（简历：CV-AI-Engineer.pdf）。提交吗？
你      提交
Claude  3/3 已发出并记录到 Notion。明天的邮件同步会把确认信链接上。
```

### 模块
| 模块 | 位置 | 作用 |
|---|---|---|
| 知识库 | `.claude/skills/job-knowledge-base`、`tools/kb_*.py` | inbox → `knowledge/library/` 单元文件 + `manifest.yaml` + `PROFILE.md`；按上传入口合并或分开（不会提交到 git） |
| 引导问卷 | `config/profile.example.yaml` → `config/profile.yaml` | 个人信息、搜索条件、投递规则、标准答案 |
| 扫描与投递 | `.claude/skills/job-scan-apply` 等 | 精选表 → 挑选 → 预填 → 确认 → 提交 |
| 邮件同步与标签 | `.claude/skills/job-mail-sync`、`tools/sync_mail.py` | 邮件分类、更新 Notion、打 `applications` 标签、发现手动申请、历史回填 |
| Notion 申请表 | `tools/notion_setup.py` | 自动建表（[字段说明](docs/data-model.md)） |
| 看板 | `.claude/skills/job-dashboard`、`dashboard/index.html` | Notion 图表 + claude.ai 交互看板 |
| 文件上传 | `tools/upload_file.sh` | 驱动 macOS 打开对话框，把 PDF 传给公司官网 |
| 健康检查 | `tools/check_setup.py` | 一张清单检查以上所有配置 |

### 边界
- 不经你确认不会提交任何申请。一键投递按钮先列出来，你选了才点。
- 输入密码、验证码、注册官网账号、点击会创建账号的验证链接，都由你来做。
- 只上传表单要求的材料；强制要求求职信的岗位默认跳过。
- 凭证只保存在你电脑的 `.env`；简历、问卷答案和日志都不会进入 git。
- 招聘平台的条款通常限制自动化使用。本项目坚持每批由人挑选和确认，并设每日上限；如何使用由你自己负责。

### 踩过的坑
搭建过程中遇到的所有问题和解决办法（用错浏览器、一键投递直接发出、React 下拉框、shadow DOM 里的上传框、macOS 权限丢失、
合并 PDF、邮件回执没有公司名……）：**[docs/pitfalls.md](docs/pitfalls.md)**。各平台行为说明：**[docs/platforms.md](docs/platforms.md)**。

### 规划中
- 按岗位调整简历（从知识库重排、改写要点，每次投递保留版本）。
- 按你的文风起草和修改 Anschreiben，用于必须附求职信的岗位。

### 常见问题
- **Windows 可以用吗？** 除了文件上传助手（仅 macOS），其他都可以；上传时需要你拖一下文件。
- **不用 Gmail 可以吗？** 脚本基于 IMAP + Gmail 标签，其他邮箱需要小改 `tools/common.py`。
- **其他国家或平台？** 把搜索链接和平台行为写进 `docs/platforms.md`，skill 会读取。

---

<sub>MIT License · Built with the Claude desktop app.</sub>
