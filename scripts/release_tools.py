#!/usr/bin/env python3
"""Offline helpers. No installs, Git changes, credential access or network writes."""
import argparse
import fnmatch
import hashlib
import json
import os
import re
import sys
import zipfile
from pathlib import Path, PurePosixPath


class CheckError(Exception):
    pass


SECRET_RULES = {
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "github_token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"),
    "aws_access_key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "possible_secret_assignment": re.compile(r'''(?i)\b(?:api[_-]?key|access[_-]?token|client[_-]?secret|password)\s*[=:]\s*["'][^"'\n]{12,}["']'''),
    "personal_absolute_path": re.compile(r"(?:/Users/|/home/|[A-Za-z]:\\Users\\)"),
    "email_for_review": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
}
SCAN_LIMIT = 2 * 1024 * 1024


def digest(data):
    return hashlib.sha256(data).hexdigest()


def blob_sha(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def root_path(value):
    root = Path(value).expanduser()
    if root.is_symlink() or not root.is_dir():
        raise CheckError("root 必须是普通目录，不能是符号链接")
    return root.resolve()


def clean_name(value):
    if not isinstance(value, str) or not value or "\\" in value or any(ord(c) < 32 for c in value):
        raise CheckError("文件清单必须使用非空、相对的 POSIX 路径")
    p = PurePosixPath(value)
    if p.is_absolute() or re.match(r"^[A-Za-z]:", value) or any(c in ("", ".", "..") for c in value.split("/")):
        raise CheckError("拒绝绝对路径、空路径片段或目录越界")
    if ".git" in p.parts:
        raise CheckError("不得将 .git 纳入发布清单")
    return value


def checked_file(root, name):
    name = clean_name(name)
    p = root
    for part in PurePosixPath(name).parts:
        p = p / part
        if p.is_symlink():
            raise CheckError("拒绝文件或目录符号链接：" + name)
    if not p.is_file() or not p.resolve().is_relative_to(root):
        raise CheckError("清单文件不存在或不是普通文件：" + name)
    return p


def json_file(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def file_list(path):
    names = json_file(path)
    if not isinstance(names, list) or not names:
        raise CheckError("文件清单 JSON 必须是非空字符串数组")
    names = [clean_name(n) for n in names]
    if len(names) != len(set(names)):
        raise CheckError("清单包含重复文件")
    return sorted(names)


def inventory(root):
    names, links = [], []
    for folder, dirs, files in os.walk(root, followlinks=False):
        for d in list(dirs):
            p = Path(folder) / d
            if d == ".git":
                dirs.remove(d)
            elif p.is_symlink():
                links.append(p.relative_to(root).as_posix())
                dirs.remove(d)
        for f in files:
            p = Path(folder) / f
            rel = p.relative_to(root).as_posix()
            if f == ".git":
                continue
            if p.is_symlink():
                links.append(rel)
            else:
                names.append(rel)
    return sorted(names), sorted(links)


def manifest_refs(m):
    refs = []
    def add(value):
        if isinstance(value, str) and value:
            refs.append(value)
        elif isinstance(value, list):
            for item in value:
                add(item)
    for key in ("action", "browser_action", "page_action"):
        obj = m.get(key, {})
        if isinstance(obj, dict):
            add(obj.get("default_popup"))
            icon = obj.get("default_icon", {})
            add(list(icon.values()) if isinstance(icon, dict) else icon)
    add(list(m.get("icons", {}).values()))
    bg = m.get("background", {})
    add(bg.get("service_worker")); add(bg.get("scripts")); add(bg.get("page"))
    add(m.get("options_page")); add(m.get("devtools_page"))
    add(m.get("options_ui", {}).get("page"))
    add(m.get("side_panel", {}).get("default_path"))
    add(list(m.get("chrome_url_overrides", {}).values()))
    for item in m.get("content_scripts", []):
        add(item.get("js")); add(item.get("css"))
    for item in m.get("web_accessible_resources", []):
        add(item.get("resources") if isinstance(item, dict) else item)
    add(m.get("sandbox", {}).get("pages"))
    if m.get("default_locale"):
        add("_locales/" + m["default_locale"] + "/messages.json")
    return sorted(set(refs))


def manifest_check(root, available):
    m = json_file(checked_file(root, "manifest.json"))
    if not isinstance(m, dict) or not all(m.get(k) for k in ("name", "version", "manifest_version")):
        raise CheckError("manifest 缺少 name/version/manifest_version")
    missing, invalid = [], []
    for ref in manifest_refs(m):
        normalized = ref[1:] if ref.startswith("/") else ref
        try:
            clean_name(normalized)
            if not any(fnmatch.fnmatchcase(n, normalized) for n in available):
                missing.append(ref)
        except CheckError:
            invalid.append(ref)
    return m, {"missing": missing, "invalid": invalid}


def scan(root, names):
    findings, skipped = [], []
    for name in names:
        p = checked_file(root, name)
        parts = PurePosixPath(name).parts
        if any(s == ".env" or s.startswith(".env.") or s in (".ssh", ".aws", "User Data") for s in parts) or p.suffix.lower() in (".pem", ".key", ".p12"):
            findings.append({"file": name, "rule": "sensitive_filename"})
        if p.stat().st_size > SCAN_LIMIT:
            skipped.append({"file": name, "reason": "large_file"})
            continue
        data = p.read_bytes()
        try:
            text = data.decode("utf-8")
            if "\0" in text:
                raise UnicodeError()
        except UnicodeError:
            skipped.append({"file": name, "reason": "binary_or_non_utf8"})
            continue
        for rule, pattern in SECRET_RULES.items():
            for match in pattern.finditer(text):
                # Never output the matched value or surrounding text.
                findings.append({"file": name, "line": text.count("\n", 0, match.start()) + 1, "rule": rule})
    return findings, skipped


def inspect(args):
    root = root_path(args.root)
    names, links = inventory(root)
    m, refs = manifest_check(root, names)
    findings, skipped = scan(root, names)
    return {"mode": "read_only_inspection", "name": m["name"], "version": m["version"],
            "manifest_version": m["manifest_version"], "minimum_chrome_version": m.get("minimum_chrome_version"),
            "permissions": m.get("permissions", []), "host_permissions": m.get("host_permissions", []),
            "optional_permissions": m.get("optional_permissions", []), "optional_host_permissions": m.get("optional_host_permissions", []),
            "file_count": len(names), "files": names, "symlinks": links, "manifest_references": refs,
            "findings": findings, "unscanned_content": skipped,
            "limitations": ["扫描只提供常见线索，不能证明无敏感内容", "未检查 Git 历史", "HTML/CSS/JS 的间接依赖须人工核对", "未运行插件或测试", "不是完整 manifest schema 校验"]}


def package(args):
    root = root_path(args.root)
    names = file_list(args.files)
    if "manifest.json" not in names:
        raise CheckError("安装 ZIP 清单必须在根目录包含 manifest.json")
    paths = {n: checked_file(root, n) for n in names}
    m, refs = manifest_check(root, names)
    if refs["missing"] or refs["invalid"]:
        raise CheckError("安装清单缺少或含无效的 manifest 引用；先执行 inspect 查看线索")
    findings, skipped = scan(root, names)
    blocked = [f for f in findings if f["rule"] in ("sensitive_filename", "private_key", "github_token", "aws_access_key")]
    if blocked:
        return {"packaged": False, "reason": "疑似凭据，需移除后重新审阅", "findings": blocked}, 2
    out = Path(args.output).expanduser()
    resolved = out.resolve()
    if resolved.is_relative_to(root) or not out.parent.is_dir() or out.suffix.lower() != ".zip":
        raise CheckError("输出必须是插件目录外、已有父目录内的新 ZIP")
    if out.exists() or out.is_symlink():
        raise CheckError("拒绝覆盖已有输出")
    hashes = {n: digest(p.read_bytes()) for n, p in paths.items()}
    with out.open("xb") as handle:
        with zipfile.ZipFile(handle, "w", zipfile.ZIP_DEFLATED) as z:
            for name in names:
                data = paths[name].read_bytes()
                if digest(data) != hashes[name]:
                    raise CheckError("打包期间源文件发生变化；输出未核验")
                info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                z.writestr(info, data)
    with zipfile.ZipFile(out) as z:
        if z.namelist() != names or z.testzip() is not None or any(digest(z.read(n)) != hashes[n] for n in names):
            raise CheckError("包内容核验失败；不要发布该输出")
    if any(digest(p.read_bytes()) != hashes[n] for n, p in paths.items()):
        raise CheckError("源文件核验失败；不要发布该输出")
    return {"packaged": True, "version": m["version"], "file_count": len(names), "files": names,
            "sha256": digest(out.read_bytes()), "bytes": out.stat().st_size, "source_unchanged": True,
            "review_findings": findings, "unscanned_content": skipped, "remote_status": "not_uploaded"}, 0


def verify_tree(args):
    root = root_path(args.root)
    names = file_list(args.files)
    tree = json_file(args.tree)
    if not isinstance(tree, dict) or tree.get("truncated") is not False or not isinstance(tree.get("tree"), list) or not tree.get("sha"):
        raise CheckError("必须提供完整 Git tree API JSON（含 sha、tree 与 truncated:false）")
    entries = tree["tree"]
    remote = {}
    for item in entries:
        name = item["path"]
        if name in remote:
            raise CheckError("远端树包含重复路径")
        if item["type"] != "tree":
            remote[name] = item
    expected = {n: checked_file(root, n) for n in names}
    missing = sorted(set(expected) - set(remote))
    extra = sorted(set(remote) - set(expected))
    different, modes = [], []
    for name in set(expected) & set(remote):
        item = remote[name]
        p = expected[name]
        if item["type"] != "blob" or item["sha"] != blob_sha(p.read_bytes()):
            different.append(name)
        expected_mode = "100755" if p.stat().st_mode & 0o111 else "100644"
        if item.get("mode") != expected_mode:
            modes.append(name)
    ok = not (missing or extra or different or modes)
    return {"verified": ok, "tree_sha": tree["sha"], "expected_files": len(expected), "remote_files": len(remote),
            "missing": missing, "extra": extra, "different": sorted(different), "mode_differences": sorted(modes),
            "scope": "源码树内容；不证明仓库可见性、标签、Release、下载包或浏览器效果"}, 0 if ok else 2


def verify_asset(args):
    local, downloaded = Path(args.local), Path(args.downloaded)
    if local.is_symlink() or downloaded.is_symlink() or not local.is_file() or not downloaded.is_file():
        raise CheckError("请提供两个普通文件")
    if local.resolve() == downloaded.resolve():
        raise CheckError("下载包必须是另一份独立文件，不能用本地包核对自身")
    lh, dh = digest(local.read_bytes()), digest(downloaded.read_bytes())
    ok = lh == dh
    return {"verified": ok, "local_sha256": lh, "downloaded_sha256": dh,
            "local_bytes": local.stat().st_size, "downloaded_bytes": downloaded.stat().st_size,
            "scope": "两文件字节一致性；下载来源、仓库及所属 Release 仍需核对"}, 0 if ok else 2


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    s = sub.add_parser("inspect", help="只读目录清单、manifest 引用和敏感格式线索")
    s.add_argument("--root", required=True)
    s = sub.add_parser("package", help="获准后按明确清单生成新安装 ZIP；不覆盖")
    s.add_argument("--root", required=True); s.add_argument("--files", required=True); s.add_argument("--output", required=True)
    s = sub.add_parser("verify-tree", help="只读核对已取得的完整 GitHub tree JSON")
    s.add_argument("--root", required=True); s.add_argument("--files", required=True); s.add_argument("--tree", required=True)
    s = sub.add_parser("verify-asset", help="只读比较本地 ZIP 与另行下载的附件")
    s.add_argument("--local", required=True); s.add_argument("--downloaded", required=True)
    args = p.parse_args(argv)
    try:
        result = {"inspect": inspect, "package": package, "verify-tree": verify_tree, "verify-asset": verify_asset}[args.command](args)
        payload, code = result if isinstance(result, tuple) else (result, 0)
    except (CheckError, OSError, ValueError, TypeError, KeyError, AttributeError, zipfile.BadZipFile) as exc:
        payload, code = {"ok": False, "error": str(exc) if isinstance(exc, CheckError) else type(exc).__name__ + "：检查输入文件与格式"}, 2
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())
