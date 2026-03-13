#!/usr/bin/env python3
"""
Markdown → 飞书文档
支持表格（格式化文本）、列表（圆点）、粗体等格式
集成所有权转移功能
"""
import json
import os
import sys
import urllib.request
import urllib.error
import urllib.parse
import argparse
import re
import time
from typing import List, Dict, Any, Tuple

# 导入所有权转移模块
from feishu_ownership_transfer import FeishuOwnershipTransfer, TransferSession


def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data: Dict[str, Any]):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def request_json(method: str, url: str, headers: Dict[str, str] = None, data_obj: Dict[str, Any] = None) -> Dict[str, Any]:
    data = None
    req_headers = headers or {}
    if data_obj is not None:
        data = json.dumps(data_obj).encode("utf-8")
        req_headers = dict(req_headers)
        req_headers.setdefault("Content-Type", "application/json; charset=utf-8")
    req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
    with urllib.request.urlopen(req) as resp:
        body = resp.read().decode("utf-8")
        return json.loads(body)


# --------------- Token 管理 ---------------

def get_tenant_access_token(app_id: str, app_secret: str, api_base: str) -> str:
    """获取应用身份 token"""
    url = f"{api_base}/open-apis/auth/v3/tenant_access_token/internal"
    obj = request_json("POST", url, data_obj={"app_id": app_id, "app_secret": app_secret})
    if obj.get("code") == 0 and obj.get("tenant_access_token"):
        return obj["tenant_access_token"]
    msg = obj.get("msg") or "unexpected response"
    raise RuntimeError(f"get token failed: {msg}")


def generate_oauth_url(app_id: str, redirect_uri: str, scope: str = "docx:document auth:user.id:read drive:drive:readonly") -> str:
    """生成 OAuth 授权 URL"""
    state = f"feishu_{int(time.time())}"
    return (
        f"https://open.feishu.cn/open-apis/authen/v1/authorize"
        f"?app_id={app_id}"
        f"&redirect_uri={urllib.parse.quote(redirect_uri, safe='')}"
        f"&state={state}"
        f"&scope={urllib.parse.quote(scope)}"
    )


def exchange_code_for_token(app_id: str, app_secret: str, code: str, redirect_uri: str) -> Dict[str, Any]:
    """用 code 换取 user_access_token"""
    url = "https://open.feishu.cn/open-apis/authen/v2/oauth/token"
    payload = {
        "grant_type": "authorization_code",
        "client_id": app_id,
        "client_secret": app_secret,
        "code": code,
        "redirect_uri": redirect_uri,
    }
    return request_json("POST", url, data_obj=payload)


def load_or_obtain_user_token(cfg: Dict[str, Any], cfg_path: str, app_id: str, app_secret: str, redirect_uri: str) -> str:
    """
    加载或获取 user_access_token
    """
    token = cfg.get("user_access_token", "").strip()
    expires_at = cfg.get("token_expires_at", 0)
    now = int(time.time())

    if token and expires_at > now:
        print("使用已保存的用户 token")
        return token

    print("=" * 60)
    print("  需要飞书用户授权")
    print("=" * 60)
    print()
    print("请在浏览器中打开以下链接完成授权：")
    print()

    auth_url = generate_oauth_url(app_id, redirect_uri)
    print(auth_url)
    print()
    print("步骤：")
    print("1. 点击链接，在飞书中确认授权")
    print("2. 授权后，复制浏览器地址栏中的完整 URL")
    print("3. 将 URL 粘贴到下方")
    print()

    callback_url = input("请粘贴回调 URL: ").strip()

    if not callback_url:
        raise RuntimeError("未输入回调 URL，授权取消")

    parsed = urllib.parse.urlparse(callback_url)
    params = urllib.parse.parse_qs(parsed.query)
    code = params.get("code", [None])[0]

    if not code:
        raise RuntimeError("回调 URL 中未找到授权码 (code)")

    print("正在换取 token...")

    result = exchange_code_for_token(app_id, app_secret, code, redirect_uri)

    if result.get("code") != 0:
        msg = result.get("msg", "unknown error")
        raise RuntimeError(f"换取 token 失败: {msg}")

    access_token = result["access_token"]
    expires_in = result.get("expires_in", 7200)
    scope = result.get("scope", "")

    if "docx" not in scope:
        print(f"警告: token 缺少 docx 权限 (scope: {scope})")
        print("请确保应用已开通 docx:document 用户权限")

    cfg["user_access_token"] = access_token
    cfg["token_expires_at"] = int(time.time()) + expires_in - 60
    cfg["token_scope"] = scope
    save_json(cfg_path, cfg)

    print("授权成功，token 已保存")
    return access_token


# --------------- 文档操作 ---------------

def create_doc(token: str, api_base: str, title: str, folder_token: str = "") -> Tuple[str, str]:
    """创建文档"""
    url = f"{api_base}/open-apis/docx/v1/documents"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"title": title}
    if folder_token:
        payload["folder_token"] = folder_token

    obj = request_json("POST", url, headers=headers, data_obj=payload)
    if obj.get("code") != 0:
        msg = obj.get("msg") or "unexpected response"
        raise RuntimeError(f"create doc failed: {msg}")

    data = obj.get("data") or {}
    doc = data.get("document") or {}
    doc_id = doc.get("document_id") or data.get("document_id")
    if not doc_id:
        raise RuntimeError("missing document_id in response")

    doc_url = f"https://www.feishu.cn/docx/{doc_id}"
    return doc_id, doc_url


def parse_inline_text(text: str) -> List[Dict[str, Any]]:
    """解析行内文本，支持粗体**text**"""
    elements = []
    # 处理粗体 **text**
    parts = re.split(r'\*\*(.*?)\*\*', text)
    for i, part in enumerate(parts):
        if not part:
            continue
        if i % 2 == 1:  # 粗体部分
            elements.append({"text_run": {"content": part, "text_element_style": {"bold": True}}})
        else:  # 普通文本
            elements.append({"text_run": {"content": part}})
    return elements


def parse_table_to_json(table_lines: List[str]) -> Dict[str, Any]:
    """
    将 Markdown 表格解析为 JSON 结构
    返回: {"headers": [...], "rows": [[...], [...]]}
    """
    rows = []
    for line in table_lines:
        line = line.strip()
        # 跳过分隔符行（包含 --- 或 :-- 的行）
        if not line or re.search(r'^\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?$', line):
            continue
        # 移除首尾的 |
        line = line[1:] if line.startswith('|') else line
        line = line[:-1] if line.endswith('|') else line
        # 分割单元格
        cells = [cell.strip() for cell in line.split('|')]
        rows.append(cells)

    if not rows:
        return None

    return {
        "headers": rows[0] if rows else [],
        "rows": rows[1:] if len(rows) > 1 else []
    }


def create_table_cell(content: str, is_header: bool = False) -> Dict[str, Any]:
    """创建表格单元格内容（段落块）"""
    if not content:
        content = " "

    elements = parse_inline_text(content)

    if not elements:
        elements = [{"text_run": {"content": content, "text_element_style": {}}}]

    # 表头单元格加粗处理
    if is_header:
        for elem in elements:
            if "text_run" in elem:
                if "text_element_style" not in elem["text_run"]:
                    elem["text_run"]["text_element_style"] = {}
                elem["text_run"]["text_element_style"]["bold"] = True

    # 确保每个 text_run 都有 text_element_style 字段
    for elem in elements:
        if "text_run" in elem and "text_element_style" not in elem["text_run"]:
            elem["text_run"]["text_element_style"] = {}

    return {
        "block_type": 2,
        "text": {"elements": elements},
        "children": []
    }


class TableData:
    """表格数据容器，用于存储表格内容和单元格内容"""
    def __init__(self, row_count: int, col_count: int, cell_contents: List[Dict[str, Any]]):
        self.row_count = row_count
        self.col_count = col_count
        self.cell_contents = cell_contents  # 每个单元格的内容块


class ParsedBlock:
    """解析后的块，可能是普通块或表格"""
    def __init__(self, block: Dict[str, Any], is_table: bool = False, table_data: TableData = None):
        self.block = block
        self.is_table = is_table
        self.table_data = table_data  # 如果是表格，存储单元格内容


def create_table_structure(table_data: Dict[str, Any]) -> Tuple[Dict[str, Any], TableData]:
    """
    创建飞书表格结构（不含单元格内容）

    飞书 API 要求：
    1. 先创建表格结构（block_type: 31 + property）
    2. API 返回自动创建的单元格 IDs
    3. 再往每个单元格插入内容

    Returns:
        (table_block, TableData) - 表格块和单元格内容数据
    """
    headers = table_data.get("headers", [])
    rows = table_data.get("rows", [])

    if not headers:
        return None, None

    col_count = len(headers)
    row_count = 1 + len(rows)  # 表头 + 数据行

    # 收集单元格内容
    cell_contents = []

    # 表头行单元格
    for header in headers:
        cell_contents.append(create_table_cell(header, is_header=True))

    # 数据行单元格
    for row in rows:
        for i in range(col_count):
            cell_content = row[i] if i < len(row) else ""
            cell_contents.append(create_table_cell(cell_content, is_header=False))

    # 创建表格块（只含结构，不含 children）
    table_block = {
        "block_type": 31,
        "table": {
            "property": {
                "row_size": row_count,
                "column_size": col_count
            }
        }
    }

    table_info = TableData(row_count, col_count, cell_contents)

    return table_block, table_info


# 保留旧函数名以兼容
def create_table_blocks(table_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    创建飞书原生表格块 (block_type: 31)
    注意：此函数返回的表格块不含单元格内容
    """
    table_block, _ = create_table_structure(table_data)
    if not table_block:
        return []

    blocks = [table_block]

    # 表格后空行
    blocks.append({
        "block_type": 2,
        "text": {"elements": [{"text_run": {"content": ""}}]},
        "children": []
    })

    return blocks


def create_bullet_block(text: str) -> Dict[str, Any]:
    """创建无序列表项（使用飞书原生 bullet 块）"""
    # 移除开头的 - 或 * 和空格
    content = re.sub(r'^[\-\*]\s+', '', text)
    # block_type 12 = bullet (无序列表)，飞书会自动渲染圆点符号
    return {
        "block_type": 12,
        "bullet": {
            "elements": parse_inline_text(content)
        },
        "children": []
    }


def create_ordered_block(text: str, number: int) -> Dict[str, Any]:
    """创建有序列表项（使用飞书原生 ordered 块）"""
    # 移除开头的数字和空格 (如 "1. " 或 "2) ")
    content = re.sub(r'^\d+[\.\)]\s+', '', text)
    # block_type 13 = ordered (有序列表)，飞书会自动渲染序号
    return {
        "block_type": 13,
        "ordered": {
            "elements": parse_inline_text(content)
        },
        "children": []
    }


def parse_markdown_children(md: str) -> List[Dict[str, Any]]:
    """
    解析 Markdown 为飞书文档块（旧版本，保留兼容性）
    """
    parsed = parse_markdown_with_tables(md)
    # 将 ParsedBlock 转换为普通块（表格不含单元格内容）
    result = []
    for item in parsed:
        if item.is_table:
            result.append(item.block)
            # 表格后空行
            result.append({
                "block_type": 2,
                "text": {"elements": [{"text_run": {"content": ""}}]},
                "children": []
            })
        else:
            result.append(item.block)
    return result


def parse_markdown_with_tables(md: str) -> List[ParsedBlock]:
    """
    解析 Markdown 为 ParsedBlock 列表

    返回的列表中包含：
    - 普通块（段落、标题等）
    - 表格块（包含表格结构和单元格内容数据）

    用于正确处理飞书 API 的表格创建流程
    """
    lines = md.splitlines()
    parsed_blocks: List[ParsedBlock] = []
    code_buffer: List[str] = None
    table_buffer: List[str] = []

    heading_pattern = re.compile(r'^(#{1,6})\s+(.+)$')
    table_pattern = re.compile(r'^\|.*\|$')
    bullet_pattern = re.compile(r'^[\-\*]\s+(.+)$')
    ordered_pattern = re.compile(r'^(\d+)[\.\)]\s+(.+)$')

    def flush_table_buffer():
        """处理表格缓冲区"""
        if not table_buffer:
            return
        table_data = parse_table_to_json(table_buffer)
        if table_data:
            table_block, table_info = create_table_structure(table_data)
            if table_block:
                parsed_blocks.append(ParsedBlock(
                    block=table_block,
                    is_table=True,
                    table_data=table_info
                ))
        table_buffer.clear()

    i = 0
    while i < len(lines):
        raw = lines[i]
        line = raw.rstrip("\n")

        # 代码块处理
        if re.match(r"^```", line):
            flush_table_buffer()

            if code_buffer is None:
                code_buffer = []
            else:
                content = "\n".join(code_buffer)
                parsed_blocks.append(ParsedBlock({
                    "block_type": 2,
                    "text": {"elements": [{"text_run": {"content": content}}]},
                    "children": []
                }))
                code_buffer = None
            i += 1
            continue

        if code_buffer is not None:
            code_buffer.append(line)
            i += 1
            continue

        # 空行跳过
        if not line.strip():
            flush_table_buffer()
            i += 1
            continue

        # 表格检测
        if table_pattern.match(line):
            table_buffer.append(line)
            i += 1
            continue
        elif table_buffer:
            flush_table_buffer()

        # 无序列表检测
        bullet_match = bullet_pattern.match(line)
        if bullet_match:
            parsed_blocks.append(ParsedBlock(create_bullet_block(line)))
            i += 1
            continue

        # 有序列表检测
        ordered_match = ordered_pattern.match(line)
        if ordered_match:
            number = int(ordered_match.group(1))
            parsed_blocks.append(ParsedBlock(create_ordered_block(line, number)))
            i += 1
            continue

        # 标题检测
        heading_match = heading_pattern.match(line)
        if heading_match:
            level = len(heading_match.group(1))
            title = heading_match.group(2).strip()
            block_type = 2 + level
            parsed_blocks.append(ParsedBlock({
                "block_type": block_type,
                f"heading{level}": {"elements": [{"text_run": {"content": title}}]},
                "children": []
            }))
        else:
            # 普通文本
            parsed_blocks.append(ParsedBlock({
                "block_type": 2,
                "text": {"elements": parse_inline_text(line)},
                "children": []
            }))
        i += 1

    # 处理末尾的表格
    flush_table_buffer()

    return parsed_blocks


def insert_children(token: str, api_base: str, document_id: str, children: List[Dict[str, Any]], index: int = 0):
    """
    批量插入文档内容

    注意：飞书 API 限制每个 block 最多 50 个子元素，
    该函数会自动将 children 分批插入，每批最多 50 个。
    """
    headers = {"Authorization": f"Bearer {token}"}

    # 飞书 API 限制：每个 block 最多 50 个子元素
    MAX_CHILDREN_PER_REQUEST = 50

    # 分批插入
    obj = None
    for i in range(0, len(children), MAX_CHILDREN_PER_REQUEST):
        chunk = children[i:i + MAX_CHILDREN_PER_REQUEST]
        url = f"{api_base}/open-apis/docx/v1/documents/{urllib.parse.quote(document_id)}/blocks/{urllib.parse.quote(document_id)}/children?document_revision_id=-1"
        payload = {"index": index + i, "children": chunk}
        obj = request_json("POST", url, headers=headers, data_obj=payload)
        if obj.get("code") != 0:
            msg = obj.get("msg") or "unexpected response"
            raise RuntimeError(f"insert children failed (chunk {i//MAX_CHILDREN_PER_REQUEST + 1}): {msg}")

    return obj


def insert_table_with_content(
    token: str,
    api_base: str,
    document_id: str,
    table_block: Dict[str, Any],
    cell_contents: List[Dict[str, Any]],
    index: int = 0
) -> Dict[str, Any]:
    """
    插入表格并填充单元格内容

    飞书 API 要求分两步：
    1. 创建表格结构（飞书自动创建空单元格）
    2. 往每个单元格插入内容

    Args:
        token: 访问令牌
        api_base: API 基础地址
        document_id: 文档 ID
        table_block: 表格块（block_type: 31）
        cell_contents: 每个单元格的内容块列表
        index: 插入位置

    Returns:
        API 响应
    """
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"}

    # Step 1: 插入表格结构
    url = f"{api_base}/open-apis/docx/v1/documents/{urllib.parse.quote(document_id)}/blocks/{urllib.parse.quote(document_id)}/children?document_revision_id=-1"
    payload = {"index": index, "children": [table_block]}

    print(f"[DEBUG] 正在插入表格结构: {len(cell_contents)} 个单元格")
    print(f"[DEBUG] 表格结构: {json.dumps(table_block, ensure_ascii=False)}")

    result = request_json("POST", url, headers=headers, data_obj=payload)
    if result.get("code") != 0:
        print(f"[ERROR] 创建表格失败: code={result.get('code')}, msg={result.get('msg')}")
        print(f"[ERROR] 请求payload: {json.dumps(payload, ensure_ascii=False)}")
        raise RuntimeError(f"创建表格失败: {result.get('msg')}")

    # 获取返回的表格块和单元格 IDs
    created_children = result.get("data", {}).get("children", [])
    if not created_children:
        raise RuntimeError("未返回创建的表格块")

    table_block_result = created_children[0]
    cell_ids = table_block_result.get("children", [])

    if len(cell_ids) != len(cell_contents):
        print(f"警告: 单元格数量不匹配 (预期 {len(cell_contents)}, 实际 {len(cell_ids)})")

    # Step 2: 往每个单元格插入内容
    for i, cell_id in enumerate(cell_ids):
        if i >= len(cell_contents):
            break

        cell_url = f"{api_base}/open-apis/docx/v1/documents/{urllib.parse.quote(document_id)}/blocks/{cell_id}/children?document_revision_id=-1"
        cell_payload = {"index": 0, "children": [cell_contents[i]]}

        cell_result = request_json("POST", cell_url, headers=headers, data_obj=cell_payload)
        if cell_result.get("code") != 0:
            print(f"警告: 单元格 {i} 内容插入失败: {cell_result.get('msg')}")

        # 避免速率限制
        import time
        time.sleep(0.1)

    return result


# --------------- 所有权转移集成 ---------------

def handle_ownership_transfer(
    access_token: str,
    document_id: str,
    api_base: str,
    force_ask: bool = False
) -> Dict[str, Any]:
    """
    处理所有权转移逻辑

    Args:
        access_token: 用户访问令牌
        document_id: 文档 ID
        api_base: API 基础地址
        force_ask: 强制询问（忽略会话偏好）

    Returns:
        转移结果
    """
    # 获取会话偏好
    if not force_ask:
        preference = TransferSession.get_preference()
        if preference is False:
            print("[md-to-feishu-doc] 使用会话偏好：不转移所有权")
            return {"success": False, "message": "用户选择不转移"}
        elif preference is True:
            print("[md-to-feishu-doc] 使用会话偏好：转移所有权")
            try:
                client = FeishuOwnershipTransfer(access_token, api_base)
                return client.transfer_to_current_user(token=document_id)
            except Exception as e:
                return {"success": False, "message": str(e)}

    # 需要询问用户
    should_transfer = TransferSession.ask_user_for_transfer()

    if should_transfer:
        try:
            client = FeishuOwnershipTransfer(access_token, api_base)
            return client.transfer_to_current_user(token=document_id)
        except Exception as e:
            return {"success": False, "message": str(e)}

    return {"success": False, "message": "用户选择不转移"}


# --------------- 输入处理 ---------------

def load_markdown_from_source(args: argparse.Namespace) -> str:
    if args.source_type == "text":
        return args.source_text or ""
    if args.source_type == "file":
        if not args.file_path or not os.path.exists(args.file_path):
            raise RuntimeError("file_path missing or not exists")
        with open(args.file_path, "r", encoding="utf-8") as f:
            return f.read()
    if args.source_type == "url":
        if not args.url:
            raise RuntimeError("url missing")
        req = urllib.request.Request(args.url, method="GET")
        with urllib.request.urlopen(req) as resp:
            return resp.read().decode("utf-8")
    raise RuntimeError("invalid source_type")


# --------------- 主函数 ---------------

def main():
    parser = argparse.ArgumentParser(description="Markdown → 飞书文档（支持所有权转移）")
    parser.add_argument("--source-type", choices=["text", "file", "url"],
                       help="Markdown 来源类型（导入模式必需）")
    parser.add_argument("--source-text", help="当 source-type=text 时的 Markdown 内容")
    parser.add_argument("--file-path", help="当 source-type=file 时的文件路径")
    parser.add_argument("--url", help="当 source-type=url 时的 URL")
    parser.add_argument("--title", help="文档标题（导入模式必需）")
    parser.add_argument("--folder-token", help="目标文件夹 token（可选，默认创建到用户个人空间）")
    parser.add_argument("--use-app-identity", action="store_true",
                       help="使用应用身份创建（默认使用用户身份）")
    parser.add_argument("--share-chat-id", help="分享到群聊的 ID（可选）")
    parser.add_argument("--api-base", default="https://open.feishu.cn", help="API 基础地址")
    parser.add_argument("--debug", action="store_true", help="调试模式：打印解析结果和请求数据")

    # 所有权转移相关参数
    parser.add_argument("--skip-transfer-prompt", action="store_true",
                       help="跳过所有权转移询问（不转移）")
    parser.add_argument("--auto-transfer", action="store_true",
                       help="自动转移所有权给当前用户（不询问）")

    # 独立转移模式
    parser.add_argument("--transfer-ownership", action="store_true",
                       help="独立模式：仅转移已有文档的所有权")
    parser.add_argument("--document-token", help="要转移所有权的文档 token")

    # 动态 Token 参数（推荐使用，避免过期问题）
    parser.add_argument("--token", help="user_access_token（动态传入，优先级高于配置文件）")

    args = parser.parse_args()

    # 加载配置
    script_dir = os.path.dirname(os.path.abspath(__file__))
    skill_cfg_path = os.path.join(script_dir, "config.json")
    if not os.path.exists(skill_cfg_path):
        print("错误: 缺少技能配置文件 config.json")
        sys.exit(1)

    skill_cfg = load_json(skill_cfg_path)
    app_id = (skill_cfg.get("app_id") or "").strip()
    app_secret = (skill_cfg.get("app_secret") or "").strip()

    if not app_id or not app_secret:
        print("错误: 请在 config.json 中填写 app_id 和 app_secret")
        sys.exit(1)

    redirect_uri = skill_cfg.get("oauth_redirect_uri", "https://open.feishu.cn/api-explorer/loading")

    try:
        # 独立转移模式
        if args.transfer_ownership:
            if not args.document_token:
                print("错误: 独立转移模式需要 --document-token 参数")
                sys.exit(1)

            # 优先使用命令行传入的 token
            token = args.token or skill_cfg.get("user_access_token", "").strip()
            if not token:
                print("错误: 缺少 user_access_token，请通过 --token 参数传入或在配置文件中配置")
                sys.exit(1)

            result = handle_ownership_transfer(
                access_token=token,
                document_id=args.document_token,
                api_base=args.api_base,
                force_ask=False  # 独立模式默认使用会话偏好
            )
            print(json.dumps(result, ensure_ascii=False))
            return

        # 加载 Markdown
        md = load_markdown_from_source(args)

        # 获取 token
        if args.use_app_identity:
            token = get_tenant_access_token(app_id, app_secret, args.api_base)
            print("使用应用身份创建文档")
            print("注意: 应用身份创建的文档无法转移所有权给用户")
        else:
            # 优先使用命令行传入的 token
            if args.token:
                token = args.token
                print("使用命令行传入的 user_access_token")
            else:
                token = load_or_obtain_user_token(skill_cfg, skill_cfg_path, app_id, app_secret, redirect_uri)

        # 创建文档
        folder_token = args.folder_token or skill_cfg.get("folder_token", "")
        document_id, doc_url = create_doc(token, args.api_base, args.title, folder_token)
        print(f"文档已创建: {doc_url}")

        # 写入内容（需要特殊处理表格）
        parsed_blocks = parse_markdown_with_tables(md)

        if args.debug:
            print("\n=== 调试：解析后的文档结构 ===")
            print(f"总计 {len(parsed_blocks)} 个块")
            for i, pb in enumerate(parsed_blocks):
                if pb.is_table:
                    print(f"  [{i}] 表格块: {pb.table_data.row_count}行 x {pb.table_data.col_count}列, {len(pb.table_data.cell_contents)}个单元格")
                else:
                    print(f"  [{i}] 普通块: block_type={pb.block.get('block_type')}")
            print("=" * 60 + "\n")

        # 分批插入，每个表格单独处理
        current_index = 0
        batch_blocks = []
        total_blocks = 0

        for pb in parsed_blocks:
            if pb.is_table:
                # 先插入之前的普通块
                if batch_blocks:
                    insert_children(token, args.api_base, document_id, batch_blocks, index=current_index)
                    total_blocks += len(batch_blocks)
                    print(f"已写入 {len(batch_blocks)} 个普通块")
                    current_index += len(batch_blocks)
                    batch_blocks = []

                # 插入表格（含单元格内容）
                insert_table_with_content(
                    token, args.api_base, document_id,
                    pb.block, pb.table_data.cell_contents,
                    index=current_index
                )
                total_blocks += 1
                print(f"已写入表格: {pb.table_data.row_count}行 x {pb.table_data.col_count}列")
                current_index += 1

                # 表格后的空行
                insert_children(token, args.api_base, document_id, [{
                    "block_type": 2,
                    "text": {"elements": [{"text_run": {"content": ""}}]},
                    "children": []
                }], index=current_index)
                current_index += 1
            else:
                batch_blocks.append(pb.block)

        # 插入剩余的普通块
        if batch_blocks:
            insert_children(token, args.api_base, document_id, batch_blocks, index=current_index)
            total_blocks += len(batch_blocks)
            print(f"已写入 {len(batch_blocks)} 个普通块")

        print(f"内容已写入完成（共 {total_blocks} 个块）")

        # 处理所有权转移（仅用户身份）
        transfer_result = None
        if not args.use_app_identity:
            if args.auto_transfer:
                # 自动转移模式
                print("\n[md-to-feishu-doc] 自动转移所有权模式")
                TransferSession.set_preference(True)
                transfer_result = handle_ownership_transfer(
                    access_token=token,
                    document_id=document_id,
                    api_base=args.api_base,
                    force_ask=False
                )
            elif not args.skip_transfer_prompt:
                # 默认：询问用户
                transfer_result = handle_ownership_transfer(
                    access_token=token,
                    document_id=document_id,
                    api_base=args.api_base,
                    force_ask=TransferSession.get_preference() is None
                )

        # 分享到群聊
        if args.share_chat_id:
            from urllib.parse import quote
            share_cfg = skill_cfg.get("share", {})
            template = share_cfg.get("message_template", "文档已生成：{url}")
            message = template.format(url=doc_url)

            headers = {"Authorization": f"Bearer {token}"}
            url = f"{args.api_base}/open-apis/im/v1/messages?receive_id_type=chat_id"
            payload = {
                "receive_id": args.share_chat_id,
                "msg_type": "text",
                "content": json.dumps({"text": message}, ensure_ascii=False)
            }
            try:
                request_json("POST", url, headers=headers, data_obj=payload)
                print("已分享到群聊")
            except Exception as e:
                print(f"分享失败: {e}")

        # 输出结果
        result = {
            "document_id": document_id,
            "url": doc_url,
            "ownership_transfer": transfer_result
        }
        print(json.dumps(result, ensure_ascii=False))

    except urllib.error.HTTPError as e:
        print(f"HTTP 错误: {e.code}")
        try:
            err = e.read().decode("utf-8")
            print(err)
            # 尝试解析错误信息
            try:
                err_json = json.loads(err)
                if 'code' in err_json and 'msg' in err_json:
                    print(f"\n错误详情: code={err_json['code']}, msg={err_json['msg']}")
            except Exception:
                pass
        except Exception as ex:
            print(f"无法读取错误详情: {ex}")
        sys.exit(1)
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()