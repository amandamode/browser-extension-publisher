# 浏览器插件 GitHub 发布 Skill

把已有的浏览器插件整理成可审阅、可下载的 GitHub 发布版本。先检查与准备，用户确认后发布，再核对源码和下载包。

| Skill | 适用请求 | 版本 |
| --- | --- | --- |
| [browser-extension-publisher](SKILL.md) | 把浏览器插件发布到 GitHub；更新插件版本与安装包 | 1.0.0 |

主要面向有 `manifest.json` 的 Chrome/Chromium 插件。提供中文流程指引和 Python 本地辅助工具，不是无人值守发布服务，不包含 Chrome 网上应用店上架。

## 安装

使用 [skills CLI](https://github.com/vercel-labs/skills) 安装到当前项目的 Codex：

```sh
npx skills add amandamode/browser-extension-publisher --skill browser-extension-publisher --agent codex
```

仅查看可发现的 Skill（不安装 Skill，但运行 npx 本身可能下载 CLI）：

```sh
npx skills add amandamode/browser-extension-publisher --list
```

CLI 需要 Node.js/npm。命令按官方语法编写；本项目尚未实测 CLI 安装与自动触发，执行前请确认环境和安装范围。其他 agent 按官方 CLI 支持情况选择。

也可在 [Releases](https://github.com/amandamode/browser-extension-publisher/releases) 下载完整 ZIP，解压后让助手读取 `browser-extension-publisher/SKILL.md`。下载和解压不等于已安装，具体安装目录按使用环境确定。

## 使用

安装后向助手说明：

> 使用 $browser-extension-publisher，先检查我的浏览器插件并准备 GitHub 发布预览，确认后再发布。插件目录是……

提供插件目录、GitHub 账号/组织、仓库名、公开/私有、版权选择和版本。助手会检查现有状态，说明需要新建或修改的范围，准备说明与包，取得具体授权后上传，再核验结果。已明确覆盖同一动作的授权不重复询问。

## 工作流程

1. 找到插件，检查 Git 状态、manifest、构建产物和既有发布。
2. 检查权限、敏感内容、数据流向、第三方资源与许可证。
3. 在经批准的独立副本中准备源码、文档、文件清单和安装 ZIP。
4. 展示账号、仓库、可见性、版本、版权、文件及操作预览。
5. 用户确认后通过现有 GitHub 工具或浏览器发布，核对源码文件和实际下载附件。

没有 GitHub CLI 时可使用浏览器或人工步骤，不默认安装新工具。Git 管版本与 push；GitHub CLI/API 管仓库及 Release；Actions/CI 只有实际配置并运行才提供相应自动检查。

## 本地辅助工具

需要 Python 3.9+，只使用标准库。工具不登录、不联网、不创建仓库、不 commit/push，也不运行插件。

| 命令 | 用途 |
| --- | --- |
| `inspect` | 只读清单、manifest 直接引用、权限与常见敏感格式线索 |
| `package` | 获准后按明确清单生成新 ZIP，不覆盖旧包 |
| `verify-tree` | 对照完整 GitHub tree JSON，检查文件、内容哈希和模式 |
| `verify-asset` | 对照本地包与独立下载附件的 SHA-256 |

详细参数、局限和失败处理见 [辅助工具说明](references/local-tools.md)。敏感格式扫描只是线索，不能证明没有秘密；manifest 引用检查不覆盖 HTML/CSS/JS 的全部间接依赖。Git 历史和真实浏览器效果需另行核验。

## 验证状态

2026-10-12：

- Skill 基础结构校验通过；12 项本地工具检查通过。
- 对留页发布提交只读核对：17 个远端源码文件一致。
- 在临时目录重打包：10 个安装文件与已有包的成员内容一致。
- 留页实际 Release 下载附件 SHA-256 与本地已有发布包一致。
- 尚未实测这个 Skill 的 CLI 安装/自动触发，也未用它向另一个真实插件仓库完成一次全新发布。

可运行已有工具检查：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/test_release_tools.py -v
```

逻辑检查通过不代表任意网页的真实浏览器效果通过，也不代表插件已获商店审核。

## 反馈与改进

欢迎通过 Issues 提供插件类型、复现步骤、工具版本和已脱敏的错误信息。不要公开上传 token、私人收藏、网页正文、聊天记录或含敏感信息的截图。修改可通过 Pull Request 提交。

## 来源与版权

本项目从 [留页首次 GitHub 发布实践](references/liuye-case.md)整理而来；没有复制乔木两个项目的代码。流程中涉及的官方工具文档见 [GitHub 发布说明](references/github-flow.md)。

本 Skill 使用 [MIT](LICENSE)，Copyright (c) 2026 amandamode。MIT 仅适用于本仓库内容；案例中提及的留页插件仍按其自身版权说明处理，不因本 Skill 开源而改变许可。
