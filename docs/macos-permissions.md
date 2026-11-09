# macOS permission for file uploads · 文件上传权限

**Why** · Company career sites need a real file upload (CV, certificates). Claude's built-in browser has no upload tool,
and many forms hide the file input inside shadow DOM. `tools/upload_file.sh` therefore drives the normal macOS
"Open" dialog: `Cmd+Shift+G` → full path → Return → Return. That needs the **Accessibility** permission for the Claude app.

**为什么** · 公司官网投递需要真的上传文件。Claude 内置浏览器没有上传工具，很多表单的文件框藏在 shadow DOM 里。
所以 `tools/upload_file.sh` 直接操作 macOS 的"打开"对话框，这需要给 Claude 应用 **辅助功能** 权限。

## Step by step · 一步一步
Nothing to download or install. The uploader is `tools/upload_file.sh`, a short AppleScript that macOS runs with its built-in
`osascript`. You only grant one permission. 不需要下载或安装任何东西：上传助手是 `tools/upload_file.sh`，由 macOS 自带的 `osascript` 运行，你只需要授权一次。

1. **Open the setting · 打开设置** — System Settings → Privacy & Security → **Accessibility**.
   系统设置 → 隐私与安全性 → **辅助功能**。
2. **Turn on Claude · 打开 Claude** — switch **Claude** on. Not in the list? Click **+**, choose Applications → Claude, enter your Mac password.
   把 **Claude** 的开关打开；列表里没有就点 **+** → 应用程序 → Claude，输入电脑密码。
3. **If macOS asks once more · 如果系统再弹一次** — "Claude wants to control System Events": click **OK** (it is listed under Privacy & Security →
   Automation). 出现"Claude 想要控制 System Events"时点 **好**（在 隐私与安全性 → 自动化 里可以看到）。
4. **Test it · 测试** — Claude opens `tools/upload_test.html` in its browser tab. Make sure that tab is in front, then Claude clicks the file
   box and runs `tools/upload_file.sh <a CV>` within 10 seconds. The page must then show the file name. You only watch.
   Claude 在内置浏览器里打开测试页；这个标签页必须在最前面，Claude 点一下文件框，10 秒内运行脚本，页面应显示文件名。你只需要看。
5. **Done · 完成** — from now on Claude uses it for every company-portal upload; there is nothing to start or keep running.
   以后每次公司官网上传 Claude 都会自动用它，不需要你启动或保持任何程序。

### What the script does · 脚本做了什么
It waits for the Open sheet of the Claude window, presses **Cmd+Shift+G**, types the full file path into the "Go to folder" field,
presses **Return** (selects the file) and **Return** again (Open). It uses key combinations, not button names, so it works in any system language.
等"打开"面板出现 → Cmd+Shift+G → 在"前往文件夹"里填完整路径 → 回车选中文件 → 再回车确认。只用快捷键、不依赖按钮文字，所以系统是什么语言都可以。

### What the messages mean · 报错含义
| Message | Cause · fix |
|---|---|
| `no file sheet open on Claude window 1` | the choose-file control was not clicked, more than 10 s passed, or the tab is **not the front tab** (a background tab never shows the sheet). Bring the tab to the front, click the control, run the script again. |
| `not allowed assistive access` | Accessibility is off for Claude, or was reset by an update → toggle it off and on (below). |
| `Go-to-folder field did not appear` | another window had focus; click the browser tab and retry. |
| `AppleEvent … (-10000)` | macOS sometimes reports this although the file **was** attached. Look at the page before retrying. |
| `file sheet still open after confirming` | the file could not be selected: wrong path, or the portal needs the type chosen first. |

## Turn it on again · 重新开启
1. System Settings → Privacy & Security → **Accessibility** · 系统设置 → 隐私与安全性 → **辅助功能**
2. Turn on **Claude**. If it is not listed: **+** → Applications → Claude. · 打开 **Claude**；不在列表里就点 **+** 添加。
3. Claude tests it on `tools/upload_test.html`. · Claude 会用测试页验证。

## If it stops working · 失效时
- After a Claude app update macOS may drop the grant: switch the toggle off and on. · Claude 更新后可能失效：关掉再打开开关。
- Do **not** wrap the script in a self-built `.app` (osacompile). Every rebuild is a new identity to macOS and the
  permission is lost again — we lost three rounds of re-authorisation this way.
  **不要**把脚本编译成自制 `.app`：每次重新编译在系统看来都是新程序，权限会丢。
- The dialog must belong to the Claude window: click the page's "choose file" control in the built-in browser first,
  then run the script within ~10 seconds. · 先在内置浏览器里点"选择文件"，10 秒内运行脚本。
