# GitHub 发布与核验

## 选择渠道

先只读确认目标账号、仓库、远端分支、同名标签及 Release。已存在的仓库按用户批准的更新范围处理，不创建重复项目。优先使用已连接的工具、已安装的 GitHub CLI；不可用时用浏览器。工具不能替代授权。

| 工具 | 作用 | 容易误判的地方 |
| --- | --- | --- |
| Git | 本地版本、commit、向远端 push | 有 `.git` 不代表已公开；当前目录无秘密不代表历史无秘密 |
| GitHub CLI/API | 创建/查看仓库、文件操作、标签与 Release 附件 | 命令退出成功不能替代下载内容核对 |
| GitHub 浏览器 | 创建仓库、上传已批准文件、建立 Release | 上传副本的子目录要正确；ZIP 不受 `.gitignore` 过滤 |
| Actions/CI | 按已有工作流自动构建、测试或发布 | 只有配置并实际运行了对应流程才算证据；不默认新增工作流 |

## 命令方式

以下说明动作含义，不是一键执行脚本。按现场工具版本检查帮助，用结构化参数或可靠 shell 引号；多行发布文案放经批准的文件，用 `--notes-file` 等参数传递，不把文案拼接成命令。

1. 只读检查 `gh auth status`、Git 状态和远端。不要打印 token，也不要为了身份确认调用 token 输出接口。
2. 确认现有身份符合目标账号；账号不符时让用户选择，不能静默改用其他账号。
3. 新建仓库用明确 OWNER/REPO 及 `--public` 或 `--private`；不加默认 MIT 参数。`gh repo create --source` 涉及本地 Git 项目，`--push` 会上传提交；这些需在预览中说明。不要把包含未经审查历史的原项目直接推送。
4. 本地 commit 前检查 staged 文件和差异；push 前核对目标 URL、分支以及需要上传的历史。不存在 Git 仓库时只在用户批准的候选目录初始化。
5. Release 可以指向明确提交创建新标签，或用已存在且校验好的标签。CLI 可用 `--target` 指向完整 SHA，`--verify-tag` 要求远端标签已经存在；根据实际情况选用，不能同时假定标签既不存在又可 verify。
6. 首次试用或实际运行验证不足时提出 prerelease 选项，不擅自改用户已确认的发布状态。上传明确的安装 ZIP，避免通配符夹带其他材料。
7. 写操作中断后先查仓库、标签、Release 和附件状态；同名存在时比较内容，不用 `--clobber` 或删除后重建掩盖差异。

## 浏览器方式

用户自行完成登录、密码、验证码等需其操作的步骤。通过当前页面的可见控件确认身份、仓库名和公开范围。现有仓库不重复创建。

只上传候选源码清单；子目录文件需保留结构，不将 tests 里的文件扁平放进根目录。上传完成后查看页面文件列表和提交。源码上传与 Release 附件上传是两个动作：前者可供查看/开发，后者提供方便安装的下载包。

创建 Release 时核对标签、目标提交、标题、说明、试用状态和已上传附件，点击发布一次，随后检查发布页面。UI 工作期间遵守浏览器工具说明，不用隐藏网络、提取凭据或无授权接口补救。

## 远端核验

工具支持时通过只读 API 或 CLI 取得 repo、commit、Git tree、Release 和 tag 信息。私有仓库用用户已授权的身份；404 也可能表示无权限，不能据此反复创建。

- 根据所确认分支取得提交 SHA；对固定 SHA 获取完整递归 Git tree。`truncated: true` 时报告未核验，按子树分批核对或切换受支持的完整克隆，不忽略截断标记。
- `release_tools.py verify-tree` 比较候选源码清单和完整 tree JSON：Git blob SHA-1 是 `SHA1(b"blob " + 长度 + b"\0" + 内容)`，不是直接对文件内容求 SHA-1。额外文件也要审核，不能无视。
- 确认 Release 不为 draft，标签和 prerelease 符合预览；标签可能是 annotated tag，必要时解引用到最终 commit 再比较。
- 下载特定安装附件，不把 GitHub 自动生成的 Source code ZIP 当安装包。用 `verify-asset` 比较本地和下载包字节哈希；API/UI 还需核对附件名与大小、所属版本。
- 私有下载失败时不要改公开范围；同一失败分析一次，使用已授权工具或请用户下载指定附件。

## 官方资料

具体执行时检查当前版本。2026-10-12 查阅过：

- [gh repo create](https://cli.github.com/manual/gh_repo_create)
- [gh release create](https://cli.github.com/manual/gh_release_create)
- [Git trees API](https://docs.github.com/en/rest/git/trees)

该 Skill 不自动安装 CLI、创建 CI 或申请新权限，不承诺商店上架。
