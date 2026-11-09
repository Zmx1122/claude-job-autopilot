# Credentials · 凭证

Two secrets are needed. Both go into `.env`, which never leaves your Mac. 只需要两个密钥，都写进 `.env`，不会离开你的电脑。

## Notion

**English**
1. Open <https://www.notion.so/profile/integrations> → **New integration**.
2. Name `Job Autopilot`, type **Internal**, pick your workspace → Save.
3. Copy the **Internal Integration Secret** (starts with `ntn_`) → `NOTION_TOKEN` in `.env`.
4. In Notion create a page called **Job Search** (anywhere you like).
5. On that page: `•••` (top right) → **Connections** → search `Job Autopilot` → confirm. Without this step the token sees nothing.
6. Copy the page link (`•••` → Copy link) → `NOTION_PARENT_PAGE_ID` in `.env` (the whole link is fine).
7. Claude runs `python3 tools/notion_setup.py`, which creates the **Job Applications** database on that page.

**中文**
1. 打开 <https://www.notion.so/profile/integrations> → **New integration**。
2. 名字填 `Job Autopilot`，类型选 **Internal**，选择你的 workspace → 保存。
3. 复制 **Internal Integration Secret**（`ntn_` 开头）→ 填到 `.env` 的 `NOTION_TOKEN`。
4. 在 Notion 新建页面 **Job Search**。
5. 页面右上角 `•••` → **Connections** → 搜索 `Job Autopilot` → 确认。不做这一步 token 什么都看不到。
6. 复制页面链接 → 填到 `NOTION_PARENT_PAGE_ID`（整条链接即可）。
7. Claude 运行 `python3 tools/notion_setup.py`，在该页面下建好 **Job Applications** 数据库。

## Gmail

**English**
1. Use the Gmail address you apply with. Every portal sends its confirmations there; that is how the tracker updates itself.
2. Turn on **2-Step Verification**: <https://myaccount.google.com/signinoptions/twosv>.
3. Create an **app password**: <https://myaccount.google.com/apppasswords> → name `job-autopilot` → copy the 16 letters.
4. `.env`: `IMAP_USER=you@gmail.com`, `IMAP_APP_PASSWORD=abcd efgh ijkl mnop` (spaces are fine).
5. Claude runs `python3 tools/gmail_setup.py`. If the label `applications` does not exist, Claude asks and then creates it
   (`--create`), or you choose an existing label such as `Bewerbungen` and Claude sets `GMAIL_LABEL`.
   Manual alternative: Gmail left sidebar → **Labels** → **+** → `applications`.
6. Access is read-only except adding that label. Revoke any time on the app-passwords page.

**中文**
1. 用你投递时填写的 Gmail。各公司的确认信、面试邀请、拒信都会发到这里，表格就靠它自动更新。
2. 开启 **两步验证**：<https://myaccount.google.com/signinoptions/twosv>。
3. 生成 **应用专用密码**：<https://myaccount.google.com/apppasswords> → 名称 `job-autopilot` → 复制 16 个字母。
4. `.env` 里填 `IMAP_USER` 和 `IMAP_APP_PASSWORD`（带空格也可以）。
5. Claude 运行 `python3 tools/gmail_setup.py`。如果没有 `applications` 标签，Claude 会先问你，再用 `--create` 建好；
   也可以选用你已有的标签（如 `Bewerbungen`），Claude 会改 `GMAIL_LABEL`。手动建法：Gmail 左栏 **标签** → **+** → `applications`。
6. 除了打标签以外全部只读。随时可以在应用专用密码页面撤销。

## Where secrets are stored · 密钥存在哪里
Standard: the **`.env`** file in this folder — plain text on your Mac, git-ignored, **not** in the backup, and `tools/check_public.py`
blocks any commit that contains them. There is no keychain integration; keep a copy in your password manager.
标准做法：本文件夹里的 **`.env`**——你电脑上的明文文件，不进 git、不进备份，提交时 `tools/check_public.py` 会拦截。没有接入系统钥匙串，请另存一份到密码管理器。

## Where to type secrets · 在哪里填密钥
1. **Safest · 最稳妥**: open `.env` (Claude opens it for you) and paste there yourself. 在 Claude 帮你打开的 `.env` 里自己粘贴。
2. **Also possible · 也可以**: paste it into the chat and Claude writes it to `.env` and does not repeat it — **but it then stays in the
   conversation history, so you accept a potential leak risk.** Not sure? Revoke it afterwards (Notion integrations page / Google
   app-passwords page) and create a new one.
   直接贴在对话框里，Claude 会写进 `.env`、不会复述——**但它会留在对话记录里，你需要接受潜在的泄露风险。** 不放心就事后撤销（Notion 集成页 /
   Google 应用专用密码页）并重新生成。
