# Knowledge base · 知识库

Everything Claude may upload or quote in an application. Contents of these folders are git-ignored.
Claude 投递时可以上传或引用的全部材料。文件夹内容不会进入 git。

| Folder | Put here | 放什么 |
|---|---|---|
| `cv/` | one PDF per CV variant, one page or two, no transcripts inside | 每个简历版本一个 PDF，不要把成绩单合并进去 |
| `certificates/` | degree certificate, transcripts, language certificates, Arbeitszeugnisse — one file each | 学位证、成绩单、语言证书、工作证明，每份单独一个 PDF |
| `cover_letters/` | past letters, used only as style samples | 过往求职信，仅作文风参考 |
| `other/` | anything else a form might ask for (publications list, portfolio PDF) | 其他（论文列表、作品集等） |

You do not need to sort files yourself: drop them into the chat during setup and Claude files them, splits merged PDFs,
and writes `manifest.yaml` (see `manifest.example.yaml`). 不用自己整理：配置时把文件拖进对话，Claude 会归类、拆分合并 PDF 并生成 `manifest.yaml`。
