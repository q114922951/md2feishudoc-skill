#!/usr/bin/env python3
"""
Feishu Import Task API Client
使用 import_task API 将本地文件导入为飞书云文档
"""

import os
import json
import time
import requests
from pathlib import Path
from typing import Optional, Dict, Any


class FeishuImportClient:
    """飞书导入任务客户端"""

    def __init__(self, access_token: str, api_base: str = "https://open.feishu.cn"):
        """
        初始化客户端

        Args:
            access_token: 访问令牌（user_access_token 或 tenant_access_token）
            api_base: API 基础地址
        """
        self.access_token = access_token
        self.api_base = api_base
        self.headers = {
            "Authorization": f"Bearer {access_token}",
        }

    def upload_file(
        self,
        file_path: str,
        obj_type: str = "docx",
        file_extension: Optional[str] = None
    ) -> str:
        """
        上传文件到飞书云空间

        Args:
            file_path: 本地文件路径
            obj_type: 目标文档类型 (docx/sheet/bitable)
            file_extension: 文件扩展名（默认从文件路径获取）

        Returns:
            file_token: 上传成功后返回的文件 token

        Raises:
            FileNotFoundError: 文件不存在
            RuntimeError: 上传失败
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        # 如果未指定扩展名，从文件路径获取
        if file_extension is None:
            file_extension = path.suffix.lstrip('.')

        file_size = path.stat().st_size

        # 构建 extra 参数
        extra = json.dumps({
            "obj_type": obj_type,
            "file_extension": file_extension
        })

        url = f"{self.api_base}/open-apis/drive/v1/medias/upload_all"

        files = {
            'file': (path.name, open(file_path, 'rb'), 'application/octet-stream')
        }

        data = {
            'file_name': path.name,
            'parent_type': 'ccm_import_open',
            'size': str(file_size),
            'extra': extra
        }

        try:
            response = requests.post(url, headers=self.headers, files=files, data=data)
            result = response.json()

            if result.get('code') != 0:
                raise RuntimeError(
                    f"文件上传失败: {result.get('msg')} (code: {result.get('code')})"
                )

            file_token = result['data']['file_token']
            print(f"[ImportClient] 文件上传成功，token: {file_token}")
            return file_token

        finally:
            files['file'][1].close()

    def create_import_task(
        self,
        file_token: str,
        file_extension: str,
        obj_type: str = "docx",
        file_name: Optional[str] = None,
        folder_token: Optional[str] = None
    ) -> str:
        """
        创建导入任务

        Args:
            file_token: 上传文件后返回的 token
            file_extension: 文件扩展名
            obj_type: 目标文档类型 (docx/sheet/bitable)
            file_name: 导入后的文档名称（可选）
            folder_token: 目标文件夹 token（可选，空为根目录）

        Returns:
            ticket: 导入任务 ID

        Raises:
            RuntimeError: 创建任务失败
        """
        url = f"{self.api_base}/open-apis/drive/v1/import_tasks"

        self.headers["Content-Type"] = "application/json; charset=utf-8"

        payload = {
            "file_extension": file_extension,
            "file_token": file_token,
            "type": obj_type,
            "point": {
                "mount_type": 1,
                "mount_key": folder_token or ""
            }
        }

        if file_name:
            payload["file_name"] = file_name

        response = requests.post(url, headers=self.headers, json=payload)
        result = response.json()

        if result.get('code') != 0:
            raise RuntimeError(
                f"创建导入任务失败: {result.get('msg')} (code: {result.get('code')})"
            )

        ticket = result['data']['ticket']
        print(f"[ImportClient] 导入任务已创建，ticket: {ticket}")
        return ticket

    def poll_import_result(
        self,
        ticket: str,
        max_retries: int = 30,
        interval: int = 2
    ) -> Dict[str, Any]:
        """
        轮询查询导入任务结果

        Args:
            ticket: 导入任务 ID
            max_retries: 最大重试次数
            interval: 轮询间隔（秒）

        Returns:
            包含导入结果的字典 {
                'success': bool,
                'token': str,
                'url': str,
                'job_status': int,
                'job_error_msg': str,
                'extra': list
            }

        Raises:
            RuntimeError: 导入失败或超时
        """
        url = f"{self.api_base}/open-apis/drive/v1/import_tasks/{ticket}"

        for i in range(max_retries):
            response = requests.get(url, headers=self.headers)
            result = response.json()

            if result.get('code') != 0:
                raise RuntimeError(
                    f"查询导入结果失败: {result.get('msg')} (code: {result.get('code')})"
                )

            task_result = result['data']['result']
            job_status = task_result.get('job_status')
            job_error_msg = task_result.get('job_error_msg', '')

            # job_status: 0=成功, 1=初始化, 2=处理中, 其他=失败
            if job_status == 0:
                print(f"[ImportClient] 导入成功！")
                return {
                    'success': True,
                    'token': task_result.get('token'),
                    'url': task_result.get('url'),
                    'job_status': job_status,
                    'job_error_msg': job_error_msg,
                    'extra': task_result.get('extra', [])
                }
            elif job_status in (1, 2):
                # 继续等待
                print(f"[ImportClient] 等待导入完成... ({i+1}/{max_retries})")
                time.sleep(interval)
            else:
                # 导入失败
                raise RuntimeError(
                    f"导入任务失败: {job_error_msg} (status: {job_status})"
                )

        raise RuntimeError(f"导入任务超时，已尝试 {max_retries} 次")

    def import_file(
        self,
        file_path: str,
        file_name: Optional[str] = None,
        folder_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        完整导入流程：上传文件 → 创建任务 → 等待结果

        Args:
            file_path: 本地文件路径
            file_name: 导入后的文档名称（可选）
            folder_token: 目标文件夹 token（可选）

        Returns:
            导入结果字典
        """
        path = Path(file_path)
        file_extension = path.suffix.lstrip('.')

        print(f"[ImportClient] 开始导入文件: {file_path}")

        # 步骤1: 上传文件
        file_token = self.upload_file(file_path, "docx", file_extension)

        # 步骤2: 创建导入任务
        ticket = self.create_import_task(
            file_token=file_token,
            file_extension=file_extension,
            obj_type="docx",
            file_name=file_name,
            folder_token=folder_token
        )

        # 步骤3: 轮询查询结果
        result = self.poll_import_result(ticket)

        print(f"[ImportClient] 文档链接: {result['url']}")

        return result


# 测试代码
if __name__ == "__main__":
    # 配置（实际使用时从 config.json 读取）
    ACCESS_TOKEN = "your_access_token_here"

    client = FeishuImportClient(ACCESS_TOKEN)

    # 示例：导入文件
    # result = client.import_file(
    #     file_path="./test.md",
    #     file_name="测试文档"
    # )
    # print(f"导入成功: {result['url']}")
