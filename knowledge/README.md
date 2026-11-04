# Knowledge base · 知识库

Drop **every** document you might need into `inbox/` (or into the chat during setup) — unsorted, scanned, merged, photos are fine.
把可能用到的**所有**材料丢进 `inbox/`（或配置时直接拖进对话）——不用整理，扫描件、合并的 PDF、手机照片都可以。

Claude then (skill `job-knowledge-base`) · 然后 Claude 会：
1. reads every page, including scans · 逐页阅读（包括扫描件）
2. splits multi-document PDFs into **unit files**, one document each, consistently named · 把多文档 PDF 拆成**单元文件**（一份文件 = 一个文档），统一命名
3. writes `manifest.yaml` (machine index) and `PROFILE.md` (what each document is, what it proves, what is missing) · 生成索引和知识库画像（每个文档是什么、证明了什么能力、还缺什么）
4. at application time picks the right files per upload slot and merges or separates them in the right order · 投递时按页面上传入口决定合并还是分开、按什么顺序

| Folder | Content | Tracked by git |
|---|---|---|
| `inbox/` | new files to process · 待处理 | no |
| `originals/` | sources after processing, never uploaded · 原件存档，不上传 | no |
| `library/<kind>/` | unit files, the only files ever uploaded · 单元文件，唯一会被上传的文件 | no |
| `manifest.yaml`, `PROFILE.md` | generated index and profile · 自动生成 | no |

Kinds: `cv`, `cover_letter`, `degree`, `transcript`, `work_reference`, `certificate`, `language_certificate`, `award`,
`publication`, `reference_letter`, `id_document` (always sensitive), `other`. See `manifest.example.yaml`.
