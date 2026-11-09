# File uploads on company career sites · 公司官网的文件上传

Platform quick-apply (LinkedIn Easy Apply, StepStone, Indeed) uses the CV stored in your platform profile — no upload needed.
Company portals (SmartRecruiters, Workday, Personio, Porsche, Oracle …) need a real file upload. Claude's built-in browser
has no upload tool, and a page on the internet may not read files from your computer — for good reasons. Three ways work (A–C); method D below lists candidates we have not tried yet:

平台快捷投递用平台里存好的简历，不需要上传。公司官网需要真正上传文件；Claude 内置浏览器没有上传工具，网页也不能直接读你电脑上的文件。可行的方法有三种（A–C），方法 D 是尚未试过的候选：

| | Method · 方法 | System | One-time setup · 一次性设置 | Who clicks · 谁来点 |
|---|---|---|---|---|
| **A** | `tools/upload_file.sh` drives the macOS Open dialog in Claude's built-in browser | macOS | Accessibility permission for Claude → `docs/macos-permissions.md` | Claude |
| **B** | **Claude in Chrome** `file_upload` tool puts the file straight into the form | Windows, macOS | Google Chrome + the "Claude in Chrome" extension, connected to the Claude desktop app; log in to the career sites in Chrome | Claude |
| **C** | Manual: Claude opens the dialog and copies the path (`tools/copy_path.py`), you paste and press Enter | any | none | you (2 keys) |

**Recommendation · 推荐**: macOS → A (fallback C). **Windows → B** (fallback C). **B has had reliability reports in 2026** (see below):
if its test fails, use C instead of debugging it. Method D lists maintained open-source alternatives we have not tried yet.
macOS 用 A（备选 C）；**Windows 用 B**（备选 C）。**B 在 2026 年有过稳定性问题的报告**（见下）：测试不通过就改用 C，不要长时间排查。方法 D 是还没试过的开源替代方案。

## A · macOS dialog script
The script is part of this repo (plain AppleScript run by the built-in `osascript`; no app to download). Click the page's
choose-file control in the built-in browser, then within ~10 s run `tools/upload_file.sh "/absolute/path/file.pdf"`.
脚本就是本仓库里的 AppleScript，由 macOS 自带的 `osascript` 运行，不需要下载任何程序。

## B · Claude in Chrome (Windows and macOS)
1. Install Google Chrome and the **Claude in Chrome** extension; connect it to the Claude desktop app (the extension shows how).
2. Log in to the career sites you use **in Chrome** (company portals keep their own logins anyway).
3. For a company-portal application Claude switches to Chrome: it fills the form there and attaches files with the
   `file_upload` tool — it locates the form's file input and sends the file directly, without any dialog.
   Limits: up to 10 MB per call; the files must be in a folder Claude may read (this repo folder is fine).
4. Scanning and platform quick-apply can stay in the built-in browser.
安装 Chrome 和 "Claude in Chrome" 扩展并连接到桌面端；在 Chrome 里登录招聘网站；遇到公司官网投递时 Claude 在 Chrome 里填表并直接附上文件，不弹对话框。

**Known issues with B (checked July 2026)** — the extension's `file_upload` exists, but public bug reports describe it failing in some
setups: not exposed to the Claude Code CLI's connection ([issue 35850](https://github.com/anthropics/claude-code/issues/35850), closed as
"not planned"; the reporter says the Claude desktop app can upload), and later reports of `Not allowed` errors, a path-versus-file-contents
mismatch between CLI and extension, and failures in Windows scheduled-task sessions. This project uses it from the desktop app; we have **not tested it
on Windows**. Always run the `tools/upload_test.html` check first.
B 的已知问题：扩展自带 `file_upload`，但公开的 bug 报告里它在部分环境下会失败（Claude Code CLI 看不到这个工具、`Not allowed` 报错、路径与文件内容协议不一致、
Windows 定时任务会话里失败）。本项目在桌面端使用它，**没有在 Windows 上实测**。先跑一遍测试页。

## C · Manual, any system
Claude clicks the choose-file control and runs `python3 tools/copy_path.py "<file>"`. In the dialog:
- Windows: click the "File name" box, **Ctrl+V**, **Enter**.
- macOS: **Cmd+Shift+G**, **Cmd+V**, **Enter**, **Enter**.
Claude 点开选择文件对话框并把路径复制到剪贴板；你在对话框里粘贴并回车即可。

## D · Open-source browser-automation servers (candidates, not tested here) · 开源浏览器自动化（候选，尚未实测）
Both put a file straight into the page's file input through the browser's automation protocol. No Open dialog, no Accessibility permission,
no front-tab requirement, and the same on macOS and Windows.
- **Playwright MCP** (Microsoft) — tool `browser_file_upload`: click the page's upload button first, then call it with absolute `paths`;
  paths are limited to the MCP workspace roots unless the server runs with `--allow-unrestricted-file-access`; drag-and-drop zones use `browser_drop`.
  [docs](https://playwright.dev/mcp/tools/file-upload)
- **Chrome DevTools MCP** (Chrome team) — tool `upload_file` with `uid` (the file input or the element that opens the chooser), `filePaths` (array)
  and `pageId`; paths must exist on the machine that runs the browser.
  [tool reference](https://github.com/ChromeDevTools/chrome-devtools-mcp/blob/main/docs/tool-reference.md)
- Trade-offs: they drive **their own browser window**, so you log in to the career sites once more there, and the MCP server has to be added to the
  Claude app. If you try one, add it as method E in this file with the exact steps that worked.
Playwright 与 Chrome DevTools 的 MCP 服务都通过浏览器自动化协议直接把文件放进 file input：不弹对话框、不需要辅助功能权限、不要求标签页在前台，Windows 和 macOS 一样用。
代价：它们操作的是**自己的浏览器窗口**，需要在那里再登录一次招聘网站，并且要把 MCP 服务添加到 Claude 应用。试用后把有效的步骤补在本文件里。

## Tried and rejected · 试过但不可行
- Serving the file from a local web server and attaching it with page JavaScript: the built-in browser blocks requests
  from internet pages to your computer (`ERR_BLOCKED_BY_CLIENT`). That is a security boundary; do not work around it.
- Wrapping the macOS script in a self-built `.app`: every rebuild loses the Accessibility permission.
