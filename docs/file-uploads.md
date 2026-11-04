# File uploads on company career sites · 公司官网的文件上传

Platform quick-apply (LinkedIn Easy Apply, StepStone, Indeed) uses the CV stored in your platform profile — no upload needed.
Company portals (SmartRecruiters, Workday, Personio, Porsche, Oracle …) need a real file upload. Claude's built-in browser
has no upload tool, and a page on the internet may not read files from your computer — for good reasons. Three ways work:

平台快捷投递用平台里存好的简历，不需要上传。公司官网需要真正上传文件；Claude 内置浏览器没有上传工具，网页也不能直接读你电脑上的文件。可行的方法有三种：

| | Method · 方法 | System | One-time setup · 一次性设置 | Who clicks · 谁来点 |
|---|---|---|---|---|
| **A** | `tools/upload_file.sh` drives the macOS Open dialog in Claude's built-in browser | macOS | Accessibility permission for Claude → `docs/macos-permissions.md` | Claude |
| **B** | **Claude in Chrome** `file_upload` tool puts the file straight into the form | Windows, macOS | Google Chrome + the "Claude in Chrome" extension, connected to the Claude desktop app; log in to the career sites in Chrome | Claude |
| **C** | Manual: Claude opens the dialog and copies the path (`tools/copy_path.py`), you paste and press Enter | any | none | you (2 keys) |

**Recommendation · 推荐**: macOS → A (fallback C). **Windows → B** (fallback C).
macOS 用 A（备选 C）；**Windows 用 B**（备选 C）。

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

## C · Manual, any system
Claude clicks the choose-file control and runs `python3 tools/copy_path.py "<file>"`. In the dialog:
- Windows: click the "File name" box, **Ctrl+V**, **Enter**.
- macOS: **Cmd+Shift+G**, **Cmd+V**, **Enter**, **Enter**.
Claude 点开选择文件对话框并把路径复制到剪贴板；你在对话框里粘贴并回车即可。

## Tried and rejected · 试过但不可行
- Serving the file from a local web server and attaching it with page JavaScript: the built-in browser blocks requests
  from internet pages to your computer (`ERR_BLOCKED_BY_CLIENT`). That is a security boundary; do not work around it.
- Wrapping the macOS script in a self-built `.app`: every rebuild loses the Accessibility permission.
