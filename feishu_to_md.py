#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Feishu → Markdown (文件夹支持版)
将飞书文档转换为 Markdown 文件，方便导入知识库进行 RAG
支持标题、列表、表格、粗体、代码块、数学公式等格式
支持普通文档(docx)和知识库(wiki)两种格式
支持文件夹递归查找
支持图片下载到本地
"""

import json
import os
import sys
import urllib.request
import urllib.error
import urllib.parse
import argparse
import re
import shutil
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

# 设置标准输出编码为 UTF-8（Windows 编码问题修复）
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def load_json(path: str) -> Dict[str, Any]:
    """加载 JSON 配置文件"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def request_json(method: str, url: str, headers: Dict[str, str] = None, data_obj: Dict[str, Any] = None) -> Dict[str, Any]:
    """发送 HTTP 请求并返回 JSON 响应"""
    data = None
    req_headers = headers or {}
    if data_obj is not None:
        data = json.dumps(data_obj, ensure_ascii=False).encode("utf-8")
        req_headers = dict(req_headers)
        req_headers.setdefault("Content-Type", "application/json; charset=utf-8")
    req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
    with urllib.request.urlopen(req) as resp:
        body = resp.read().decode("utf-8")
        return json.loads(body)


def get_tenant_access_token(app_id: str, app_secret: str, api_base: str) -> str:
    """获取应用身份 token"""
    url = f"{api_base}/open-apis/auth/v3/tenant_access_token/internal"
    obj = request_json("POST", url, data_obj={"app_id": app_id, "app_secret": app_secret})
    if obj.get("code") == 0 and obj.get("tenant_access_token"):
        return obj["tenant_access_token"]
    msg = obj.get("msg") or "unexpected response"
    raise RuntimeError(f"get token failed: {msg}")


def extract_document_id(url: str) -> Optional[Tuple[str, str]]:
    """从飞书文档 URL 中提取 document_id"""
    match = re.search(r'/docx/([a-zA-Z0-9]{27})', url)
    if match:
        return match.group(1), "docx"
    return None


def extract_wiki_token(url: str) -> Optional[Tuple[str, str]]:
    """从飞书 Wiki URL 中提取 wiki token"""
    match = re.search(r'/wiki/([a-zA-Z0-9]+)', url)
    if match:
        return match.group(1), "wiki"
    return None


class FeishuWikiClient:
    """飞书 Wiki 客户端 - 用于解析 Wiki URL 获取文档 ID"""

    def __init__(self, access_token: str, api_base: str = "https://open.feishu.cn"):
        self.access_token = access_token
        self.api_base = api_base
        self.headers = {"Authorization": f"Bearer {access_token}"}

    def get_wiki_spaces(self) -> List[Dict[str, Any]]:
        """获取用户有权限访问的所有 Wiki 空间"""
        url = f"{self.api_base}/open-apis/wiki/v2/spaces"
        result = request_json("GET", url, headers=self.headers)
        if result.get("code") != 0:
            raise RuntimeError(f"获取 Wiki 空间失败: {result.get('msg')}")
        return result.get("data", {}).get("items", [])

    def get_node_children(self, space_id: str, node_token: str, page_size: int = 100) -> List[Dict[str, Any]]:
        """
        获取 Wiki 节点的子节点（支持文件夹递归）

        Args:
            space_id: 空间 ID
            node_token: 节点 token
            page_size: 每页大小（默认 100）

        Returns:
            子节点列表
        """
        encoded_space_id = urllib.parse.quote(space_id, safe='')
        encoded_node_token = urllib.parse.quote(node_token, safe='')
        url = f"{self.api_base}/open-apis/wiki/v2/spaces/{encoded_space_id}/nodes/{encoded_node_token}/children?page_size={page_size}"
        result = request_json("GET", url, headers=self.headers)
        if result.get("code") != 0:
            raise RuntimeError(f"获取 Wiki 子节点失败: {result.get('msg')}")
        return result.get("data", {}).get("items", [])

    def get_node_info(self, space_id: str, node_token: str) -> Dict[str, Any]:
        """获取 Wiki 节点信息"""
        encoded_space_id = urllib.parse.quote(space_id, safe='')
        encoded_node_token = urllib.parse.quote(node_token, safe='')
        url = f"{self.api_base}/open-apis/wiki/v2/spaces/{encoded_space_id}/nodes/{encoded_node_token}"
        result = request_json("GET", url, headers=self.headers)
        if result.get("code") != 0:
            raise RuntimeError(f"获取 Wiki 节点信息失败: {result.get('msg')}")
        return result.get("data", {})

    def find_documents_in_folder(self, space_id: str, folder_token: str) -> List[Tuple[str, str]]:
        """
        在文件夹中递归查找所有文档

        Args:
            space_id: 空间 ID
            folder_token: 文件夹 token

        Returns:
            列表 [(node_title, obj_token), ...] - 仅返回 docx 和 sheet 类型的文档
        """
        documents = []

        def search_folder(token: str) -> List[Tuple[str, str]]:
            """递归搜索文件夹"""
            nonlocal documents

            # 获取子节点
            children = self.get_node_children(space_id, token)

            for child in children:
                node_type = child.get("node_type", "")
                obj_type = child.get("obj_type", "")
                child_token = child.get("obj_token", "")
                child_title = child.get("title", "未命名")

                # 只处理 docx 和 sheet 类型
                if obj_type == "docx":
                    print(f"  找到文档: {child_title}")
                    documents.append((child_title, child_token))
                elif obj_type == "sheet":
                    print(f"  找到表格: {child_title}")
                    documents.append((child_title, child_token))
                elif obj_type in ("folder", "my_library", "shared_library"):
                    print(f"  进入文件夹: {child_title}")
                    # 递归处理子文件夹
                    search_folder(child_token)
                # 忽略其他类型
                elif obj_type in ("mindnote", "doc", "file", "bitable", "slide"):
                    print(f"  跳过: {child_title} ({obj_type})")

        # 开始搜索
        search_folder(folder_token)

        return documents

    def wiki_url_to_document_id(self, wiki_token: str) -> Optional[str]:
        """
        将 Wiki URL 转换为 document_id

        支持文件夹：如果 Wiki 链接指向文件夹，递归查找其中的文档

        Args:
            wiki_token: Wiki URL 中的 token

        Returns:
            第一个找到的文档 ID，如果没有找到则返回 None
        """
        print(f"正在查找 Wiki 节点: {wiki_token}")

        spaces = self.get_wiki_spaces()
        print(f"找到 {len(spaces)} 个 Wiki 空间")

        for space in spaces:
            space_id = space.get("space_id")
            space_name = space.get("name", "")
            try:
                # 首先尝试获取节点信息
                node_info = self.get_node_info(space_id, wiki_token)

                node_data = node_info.get("node", {})
                obj_type = node_data.get("obj_type", "")
                obj_token = node_data.get("obj_token", "")
                node_type = node_data.get("node_type", "")
                title = node_data.get("title", "")

                print(f"\n在空间 '{space_name}' 找到节点:")
                print(f"  节点类型: {node_type}")
                print(f"  对象类型: {obj_type}")
                print(f"  标题: {title}")

                # 直接返回 docx 文档
                if obj_type == "docx" and obj_token:
                    print(f"  找到文档，文档 ID: {obj_token}")
                    return obj_token

                # 如果是文件夹，递归查找文档
                elif obj_type in ("folder", "my_library", "shared_library"):
                    print(f"  节点是文件夹，递归查找文档...")
                    documents = self.find_documents_in_folder(space_id, wiki_token)

                    if documents:
                        # 返回第一个找到的文档
                        doc_title, doc_token = documents[0]
                        print(f"  使用文件夹中的第一个文档: {doc_title}")
                        return doc_token
                    else:
                        print(f"  文件夹中未找到 docx 或 sheet 类型的文档")

            except Exception as e:
                print(f"  在空间 '{space_name}' 中查找失败: {e}")
                continue

        print(f"\n未能在任何空间中找到对应的文档或文件夹")
        return None


class FeishuDocumentClient:
    """飞书文档客户端 - 用于读取文档内容并下载图片"""

    # 块类型映射
    BLOCK_TYPE_MAP = {
        1: "page",
        2: "text",
        3: "heading1",
        4: "heading2",
        5: "heading3",
        6: "heading4",
        7: "heading5",
        8: "heading6",
        9: "heading7",
        10: "heading8",
        11: "heading9",
        12: "bullet",
        13: "ordered",
        14: "code",
        15: "quote",
        17: "todo",
        19: "callout",
        22: "divider",
        23: "equation",  # 数学公式
        27: "image",
        28: "file",
        29: "video",
        30: "audio",
        31: "table",
        32: "table_cell",
    }

    # 语言代码映射
    LANGUAGE_MAP = {
        1: "ABAP", 2: "Ada", 3: "Apache", 4: "Apex", 5: "Assembly",
        6: "Bash", 7: "C#", 8: "C++", 9: "C", 10: "COBOL",
        11: "CSS", 12: "CoffeeScript", 13: "D", 14: "Dart",
        15: "Delphi", 16: "Django", 17: "Dockerfile",
        18: "Erlang", 19: "Fortran", 20: "FoxPro",
        21: "Go", 22: "Groovy", 23: "HTML",
        24: "HTMLBars", 25: "HTTP", 26: "Haskell",
        27: "JSON", 28: "Java", 29: "JavaScript",
        30: "Julia", 31: "Kotlin", 32: "LateX",
        33: "Lisp", 34: "Logo", 35: "Lua",
        36: "MATLAB", 37: "Makefile", 38: "Markdown",
        39: "Nginx", 40: "Objective-C",
        41: "OpenEdgeABL", 42: "PHP", 43: "Perl",
        44: "PostScript", 45: "Power Shell",
        46: "Prolog", 47: "ProtoBuf", 48: "Python",
        49: "R", 50: "RPG", 51: "Ruby", 52: "Rust",
        53: "SAS", 54: "SCSS", 55: "SQL", 56: "Scala",
        57: "Scheme", 58: "Scratch", 59: "Shell",
        60: "Swift", 61: "Thrift", 62: "TypeScript",
        63: "VBScript", 64: "Visual Basic", 65: "XML",
        66: "YAML", 67: "CMake", 68: "Diff",
        69: "Gherkin", 70: "GraphQL", 71: "OpenGL Shading Language",
        72: "Properties", 73: "Solidity", 74: "TOML",
        75: "PlainText"
    }

    def __init__(self, access_token: str, api_base: str = "https://open.feishu.cn",
                 image_dir: Optional[Path] = None, download_images: bool = False):
        """
        初始化客户端

        Args:
            access_token: 访问令牌
            api_base: API 基础地址
            image_dir: 图片保存目录（如提供）
            download_images: 是否下载图片（默认：否）
        """
        self.access_token = access_token
        self.api_base = api_base
        self.headers = {"Authorization": f"Bearer {access_token}"}
        self.image_dir = image_dir
        self.download_images = download_images
        self.image_counter = 0
        self.image_mappings = {}

    def get_document_info(self, document_id: str) -> Dict[str, Any]:
        """获取文档基本信息"""
        url = f"{self.api_base}/open-apis/docx/v1/documents/{document_id}"
        result = request_json("GET", url, headers=self.headers)
        if result.get("code") != 0:
            raise RuntimeError(f"获取文档信息失败: {result.get('msg')}")
        return result.get("data", {}).get("document", {})

    def get_document_blocks(self, document_id: str, page_size: int = 500) -> List[Dict[str, Any]]:
        """获取文档所有块（支持分页）"""
        all_blocks = []
        page_token = None

        while True:
            url = f"{self.api_base}/open-apis/docx/v1/documents/{document_id}/blocks"
            params = {"page_size": page_size, "document_revision_id": -1}
            if page_token:
                params["page_token"] = page_token

            query_string = urllib.parse.urlencode(params)
            full_url = f"{url}?{query_string}"

            result = request_json("GET", full_url, headers=self.headers)
            if result.get("code") != 0:
                raise RuntimeError(f"获取文档块失败: {result.get('msg')}")

            data = result.get("data", {})
            items = data.get("items", [])
            all_blocks.extend(items)

            page_token = data.get("page_token")
            if not page_token:
                break

        return all_blocks

    def download_image(self, file_token: str, index: int) -> Optional[str]:
        """
        下载图片并保存到本地

        Args:
            file_token: 图片 token
            index: 图片序号

        Returns:
            本地相对路径（如 images/image_1.png），如果下载失败则返回 None
        """
        if not self.download_images or not self.image_dir:
            return None

        # 尝试多种 API 方式下载图片
        endpoints = [
            f"{self.api_base}/open-apis/drive/v1/files/{file_token}/download",
            f"{self.api_base}/open-apis/drive/v1/medias/{file_token}/download/",
        ]

        for endpoint in endpoints:
            try:
                req = urllib.request.Request(endpoint, headers=self.headers)
                with urllib.request.urlopen(req, timeout=30) as resp:
                    # 检测文件扩展名
                    content_type = resp.headers.get('Content-Type', '')
                    ext = '.png'
                    if 'jpeg' in content_type or 'jpg' in content_type:
                        ext = '.jpg'
                    elif 'gif' in content_type:
                        ext = '.gif'
                    elif 'webp' in content_type:
                        ext = '.webp'

                    filename = f"image_{index}{ext}"
                    filepath = self.image_dir / filename

                    # 保存文件
                    with open(filepath, 'wb') as f:
                        shutil.copyfileobj(resp, f)

                    self.image_counter += 1
                    return f"images/{filename}"
            except Exception as e:
                continue

        return None


def text_run_to_markdown(text_run: Dict[str, Any]) -> str:
    """将 text_run 转换为 Markdown 文本"""
    content = text_run.get("content", "")
    style = text_run.get("text_element_style", {})

    # 处理链接
    link = text_run.get("link", {})
    if link and link.get("url"):
        url = urllib.parse.unquote(link["url"])
        content = f"[{content}]({url})"

    # 处理行内代码
    if style.get("inline_code"):
        content = f"`{content}`"
    # 处理粗体/斜体/删除线/下划线：将 content 前后空格移到标记外面
    # 例如 "  text " + bold → "  **text** "
    if style.get("bold") or style.get("italic") or style.get("strikethrough") or style.get("underline"):
        stripped = content.strip()
        if stripped:
            leading = content[:len(content) - len(content.lstrip())]
            trailing = content[len(content.rstrip()):]
            content = stripped
            if style.get("bold"):
                content = f"**{content}**"
            if style.get("italic"):
                content = f"*{content}*"
            if style.get("strikethrough"):
                content = f"~~{content}~~"
            if style.get("underline"):
                content = f"<u>{content}</u>"
            content = leading + content + trailing

    return content


def elements_to_markdown(elements: List[Dict[str, Any]]) -> str:
    """将 elements 列表转换为 Markdown 文本"""
    result = []
    for elem in elements:
        if "text_run" in elem:
            result.append(text_run_to_markdown(elem["text_run"]))
        elif "mention_user" in elem:
            # 飞书 API 只返回 user_id（如 ou_xxx），在 Markdown 中无意义，忽略
            pass
        elif "mention_doc" in elem:
            doc = elem["mention_doc"]
            doc_title = doc.get("doc_title", "")
            doc_url = doc.get("url", "")
            if doc_url:
                # 有 URL 时生成 Markdown 链接
                label = doc_title if doc_title and doc_title != "document" else "链接"
                result.append(f"[{label}]({doc_url})")
            elif doc_title and doc_title != "document":
                # 无 URL 但有有意义的标题，直接输出标题
                result.append(doc_title)
            # 否则忽略（title 为空或 "document" 且无 URL）
    return "".join(result)


def block_to_markdown(block: Dict[str, Any], client: FeishuDocumentClient,
                     block_map: Dict[str, str] = None, indent_level: int = 0, skip_auto_number: bool = False) -> str:
    """
    将单个块转换为 Markdown

    Args:
        block: 文档块
        client: 文档客户端（用于图片下载）
        block_map: 块ID到块的映射（用于处理嵌套列表）
        indent_level: 缩进层级（用于嵌套列表）
        skip_auto_number: 跳过自动编号（当文本已带编号时）

    Returns:
        Markdown 文本
    """
    block_type = block.get("block_type", 0)
    indent = "  " * indent_level  # 每级缩进2个空格

    # 分割线
    if block_type == 22:
        return "---\n"

    # 标题 1-9
    if 3 <= block_type <= 11:
        level = block_type - 2
        key = f"heading{level}"
        heading_data = block.get(key, {})
        elements = heading_data.get("elements", [])
        text = elements_to_markdown(elements)
        prefix = "#" * level
        return f"{prefix} {text}\n"

    # 文本段落
    if block_type == 2:
        text_data = block.get("text", {})
        elements = text_data.get("elements", [])
        text = elements_to_markdown(elements)
        return f"{text}\n"

    # 无序列表
    if block_type == 12:
        bullet_data = block.get("bullet", {})
        elements = bullet_data.get("elements", [])
        text = elements_to_markdown(elements)
        return f"- {text}\n"

    # 有序列表
    if block_type == 13:
        ordered_data = block.get("ordered", {})
        elements = ordered_data.get("elements", [])
        text = elements_to_markdown(elements)

        # 检查文本是否已自带阿拉伯数字编号
        arabic_number_pattern = r'^\d+\.'
        has_existing_number = re.match(arabic_number_pattern, text.strip())

        # 如果文本已带编号或被标记为跳过自动编号，则直接返回原始文本
        if skip_auto_number or has_existing_number:
            sequence = ordered_data.get("sequence", "auto")
            number = "1." if sequence == "auto" else f"{sequence}."
            # 只保留原始的编号文本，不添加额外编号
            return f"{text}\n"
        else:
            sequence = ordered_data.get("sequence", "auto")
            number = "1." if sequence == "auto" else f"{sequence}."
            return f"{number} {text}\n"

    # 代码块
    if block_type == 14:
        code_data = block.get("code", {})
        elements = code_data.get("elements", [])
        text = elements_to_markdown(elements)
        language = code_data.get("language", 1)
        lang_name = FeishuDocumentClient.LANGUAGE_MAP.get(language, "")
        return f"```{lang_name}\n{text}\n```\n"

    # 引用
    if block_type == 15:
        quote_data = block.get("quote", {})
        elements = quote_data.get("elements", [])
        text = elements_to_markdown(elements)
        if not text.strip():
            return ""
        return f"> {text}\n"

    # 待办事项
    if block_type == 17:
        todo_data = block.get("todo", {})
        elements = todo_data.get("elements", [])
        text = elements_to_markdown(elements)
        done = todo_data.get("done", False)
        checkbox = "- [x]" if done else "- [ ]"
        return f"{checkbox} {text}\n"

    # 高亮块/Callout
    if block_type == 19:
        callout_data = block.get("callout", {})
        elements = callout_data.get("elements", [])
        text = elements_to_markdown(elements)
        bg_color = callout_data.get("background_color", "")
        emoji = callout_data.get("emoji", "")
        emoji_text = f"{emoji} " if emoji else ""
        return f"> {emoji_text}{text}\n"

    # 数学公式（新增）
    if block_type == 23:
        equation_data = block.get("equation", {})
        elements = equation_data.get("elements", [])
        text = elements_to_markdown(elements)
        # 使用 LaTeX 格式渲染公式
        return f"$${text}$$\n"

    # 图片（增强：支持本地下载）
    if block_type == 27:
        image_data = block.get("image", {})
        file_token = image_data.get("token", "")
        elements = image_data.get("elements", [])
        alt_text = elements_to_markdown(elements) if elements else "image"

        if file_token:
            client.image_counter += 1
            idx = client.image_counter

            # 尝试下载图片到本地
            local_path = client.download_image(file_token, idx)

            if local_path:
                # 使用本地路径
                return f"![{alt_text}]({local_path})\n"
            else:
                # 下载失败，使用原始 URL（带注释）
                return f"![{alt_text}](https://www.feishu.cn/space/api/box/stream/download/asyn/?token={file_token})\n<!-- 图片下载失败，保留原始 URL -->\n"
        return f"![{alt_text}](placeholder.png)\n"

    # 表格
    if block_type == 31:
        # 表格块本身不生成内容
        return ""

    # 表格单元格
    if block_type == 32:
        cell_data = block.get("table_cell", {})
        elements = cell_data.get("elements", [])
        # 如果有子块，优先处理子块
        if block_map and block.get("children"):
            children_ids = block.get("children", [])
            child_texts = []
            for child_id in children_ids:
                if child_id in block_map:
                    child_block = block_map[child_id]
                    # 递归处理子块（通常是文本块）
                    child_text = block_to_markdown(child_block, client, block_map)
                    child_texts.append(child_text)
            return "".join(child_texts)
        # 否则使用 elements
        text = elements_to_markdown(elements)
        return text

    # 不支持的块类型
    return ""


def blocks_to_markdown(blocks: List[Dict[str, Any]], client: FeishuDocumentClient, enable_heading_numbering: bool = False) -> str:
    """将所有块转换为 Markdown 文档"""
    # 构建块 ID 到块的映射
    block_map = {block["block_id"]: block for block in blocks}

    # 查找根块（parent_id 为空或等于自身的块）
    root_blocks = []
    for block in blocks:
        parent_id = block.get("parent_id", "")
        if not parent_id or parent_id == block.get("block_id"):
            root_blocks.append(block)

    # 按索引排序（如果有 index 字段）
    root_blocks.sort(key=lambda b: b.get("index", 0))

    # 构建有序的文档块列表（广度优先遍历）
    ordered_blocks = []
    for root in root_blocks:
        ordered_blocks.append(root)
        children = root.get("children", [])
        ordered_blocks.extend(
            [block_map[cid] for cid in children if cid in block_map]
        )

    # 处理表格 - 需要特殊处理
    return process_blocks_with_tables(ordered_blocks, block_map, client, enable_heading_numbering)


def detect_heading4_as_ordered(blocks: List[Dict[str, Any]]) -> tuple:
    """
    识别应该转换为有序列表的连续heading4块及其子块

    规则：连续的、同级、相同parent_id的heading4块，通常是有序列表的视觉呈现
    例如："需求说明"、"改造前"、"改造策略/方案"、"改造后"、"验收标准"

    Returns:
        (ordered_heading_ids, ordered_child_ids)
        - ordered_heading_ids: 应该作为有序列表处理的heading4块的block_id集合
        - ordered_child_ids: 这些heading4的所有子块（嵌套的heading5、ordered等）
    """
    # 按parent_id分组
    by_parent = {}
    for block in blocks:
        if block.get("block_type") == 6:  # heading4
            parent_id = block.get("parent_id", "")
            if parent_id not in by_parent:
                by_parent[parent_id] = []
            by_parent[parent_id].append(block)

    ordered_heading_ids = set()
    ordered_child_ids = set()

    # 对于每个parent下的heading4，检测连续序列
    for parent_id, heading_blocks in by_parent.items():
        if len(heading_blocks) < 2:
            continue  # 单个heading4不算序列

        # 检测连续的heading4序列
        # 按索引排序
        heading_blocks.sort(key=lambda b: b.get("index", 0))

        i = 0
        while i < len(heading_blocks):
            j = i + 1
            # 找连续的heading4序列（相同parent_id，连续索引）
            while j < len(heading_blocks):
                current = heading_blocks[j]
                prev = heading_blocks[j-1]

                # 检查是否连续：index差1或接近
                curr_index = current.get("index", 0)
                prev_index = prev.get("index", 0)
                index_gap = curr_index - prev_index

                # 如果index差距小于10（容忍飞书编号的连续性），认为是序列
                if index_gap <= 10:
                    j += 1
                else:
                    break

            # 如果找到至少2个连续的heading4，标记为有序列表
            if j - i >= 2:
                for k in range(i, j):
                    heading4_id = heading_blocks[k]["block_id"]
                    ordered_heading_ids.add(heading4_id)
                    # 同时标记这个heading4的所有children为有序列表子块
                    children_ids = heading_blocks[k].get("children", [])
                    ordered_child_ids.update(children_ids)
                i = j
            else:
                i = j

    return ordered_heading_ids, ordered_child_ids


def compute_block_depths(blocks: List[Dict[str, Any]], block_map: Dict[str, str]) -> Dict[str, int]:
    """
    计算每个块的嵌套深度（针对列表项）

    深度定义为：该块上方有多少个列表项类型的祖先块
    根块深度为 0，列表子项深度为 1，子项的子项深度为 2，以此类推
    """
    depth_map = {}

    def get_depth(block_id: str) -> int:
        """递归计算块的深度"""
        if block_id in depth_map:
            return depth_map[block_id]

        block = block_map.get(block_id)
        if not block:
            depth_map[block_id] = 0
            return 0

        parent_id = block.get("parent_id", "")
        if not parent_id or parent_id == block_id:
            # 根块
            depth_map[block_id] = 0
            return 0

        parent_depth = get_depth(parent_id)
        parent = block_map.get(parent_id)

        # 如果父块也是列表项类型，则深度 +1，否则保持父块深度
        parent_type = parent.get("block_type", 0) if parent else 0
        # 有序列表（type=13）也应该被视为列表父级，用于子块的缩进判断
        is_parent_list = parent_type in (12, 13, 17, 1)  # bullet, ordered, todo

        current_depth = parent_depth + 1 if is_parent_list else parent_depth
        depth_map[block_id] = current_depth
        return current_depth

    for block in blocks:
        block_id = block.get("block_id", "")
        get_depth(block_id)

    return depth_map


def process_blocks_with_tables(blocks: List[Dict[str, Any]], block_map: Dict[str, str],
                              client: FeishuDocumentClient, enable_heading_numbering: bool = False) -> str:
    """处理包含表格的块列表"""
    markdown_lines = []
    prev_block_type = 0  # 用于段落分隔
    heading_counter_by_parent = {}  # key: parent_id, value: [H1-H9 计数器]

    # 有序列表计数器：按父级分别计数
    ordered_list_counter = 0
    prev_parent_id = ""

    # heading4作为有序列表的计数器
    heading4_ordered_counter = 0

    # 有序列表子块的计数器（用于嵌套的有序列表项）
    ordered_child_counter = 0

    # 预计算每个块的嵌套深度
    block_depths = compute_block_depths(blocks, block_map)

    # 识别应该转换为有序列表的连续heading4块
    # 规则：连续的、同级、相同parent_id的heading4块，通常是有序列表的视觉呈现
    # 例如："需求说明"、"改造前"、"改造策略/方案"、"改造后"、"验收标准"
    ordered_heading_ids, ordered_child_ids = detect_heading4_as_ordered(blocks)

    # 用于检测新上下文（新的三级标题或未标记的heading4）
    # 当遇到新上下文时，重置有序列表计数器
    current_heading3_parent_id = None  # 当前正在处理的H3标题的parent_id

    for i, block in enumerate(blocks):
        block_type = block.get("block_type", 0)

        # 处理标题 (3-11 对应 H1-H9)
        if 3 <= block_type <= 11:
            level = block_type - 2  # 3->1 (H1), 4->2 (H2), etc.
            parent_id = block.get("parent_id", "")
            block_id = block.get("block_id", "")

            # 检查是否heading4应该渲染为有序列表
            if block_type == 6 and block_id in ordered_heading_ids:
                # 检测新上下文：在遇到新的H3标题时重置计数器
                # 简单方法：查找当前块之前的所有H3，如果找到任意一个就重置
                need_reset = any(blocks[idx].get("block_type", 0) == 5 for idx in range(i - 1))

                # 如果需要重置，重置两个计数器
                if need_reset:
                    heading4_ordered_counter = 0
                    ordered_child_counter = 0

                # 渲染为有序列表项
                key = "heading4"
                heading_data = block.get(key, {})
                elements = heading_data.get("elements", [])
                text = elements_to_markdown(elements)
                # 不同类型之间增加空行
                if prev_block_type != 0 and prev_block_type != 6:
                    markdown_lines.append("\n")

                markdown_lines.append(f"{heading4_ordered_counter}. {text}\n")
                prev_block_type = block_type

                # 处理这个heading4的子块作为有序列表
                children_ids = block.get("children", [])
                for child_id in children_ids:
                    if child_id in block_map and child_id in ordered_child_ids:
                        child_block = block_map[child_id]
                        child_type = child_block.get("block_type", 0)

                        # 根据子类型渲染
                        if child_type == 7:  # heading5
                            heading5_data = child_block.get("heading5", {})
                            elements = heading5_data.get("elements", [])
                            child_text = elements_to_markdown(elements)
                            ordered_child_counter += 1
                            markdown_lines.append(f"  {ordered_child_counter}. {child_text}\n")
                        elif child_type == 13:  # 有序列表
                            ordered_data = child_block.get("ordered", {})
                            elements = ordered_data.get("elements", [])
                            child_text = elements_to_markdown(elements)
                            ordered_child_counter += 1
                            markdown_lines.append(f"  {ordered_child_counter}. {child_text}\n")

                continue

            # 正常的标题处理
            # 获取或初始化当前父级的计数器
            if parent_id not in heading_counter_by_parent:
                heading_counter_by_parent[parent_id] = [0] * 9
            current_counters = heading_counter_by_parent[parent_id]

            key = f"heading{level}"
            heading_data = block.get(key, {})
            elements = heading_data.get("elements", [])
            text = elements_to_markdown(elements)

            # 生成编号（仅当启用时）
            if enable_heading_numbering:
                # 检测标题文本是否已带序号（中文或阿拉伯数字）
                chinese_pattern = r'^[一二三四五六七八九十百千万]+[、.]'
                arabic_pattern = r'^\d+(\.\d+)*\.'
                has_existing = (
                    re.match(chinese_pattern, text.strip()) or
                    re.match(arabic_pattern, text.strip())
                )
                # 没有编号时才添加
                if not has_existing:
                    # 更新当前父级的计数器
                    current_counters[level - 1] += 1
                    # 重置更深层级
                    for l in range(level, 9):
                        current_counters[l] = 0

                    # 生成层级编号
                    parts = [str(current_counters[l]) for l in range(level) if current_counters[l] > 0]
                    if parts:
                        text = ".".join(parts) + ". " + text

            prefix = "#" * level
            # 标题前确保有空行
            if markdown_lines and markdown_lines[-1] != "\n":
                markdown_lines.append("\n")
            markdown_lines.append(f"{prefix} {text}\n")
            prev_block_type = block_type
            continue

        # 处理表格
        if block_type == 31:
            table_data = block.get("table", {})
            property_data = table_data.get("property", {})
            row_size = property_data.get("row_size", 0)
            column_size = property_data.get("column_size", 0)

            if row_size > 0 and column_size > 0:
                # 获取所有单元格
                children_ids = block.get("children", [])
                cell_blocks = [block_map[cid] for cid in children_ids if cid in block_map]

                # 将单元格组织成表格
                # 飞书表格单元格按行优先顺序排列
                table_rows = []
                for r in range(row_size):
                    row_cells = []
                    for c in range(column_size):
                        idx = r * column_size + c
                        if idx < len(cell_blocks):
                            cell_text = block_to_markdown(cell_blocks[idx], client, block_map=block_map).strip()
                            row_cells.append(cell_text)
                        else:
                            row_cells.append("")
                    table_rows.append(row_cells)

                # 生成 Markdown 表格
                if table_rows:
                    # 表头
                    markdown_lines.append("| " + " | ".join(table_rows[0]) + " |\n")
                    # 分隔线
                    markdown_lines.append("|" + "|".join(["---"] * column_size) + "|\n")
                    # 数据行
                    for row in table_rows[1:]:
                        markdown_lines.append("| " + " | ".join(row) + " |\n")
                    markdown_lines.append("\n")
            prev_block_type = block_type
            continue

        # 处理有序列表：检测并保留原有编号，或添加自动编号
        if block_type == 13:
            # 检查是否是heading4的子块（有序列表的一部分）
            block_id = block.get("block_id", "")
            if block_id in ordered_child_ids:
                ordered_data = block.get("ordered", {})
                elements = ordered_data.get("elements", [])
                text = elements_to_markdown(elements)
                ordered_child_counter += 1
                # 缩进两个空格表示子级
                depth = block_depths.get(block_id, 0)
                indent = "  " * (depth + 1)  # 额外加一个缩进
                # 不同类型之间增加空行
                if prev_block_type != 0 and prev_block_type != 13:
                    markdown_lines.append("\n")
                markdown_lines.append(f"{indent}{ordered_child_counter}. {text}\n")
                prev_block_type = block_type
                continue

            # 正常的有序列表处理
            ordered_data = block.get("ordered", {})
            elements = ordered_data.get("elements", [])
            text = elements_to_markdown(elements)

            block_id = block.get("block_id", "")
            depth = block_depths.get(block_id, 0)

            # 获取飞书原始的 sequence 值
            sequence = ordered_data.get("sequence", "auto")

            # 检测父级变化，按父级分别计数
            parent_id = block.get("parent_id", "")
            if parent_id != prev_parent_id:
                prev_parent_id = parent_id
                ordered_list_counter = 0  # 父级变化，重置计数器

            # 判断编号方式（优先级：sequence > 检测文本编号）
            if sequence != "auto":
                # 飞书已指定编号，直接使用原始文本
                final_text = text
            else:
                # 检查文本是否已带阿拉伯数字编号（如 "1. xxx"）
                has_prefix = re.match(r'^\d+\.', text.strip())
                final_text = text if has_prefix else f"{ordered_list_counter + 1}. {text}"
                ordered_list_counter += 1 if not has_prefix else 0

            # 缩进
            indent = "  " * depth if depth > 0 else ""

            # 不同类型之间增加空行
            if prev_block_type != 0 and prev_block_type != 13:
                markdown_lines.append("\n")

            markdown_lines.append(f"{indent}{final_text}\n")
            prev_block_type = block_type
            continue

        # 处理无序列表：使用深度缩进
        if block_type == 12:
            bullet_data = block.get("bullet", {})
            elements = bullet_data.get("elements", [])
            text = elements_to_markdown(elements)

            # 调试：输出无序列表项信息
            block_id = block.get("block_id", "")
            if "入库质量" in text or "语义检索" in text or "精准可信" in text:
                print(f"[DEBUG BULLET] block_id={block_id[:15]}..., text='{text[:20]}', parent={block.get('parent_id', '')[:15]}...")

            block_id = block.get("block_id", "")
            depth = block_depths.get(block_id, 0)
            # 只有 depth > 0 时才需要缩进
            indent = "  " * depth if depth > 0 else ""

            # 不同类型之间增加空行
            if prev_block_type != 0 and prev_block_type != 12:
                markdown_lines.append("\n")

            markdown_lines.append(f"{indent}- {text}\n")
            prev_block_type = block_type
            continue

        # 处理待办事项：使用深度缩进
        if block_type == 17:
            todo_data = block.get("todo", {})
            elements = todo_data.get("elements", [])
            text = elements_to_markdown(elements)
            done = todo_data.get("done", False)
            checkbox = "- [x]" if done else "- [ ]"

            block_id = block.get("block_id", "")
            depth = block_depths.get(block_id, 0)
            indent = "  " * depth  # 每级缩进2个空格

            # 不同类型之间增加空行
            if prev_block_type != 0 and prev_block_type != 17:
                markdown_lines.append("\n")

            markdown_lines.append(f"{indent}{checkbox} {text}\n")
            prev_block_type = block_type
            continue

        # 处理普通块
        # 不同类型的 Block 之间增加空行分隔
        # 计算块类型类别：1=标题，2=文本，3=列表，4=表格，5=其他
        def get_block_category(bt):
            if 3 <= bt <= 11:  # H1-H9
                return 1
            elif bt == 2:  # text
                return 2
            elif bt in [12, 13, 17]:  # bullet, ordered, todo
                return 3
            elif bt == 31:  # table
                return 4
            else:
                return 5

        current_category = get_block_category(block_type)
        prev_category = get_block_category(prev_block_type)

        # 不同类型之间增加空行（相同类型但连续的文本块之间也增加空行）
        if prev_category != 0:
            markdown_lines.append("\n")

        md_text = block_to_markdown(block, client)
        if md_text:
            markdown_lines.append(md_text)
        prev_block_type = block_type

    return "".join(markdown_lines)


def main():
    parser = argparse.ArgumentParser(description="飞书文档 → Markdown (文件夹支持版)")
    parser.add_argument("--url", required=True, help="飞书文档 URL（支持 docx 和 wiki 格式）")
    parser.add_argument("--output", "-o", help="输出文件路径（默认使用文档标题）")
    parser.add_argument("--config", "-c", default="config.json", help="配置文件路径")
    parser.add_argument("--token", help="访问令牌（可选）")
    parser.add_argument("--use-raw", action="store_true", help="使用 raw_content API（纯文本模式，不保留格式）")
    parser.add_argument("--api-base", default="https://open.feishu.cn", help="API 基础地址")
    parser.add_argument("--download-images", action="store_true", help="下载图片到本地（默认：不下载）")
    parser.add_argument("--enable-heading-numbering", action="store_true", help="启用标题编号（默认：不启用）")
    parser.add_argument("--image-dir", "-i", help="图片保存目录（默认：输出目录/images）")
    parser.add_argument("--output-folder", help="输出文件夹路径（默认：文档标题作为文件夹）")

    args = parser.parse_args()

    # 加载配置
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, args.config)
    if not os.path.exists(config_path):
        # 尝试上级目录
        config_path = os.path.join(os.path.dirname(script_dir), args.config)
        if not os.path.exists(config_path):
            print(f"错误: 找不到配置文件 {args.config}")
            sys.exit(1)

    try:
        cfg = load_json(config_path)
    except Exception as e:
        print(f"错误: 读取配置文件失败: {e}")
        sys.exit(1)

    # 获取访问令牌（优先使用 user_access_token）
    if args.token:
        access_token = args.token
        print("使用命令行传入的 token")
    else:
        # 优先使用 user_access_token
        user_token = cfg.get("user_access_token", "").strip()
        if user_token:
            access_token = user_token
            print("使用配置文件中的 user_access_token")
        else:
            # 回退到 tenant_access_token
            app_id = cfg.get("app_id", "").strip()
            app_secret = cfg.get("app_secret", "").strip()
            if not app_id or not app_secret:
                print("错误: 请在配置文件中填写 user_access_token 或 app_id/app_secret")
                sys.exit(1)

            try:
                access_token = get_tenant_access_token(app_id, app_secret, args.api_base)
                print("使用应用身份获取 token (tenant_access_token)")
            except Exception as e:
                print(f"错误: 获取 token 失败: {e}")
                sys.exit(1)

    # 提取文档 ID 或 Wiki Token
    document_id = None
    url_type = None

    # 首先尝试作为 docx URL 处理
    docx_result = extract_document_id(args.url)
    if docx_result:
        document_id, url_type = docx_result
        print(f"URL 类型: docx")
        print(f"文档 ID: {document_id}")
    else:
        # 尝试作为 wiki URL 处理
        wiki_result = extract_wiki_token(args.url)
        if wiki_result:
            wiki_token, url_type = wiki_result
            print(f"URL 类型: wiki")
            print(f"Wiki Token: {wiki_token}")

            # 首先尝试直接使用 Wiki token 作为文档 ID
            try:
                url = f"{args.api_base}/open-apis/docx/v1/documents/{wiki_token}"
                result = request_json("GET", url, headers={"Authorization": f"Bearer {access_token}"})
                if result.get("code") == 0:
                    document_id = wiki_token
                    print(f"直接使用 Wiki token 作为文档 ID: {document_id}")
                else:
                    # 如果直接访问失败，尝试使用 Wiki API
                    wiki_client = FeishuWikiClient(access_token, args.api_base)
                    document_id = wiki_client.wiki_url_to_document_id(wiki_token)
                    if not document_id:
                        print(f"\n错误: 无法从 Wiki 节点获取文档 ID")
                        sys.exit(1)
            except Exception as e:
                # 如果直接访问失败，尝试使用 Wiki API
                try:
                    wiki_client = FeishuWikiClient(access_token, args.api_base)
                    document_id = wiki_client.wiki_url_to_document_id(wiki_token)
                    if not document_id:
                        print(f"\n错误: 无法从 Wiki 节点获取文档 ID")
                        sys.exit(1)
                except Exception as e2:
                    print(f"\n错误: 获取 Wiki 文档失败: {e}")
                    sys.exit(1)
        else:
            print(f"错误: 无法从 URL 中提取文档 ID 或 Wiki Token: {args.url}")
            print("支持的 URL 格式:")
            print("  - https://www.feishu.cn/docx/doxcnXXXXXXXXXXXXXXX")
            print("  - https://xxx.feishu.cn/wiki/XXXXXXXXXXXXXX")
            sys.exit(1)

    # 创建文档客户端
    client = FeishuDocumentClient(access_token, args.api_base,
                                image_dir=Path(args.image_dir) if args.image_dir else None,
                                download_images=args.download_images)

    try:
        # 获取文档信息
        doc_info = client.get_document_info(document_id)
        doc_title = doc_info.get("title", "untitled")

        print(f"\n文档标题: {doc_title}")

        # 确定输出路径
        if args.output:
            # 使用指定的完整输出文件路径
            output_file = Path(args.output)
            base_dir = output_file.parent
        elif args.output_folder:
            # 使用指定的输出文件夹
            base_dir = Path(args.output_folder)
        else:
            # 使用文档标题作为文件夹
            import string
            safe_title = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in doc_title)
            if not safe_title:
                safe_title = "document"
            base_dir = Path(safe_title)

        # 创建图片目录
        if args.download_images:
            image_dir = client.image_dir if client.image_dir else base_dir / "images"
            image_dir.mkdir(parents=True, exist_ok=True)
            print(f"图片目录: {image_dir}")
        else:
            image_dir = None
            print("图片下载: 禁用")

        # 创建输出目录
        base_dir.mkdir(parents=True, exist_ok=True)

        # 获取文档内容
        if args.use_raw:
            # 使用纯文本 API
            print("使用纯文本模式...")
            client_raw = FeishuDocumentClient(access_token, args.api_base)
            url = f"{args.api_base}/open-apis/docx/v1/documents/{document_id}/raw_content?lang=0"
            result = request_json("GET", url, headers=client.headers)
            if result.get("code") != 0:
                raise RuntimeError(f"获取纯文本内容失败: {result.get('msg')}")
            content = result.get("data", {}).get("content", "")
            markdown_content = f"# {doc_title}\n\n{content}"
        else:
            # 使用块 API（保留格式）
            print("正在获取文档块...")
            blocks = client.get_document_blocks(document_id)
            print(f"获取到 {len(blocks)} 个块")

            print("正在转换为 Markdown...")
            markdown_content = f"# {doc_title}\n\n{blocks_to_markdown(blocks, client, args.enable_heading_numbering)}"

        # 确保文件只以一个换行符结尾
        markdown_content = markdown_content.rstrip('\n') + '\n'

        # 写入文件
        if not args.output:
            # 没有指定完整路径，使用默认文件名
            output_file = base_dir / f"{base_dir.name}.md"
        else:
            # 已经在上面设置了 output_file
            pass
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)

        print(f"\n✓ 转换完成！")
        print(f"输出文件: {output_file}")
        if args.download_images:
            print(f"已下载图片数: {client.image_counter}")

    except urllib.error.HTTPError as e:
        print(f"\nHTTP 错误: {e.code}")
        try:
            err = e.read().decode("utf-8")
            print(err)
        except Exception:
            pass
        sys.exit(1)
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
