#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
安装脚本 - 将 feishu-md-converter 复制到 Claude Code skills 目录
"""

import os
import shutil
import argparse
from pathlib import Path

def install_skill(source_dir: Path, target_dir: Path, full: bool = False) -> bool:
    """
    安装 skill 到 Claude Code skills 目录

    Args:
        source_dir: 源目录（当前项目目录）
        target_dir: Claude Code skills 目录
        full: 是否完整安装（包含所有文件）

    Returns:
        安装是否成功
    """
    # 目标 skill 目录
    skill_dir = target_dir / "feishu-md-converter"

    # 必需文件
    required_files = [
        "SKILL.md",
        "skill-rules.json"
    ]

    # 完整安装文件
    full_files = required_files + [
        "README.md",
        "config.json.example"
    ]

    # Python 脚本
    py_scripts = [
        "feishu_to_md.py",
        "md_to_feishu_doc.py",
        "feishu_import_client.py",
        "feishu_ownership_transfer.py",
        "feishu_validator.py"
    ]

    # 创建目标目录
    skill_dir.mkdir(parents=True, exist_ok=True)

    # 检查必需文件
    print(f"检查必需文件...")
    missing_files = []
    for f in required_files:
        if not (source_dir / f).exists():
            missing_files.append(f)

    if missing_files:
        print(f"错误: 缺少必需文件: {', '.join(missing_files)}")
        return False

    print(f"✓ 所有必需文件存在")

    # 复制必需文件
    print(f"\n复制核心文件到 {skill_dir}...")
    for f in required_files:
        shutil.copy2(source_dir / f, skill_dir / f)
        print(f"  ✓ {f}")

    # 复制完整安装文件
    if full:
        print(f"\n复制完整安装文件...")
        for f in full_files:
            if (source_dir / f).exists():
                shutil.copy2(source_dir / f, skill_dir / f)
                print(f"  ✓ {f}")

        # 复制 docs 目录
        docs_dir = source_dir / "docs"
        if docs_dir.exists():
            target_docs = skill_dir / "docs"
            if target_docs.exists():
                shutil.rmtree(target_docs)
            shutil.copytree(docs_dir, target_docs)
            print(f"  ✓ docs/")

        # 复制 Python 脚本
        print(f"\n复制 Python 脚本...")
        for script in py_scripts:
            if (source_dir / script).exists():
                shutil.copy2(source_dir / script, skill_dir / script)
                print(f"  ✓ {script}")

    # 验证安装
    print(f"\n验证安装...")
    success = True

    for f in required_files:
        if not (skill_dir / f).exists():
            print(f"  ✗ {f} 未复制")
            success = False
        else:
            print(f"  ✓ {f}")

    print(f"\n{'='*60}")
    if success:
        print(f"✓ 安装成功！")
        print(f"\nSkill 目录: {skill_dir}")
        print(f"\n下一步:")
        print(f"1. 编辑 {skill_dir}/config.json.example 并复制为 config.json")
        print(f"2. 填写 app_id、app_secret 和 user_access_token")
        print(f"3. 测试: 编辑一个 .md 文件并输入相关关键词")
    else:
        print(f"✗ 安装失败，请检查上述错误")

    return success

def main():
    parser = argparse.ArgumentParser(description="安装 feishu-md-converter 到 Claude Code skills")
    parser.add_argument("--target", "-t",
                    default="~/.claude/skills",
                    help="Claude Code skills 目录路径（默认: ~/.claude/skills）")
    parser.add_argument("--full", "-f",
                    action="store_true",
                    help="完整安装（包含所有文件和 Python 脚本）")
    parser.add_argument("--source", "-s",
                    default=".",
                    help="源目录（默认: 当前目录）")

    args = parser.parse_args()

    # 展开路径
    source_dir = Path(args.source).expanduser().resolve()
    target_dir = Path(args.target).expanduser().resolve()

    print(f"源目录: {source_dir}")
    print(f"目标目录: {target_dir}")
    print(f"安装模式: {'完整' if args.full else '最小'}")
    print(f"{'='*60}\n")

    success = install_skill(source_dir, target_dir, full=args.full)

    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
