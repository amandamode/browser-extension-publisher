# 本地检查与打包工具

`scripts/release_tools.py` 只用 Python 3.9+ 标准库，无需安装依赖。不会登录、访问网络、创建仓库、commit、push 或执行插件代码。inspect / verify 命令只读，JSON 输出到屏幕；保存输出为文件仍属于写入，需在授权范围内。

下面示例中的路径是占位说明，执行时换成实际路径，并采用可靠的参数传递方式。不要把用户名、文案或用户路径未经引用拼接进 shell 命令。

## 只读检查

```sh
python3 scripts/release_tools.py inspect --root /path/to/extension
```

列出 manifest 版本、权限、目录文件、符号链接、缺失引用和常见敏感格式。报告只显示文件/行号/规则，不回显疑似秘密。邮箱、个人路径和疑似密钥赋值可能是假阳性，需人工检查。二进制、非 UTF-8 和超过 2 MiB 的文件会列为未扫描。`.git` 不扫描，推送历史时需另行检查。

返回 0 只表示检查运行完成，不表示通过隐私审核。图标等二进制需人工确认权利与内容，HTML/CSS/JS 中的间接依赖也需人工检查。

## 明确文件清单

清单为 JSON 字符串数组，例如：

```json
["manifest.json", "background.js", "popup.html", "popup.js", "icons/icon.png", "COPYRIGHT.md"]
```

从已检查的候选副本/构建产物选出真实文件，不复制示例清单。可以包含中文和子目录。源码和安装包分别用清单；清单文件放在待上传范围之外。脚本拒绝 `.git`、绝对路径、越界、符号链接、重复项和不存在的文件。

## 获准后打包

```sh
python3 scripts/release_tools.py package --root /path/to/loadable-extension --files /path/to/review/install-files.json --output /path/to/releases/plugin-v1.0.0.zip
```

输出父目录需已存在，ZIP 必须在插件目录外；同名输出拒绝覆盖。安装清单需在根目录包含 manifest 和其明确引用，通配资源至少匹配一个文件。仅能检查 manifest 直接引用，不保证全部运行依赖完整。

脚本阻止明显私钥、常见 GitHub/AWS 凭据及敏感文件名；其他扫描发现保留在 `review_findings` 供人工处理，不据此判断全部安全。发现问题后修正经批准的候选副本，再重新审阅。不得用“脚本没拦”替代审核。

按清单生成包，重新读取包成员、检查 CRC、逐项 SHA-256、核对源文件未变。成功输出 `packaged:true`、文件数、大小和 SHA-256。`remote_status:not_uploaded` 表示仅完成本地工作；不代表后来永久未上传。

## 源码远端核验

先通过可用的授权连接器、CLI 或只读公共 API，获取已确认提交的完整递归 Git tree JSON。私有仓库不得因为读取失败擅自改成公开。工具不处理任何凭据。

```sh
python3 scripts/release_tools.py verify-tree --root /path/to/repository-candidate --files /path/to/review/source-files.json --tree /path/to/review/remote-tree.json
```

树截断、漏文件、额外文件、内容哈希或文件模式变化都返回非零。模式差异（比如网页上传丢了执行位）需要解释并修正/调整经批准副本，不能把差异当成通过。tree 是目录对象，不是 commit；取得 JSON 时另行记录其对应提交。

## 安装附件核验

从目标 Release 下载明确附件，再比较：

```sh
python3 scripts/release_tools.py verify-asset --local /path/to/plugin.zip --downloaded /path/to/downloaded/plugin.zip
```

必须是不同路径的独立文件。脚本只证明两份字节一致；仍需核对下载来源、目标账号/仓库、版本、附件名与发布状态。

## 失败处理

工具错误或验证不一致返回 2，保留线索，不自动修复、删除或重试。打包过程中失败可能留下未核验输出；不要发布它，也不要未经批准删除它，选择获准的新输出路径。先分析原因，只在输入或条件有实际变化后再试。
