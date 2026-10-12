# 留页首次发布案例

历史实践日期：2026-10-11。仅用于理解流程，执行新任务时重新核实当前状态。

发布对象是浏览器插件，不是 agent Skill。用户确认的仓库为 `amandamode/liuye-chrome-extension`，公开，保留版权，不采用 MIT。

- [源码仓库](https://github.com/amandamode/liuye-chrome-extension)
- [v0.3.0 试用版](https://github.com/amandamode/liuye-chrome-extension/releases/tag/v0.3.0)
- 当时核验的发布提交：`b2bb24860b04fcaf7bb6dc32c123b7c72d62573c`
- 源码副本：17 个文件；安装 ZIP：10 个文件，manifest 位于根目录。
- 安装附件：`liuye-chrome-extension-v0.3.0.zip`，23,088 字节。
- 安装附件 SHA-256：`ef7110e1ed49940c17d7a3b6a6be18b446b0fdb6049004a06c0de7f842fcb2eb`。

当时没有 gh，使用 GitHub 浏览器完成源码和 Release 发布。随后只读 API 核对完整源码清单与 blob 哈希，再读取实际下载包核对 SHA-256，全部一致。

保留原插件目录及历史成果，只准备独立候选副本。聊天记录、私人路径核对记录、用户收藏/正文备份和被否决的 MIT 草案留在发布范围外；必要运行文件、已有测试和公开文档列入明确源码清单。

已有 11 项逻辑测试通过，但本次发布副本未重新完成真实 Chrome 人工验收；Release 因此明确标为首次公开试用版，没有宣称 Chrome 商店上架。

旧的发布前预览曾写“尚未上传”，那是该文件生成时的状态；不能用准备阶段的报告否定后来的发布，也不能仅凭历史案例认定现在的远端未变。

可复用的是分阶段核验、源码/安装包区分、用户选择版权以及工具缺失时使用浏览器。账号、仓库、署名、版本、文件数量、哈希和“不外传”结论都不可当成新插件默认值。
