#!/usr/bin/env python3
"""
Feishu Ownership Transfer Module
飞书文档所有权转移模块 - 独立、可复用

支持两种使用场景：
1. 导入时转移所有权（集成工作流）
2. 导入后转移所有权（独立操作）
"""

import json
import urllib.request
import urllib.error
import urllib.parse
from typing import Dict, Any, Optional


class FeishuOwnershipTransfer:
    """飞书文档所有权转移客户端"""

    def __init__(self, access_token: str, api_base: str = "https://open.feishu.cn"):
        """
        初始化客户端

        Args:
            access_token: 用户访问令牌（必须是 user_access_token）
            api_base: API 基础地址
        """
        self.access_token = access_token
        self.api_base = api_base
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=utf-8"
        }

    def _request_json(
        self,
        method: str,
        url: str,
        data_obj: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """发送 HTTP 请求并返回 JSON 响应"""
        data = None
        if data_obj is not None:
            data = json.dumps(data_obj).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=data,
            headers=self.headers,
            method=method
        )

        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body)

    def get_current_user_info(self) -> Dict[str, Any]:
        """
        获取当前用户信息

        使用 user_access_token 调用 /authen/v1/user_info 获取用户详情

        Returns:
            用户信息字典 {
                'user_id': str,
                'open_id': str,
                'name': str,
                'tenant_key': str,
                'avatar_url': str
            }

        Raises:
            RuntimeError: 获取用户信息失败
        """
        url = f"{self.api_base}/open-apis/authen/v1/user_info"

        result = self._request_json("GET", url)

        if result.get("code") != 0:
            msg = result.get("msg", "unknown error")
            raise RuntimeError(f"获取用户信息失败: {msg}")

        data = result.get("data", {})

        user_info = {
            "user_id": data.get("user_id", ""),
            "open_id": data.get("open_id", ""),
            "union_id": data.get("union_id", ""),
            "name": data.get("name", ""),
            "tenant_key": data.get("tenant_key", ""),
            "avatar_url": data.get("avatar_url", "")
        }

        print(f"[OwnershipTransfer] 当前用户: {user_info['name']} (open_id: {user_info['open_id']})")
        return user_info

    def transfer_ownership(
        self,
        token: str,
        doc_type: str = "docx",
        member_type: str = "openid",
        member_id: str = None,
        need_notification: bool = True,
        remove_old_owner: bool = False,
        stay_put: bool = False,
        old_owner_perm: str = "full_access"
    ) -> Dict[str, Any]:
        """
        转移文档所有权

        Args:
            token: 云文档的 token
            doc_type: 云文档类型 (doc/docx/sheet/file/wiki/bitable/mindnote/minutes/slides/folder)
            member_type: 新所有者 ID 类型 (email/openid/userid)
            member_id: 新所有者的 ID
            need_notification: 是否通知新所有者（默认 True）
            remove_old_owner: 是否移除原所有者权限（默认 False）
            stay_put: 文档是否留在原位置（默认 False）
            old_owner_perm: 原所有者保留的权限（默认 full_access）
                - view: 可阅读
                - edit: 可编辑
                - full_access: 可管理

        Returns:
            转移结果 {
                'success': bool,
                'message': str
            }

        Raises:
            RuntimeError: 转移失败
        """
        if not member_id:
            raise RuntimeError("缺少新所有者 ID (member_id)")

        # 构建请求 URL
        url = (
            f"{self.api_base}/open-apis/drive/v1/permissions/{urllib.parse.quote(token)}/members/transfer_owner"
            f"?type={doc_type}"
            f"&need_notification={'true' if need_notification else 'false'}"
            f"&remove_old_owner={'true' if remove_old_owner else 'false'}"
            f"&stay_put={'true' if stay_put else 'false'}"
            f"&old_owner_perm={old_owner_perm}"
        )

        # 构建请求体
        payload = {
            "member_type": member_type,
            "member_id": member_id
        }

        print(f"[OwnershipTransfer] 正在转移文档所有权...")
        print(f"  文档类型: {doc_type}")
        print(f"  新所有者: {member_type}:{member_id}")
        print(f"  通知新所有者: {'是' if need_notification else '否'}")
        print(f"  原所有者权限: {old_owner_perm if not remove_old_owner else '移除'}")

        result = self._request_json("POST", url, data_obj=payload)

        if result.get("code") != 0:
            code = result.get("code", -1)
            msg = result.get("msg", "unknown error")
            raise RuntimeError(f"转移所有权失败 (code: {code}): {msg}")

        print(f"[OwnershipTransfer] ✓ 所有权转移成功!")
        return {
            "success": True,
            "message": "所有权转移成功"
        }

    def transfer_to_current_user(
        self,
        token: str,
        doc_type: str = "docx",
        need_notification: bool = True,
        remove_old_owner: bool = False,
        stay_put: bool = False,
        old_owner_perm: str = "full_access"
    ) -> Dict[str, Any]:
        """
        将文档所有权转移给当前用户（便捷方法）

        自动获取当前用户信息并转移所有权

        Args:
            token: 云文档的 token
            doc_type: 云文档类型
            need_notification: 是否通知新所有者
            remove_old_owner: 是否移除原所有者权限
            stay_put: 文档是否留在原位置
            old_owner_perm: 原所有者保留的权限

        Returns:
            转移结果
        """
        # 获取当前用户信息
        user_info = self.get_current_user_info()
        open_id = user_info.get("open_id")

        if not open_id:
            raise RuntimeError("无法获取当前用户的 open_id")

        # 转移所有权
        return self.transfer_ownership(
            token=token,
            doc_type=doc_type,
            member_type="openid",
            member_id=open_id,
            need_notification=need_notification,
            remove_old_owner=remove_old_owner,
            stay_put=stay_put,
            old_owner_perm=old_owner_perm
        )


class TransferSession:
    """
    会话级别的所有权转移偏好管理

    实现用户只需选择一次，整个会话期间记住选择
    """
    _should_transfer: Optional[bool] = None
    _asked: bool = False

    @classmethod
    def reset(cls):
        """重置会话状态"""
        cls._should_transfer = None
        cls._asked = False

    @classmethod
    def get_preference(cls) -> Optional[bool]:
        """
        获取当前会话的转移偏好

        Returns:
            True: 应该转移
            False: 不应该转移
            None: 尚未询问
        """
        return cls._should_transfer

    @classmethod
    def set_preference(cls, should_transfer: bool):
        """设置转移偏好"""
        cls._should_transfer = should_transfer
        cls._asked = True

    @classmethod
    def has_been_asked(cls) -> bool:
        """是否已经询问过"""
        return cls._asked

    @classmethod
    def ask_user_for_transfer(cls) -> bool:
        """
        交互式询问用户是否转移所有权

        Returns:
            True: 用户选择转移
            False: 用户选择不转移
        """
        if cls._asked:
            return cls._should_transfer

        print("\n" + "=" * 50)
        print("  文档所有权转移")
        print("=" * 50)
        print("导入成功后，是否将文档所有权转移给当前用户？")
        print("")
        print("说明：")
        print("  - 转移后，当前用户将成为文档的所有者")
        print("  - 原所有者将保留完整管理权限")
        print("  - 当前用户将收到通知")
        print("")

        while True:
            choice = input("请输入 y/n，或直接回车跳过 (默认: n): ").strip().lower()

            if not choice or choice == 'n':
                cls.set_preference(False)
                print("[OwnershipTransfer] 选择：不转移所有权")
                return False
            elif choice == 'y':
                cls.set_preference(True)
                print("[OwnershipTransfer] 选择：转移所有权给当前用户")
                return True
            else:
                print("无效输入，请输入 y 或 n")


# 便捷函数
def transfer_ownership_to_current_user(
    access_token: str,
    document_token: str,
    doc_type: str = "docx",
    api_base: str = "https://open.feishu.cn",
    need_notification: bool = True,
    remove_old_owner: bool = False,
    old_owner_perm: str = "full_access"
) -> Dict[str, Any]:
    """
    将文档所有权转移给当前用户（便捷函数）

    Args:
        access_token: 用户访问令牌
        document_token: 文档 token
        doc_type: 文档类型
        api_base: API 基础地址
        need_notification: 是否通知新所有者
        remove_old_owner: 是否移除原所有者权限
        old_owner_perm: 原所有者保留的权限

    Returns:
        转移结果
    """
    client = FeishuOwnershipTransfer(access_token, api_base)
    return client.transfer_to_current_user(
        token=document_token,
        doc_type=doc_type,
        need_notification=need_notification,
        remove_old_owner=remove_old_owner,
        old_owner_perm=old_owner_perm
    )


# 命令行入口
if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="飞书文档所有权转移")
    parser.add_argument("--token", required=True, help="文档 token")
    parser.add_argument("--type", default="docx", help="文档类型 (doc/docx/sheet/file/wiki/bitable)")
    parser.add_argument("--config", default="config.json", help="配置文件路径")
    parser.add_argument("--api-base", default="https://open.feishu.cn", help="API 基础地址")
    parser.add_argument("--no-notification", action="store_true", help="不通知新所有者")
    parser.add_argument("--remove-old-owner", action="store_true", help="移除原所有者权限")

    args = parser.parse_args()

    # 加载配置
    try:
        with open(args.config, "r", encoding="utf-8") as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"错误: 配置文件 {args.config} 不存在")
        sys.exit(1)

    access_token = config.get("user_access_token", "")
    if not access_token:
        print("错误: 配置文件中缺少 user_access_token")
        sys.exit(1)

    # 执行转移
    try:
        client = FeishuOwnershipTransfer(access_token, args.api_base)
        result = client.transfer_to_current_user(
            token=args.token,
            doc_type=args.type,
            need_notification=not args.no_notification,
            remove_old_owner=args.remove_old_owner
        )
        print(json.dumps(result, ensure_ascii=False))
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)