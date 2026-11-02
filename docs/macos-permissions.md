# macOS permission for file uploads · 文件上传权限

**Why** · Company career sites need a real file upload (CV, certificates). Claude's built-in browser has no upload tool,
and many forms hide the file input inside shadow DOM. `tools/upload_file.sh` therefore drives the normal macOS
"Open" dialog: `Cmd+Shift+G` → full path → Return → Return. That needs the **Accessibility** permission for the Claude app.

**为什么** · 公司官网投递需要真的上传文件。Claude 内置浏览器没有上传工具，很多表单的文件框藏在 shadow DOM 里。
所以 `tools/upload_file.sh` 直接操作 macOS 的"打开"对话框，这需要给 Claude 应用 **辅助功能** 权限。

## Turn it on · 开启
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
