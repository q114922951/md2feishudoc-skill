#!/usr/bin/env python3
"""
Feishu Document Validator
文档校验器 - 验证飞书文档是否成功创建
"""

import requests
from typing import Dict, Any, List, Optional


class FeishuDocValidator:
    """飞书文档校验器"""

    # 作业状态映射
    JOB_STATUS = {
        0: "导入成功",
        1: "初始化",
        2: "处理中",
        3: "内部错误",
        100: "导入文档已加密",
        108: "处理超时",
        110: "无权限",
        112: "格式不支持",
        113: "office格式不支持",
        115: "导入文件过大",
        116: "无权限导入至文件夹",
        117: "目录已删除",
        118: "导入文件和任务指定后缀不匹配",
        119: "目录不存在",
        120: "导入文件和任务指定文件类型不匹配",
        121: "导入文件已过期",
        122: "创建副本中禁止导出",
        129: "文件格式损坏",
        5000: "内部错误",
        7000: "docx block 数量超过系统上限",
        7001: "docx block 层级超过系统上线",
        7002: "docx block 大小超过系统上限"
    }

    def __init__(self, access_token: str, api_base: str = "https://open.feishu.cn"):
        """
        初始化校验器

        Args:
            access_token: 访问令牌
            api_base: API 基础地址
        """
        self.access_token = access_token
        self.api_base = api_base
        self.headers = {
            "Authorization": f"Bearer {access_token}",
        }

    def fetch_document_blocks(self, document_id: str, page_size: int = 100) -> List[Dict[str, Any]]:
        """
        获取文档的所有块

        Args:
            document_id: 文档 token 或 ID
            page_size: 每页大小

        Returns:
            文档块列表
        """
        url = f"{self.api_base}/open-apis/docx/v1/documents/{document_id}/blocks"
        blocks = []
        page_token = ""

        while True:
            params = {
                "page_size": page_size,
            }
            if page_token:
                params["page_token"] = page_token

            response = requests.get(url, headers=self.headers, params=params)
            result = response.json()

            if result.get('code') != 0:
                raise RuntimeError(
                    f"获取文档块失败: {result.get('msg')} (code: {result.get('code')})"
                )

            data = result.get('data', {})
            items = data.get('items', [])
            blocks.extend(items)

            # 检查是否有更多页
            page_token = data.get('page_token', '')
            if not page_token:
                break

        return blocks

    def _test_existence(self, blocks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        TC-001: 文档存在性

        检查 API 返回状态码 200 且 blocks 非空
        """
        passed = len(blocks) > 0
        return {
            'test_id': 'TC-001',
            'name': '文档存在性',
            'passed': passed,
            'message': '✓ 文档已创建' if passed else '✗ 文档不存在或为空'
        }

    def _test_title_match(self, blocks: List[Dict[str, Any]], expected_title: str) -> Dict[str, Any]:
        """
        TC-002: 标题匹配

        检查第一个 heading 块的 text 是否等于预期标题
        """
        # 查找第一个标题块 (block_type 3-8 对应 H1-H6)
        first_heading = None
        heading_level = 0
        for block in blocks:
            bt = block.get('block_type')
            if bt and 3 <= bt <= 8:  # heading blocks
                first_heading = block
                heading_level = bt - 2
                break

        if not first_heading:
            return {
                'test_id': 'TC-002',
                'name': '标题匹配',
                'passed': False,
                'message': '✗ 未找到标题块'
            }

        # 获取标题内容
        heading_key = f'heading{heading_level}'
        elements = first_heading.get(heading_key, {}).get('elements', [])
        actual_title = ''
        for elem in elements:
            if 'text_run' in elem:
                actual_title += elem['text_run'].get('content', '')

        passed = actual_title.strip() == expected_title.strip()

        return {
            'test_id': 'TC-002',
            'name': '标题匹配',
            'passed': passed,
            'message': f'✓ 标题匹配: "{expected_title}"' if passed else f'✗ 标题不匹配 (预期: "{expected_title}", 实际: "{actual_title}")'
        }

    def _test_content_not_empty(self, blocks: List[Dict[str, Any]], min_chars: int = 10) -> Dict[str, Any]:
        """
        TC-003: 内容非空

        检查文档总字数 > min_chars 字符
        """
        total_chars = 0
        for block in blocks:
            block_type = block.get('block_type')
            if block_type == 2:  # paragraph
                elements = block.get('text', {}).get('elements', [])
                for elem in elements:
                    text_run = elem.get('text_run', {})
                    content = text_run.get('content', '')
                    total_chars += len(content)

        passed = total_chars >= min_chars
        return {
            'test_id': 'TC-003',
            'name': '内容非空',
            'passed': passed,
            'message': f'✓ 文档内容非空 (字数: {total_chars})' if passed else f'✗ 文档内容为空或过短 (字数: {total_chars})'
        }

    def _test_heading_structure(self, blocks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        TC-004: 标题层级验证

        检查是否包含至少一个 h1 标题
        """
        h1_count = 0
        h2_count = 0

        for block in blocks:
            bt = block.get('block_type')
            if bt == 3:  # H1
                h1_count += 1
            elif bt == 4:  # H2
                h2_count += 1

        passed = h1_count > 0
        return {
            'test_id': 'TC-004',
            'name': '标题层级验证',
            'passed': passed,
            'message': f'✓ 文档有标题结构 (H1: {h1_count}个, H2: {h2_count}个)' if passed else '✗ 文档缺少 H1 标题'
        }

    def _test_key_content(self, blocks: List[Dict[str, Any]], key_text: str) -> Dict[str, Any]:
        """
        TC-005: 关键词存在

        检查全文是否包含关键内容
        """
        all_text = ""
        for block in blocks:
            block_type = block.get('block_type')
            if block_type == 2:  # paragraph
                elements = block.get('paragraph', {}).get('elements', [])
                for elem in elements:
                    text_run = elem.get('text_run', {})
                    content = text_run.get('content', '')
                    all_text += content

        passed = key_text in all_text
        return {
            'test_id': 'TC-005',
            'name': '关键词存在',
            'passed': passed,
            'message': f'✓ 关键内容已导入' if passed else '✗ 关键内容未找到'
        }

    def _test_code_blocks(self, blocks: List[Dict[str, Any]], expected_count: int = 0) -> Dict[str, Any]:
        """
        TC-006: 代码块检测（可选）

        检查是否包含 code 类型块
        """
        code_count = 0
        for block in blocks:
            if block.get('block_type') == 12:  # code
                code_count += 1

        passed = code_count >= expected_count
        return {
            'test_id': 'TC-006',
            'name': '代码块检测',
            'passed': passed,
            'message': f'✓ 代码格式保留 (找到 {code_count} 个代码块)' if passed else f'✗ 代码块数量不足 (预期: {expected_count}, 实际: {code_count})'
        }

    def _test_paragraph_count(self, blocks: List[Dict[str, Any]], expected_count: Optional[int] = None) -> Dict[str, Any]:
        """
        TC-007: 段落数量

        检查 paragraph 类型块数量
        """
        paragraph_count = 0
        for block in blocks:
            if block.get('block_type') == 2:  # paragraph
                paragraph_count += 1

        if expected_count is not None:
            passed = paragraph_count >= expected_count
            msg = f'✓ 段落数量匹配 (预期: {expected_count}, 实际: {paragraph_count})' if passed else f'✗ 段落数量不足 (预期: {expected_count}, 实际: {paragraph_count})'
        else:
            passed = paragraph_count > 0
            msg = f'✓ 文档包含段落 (数量: {paragraph_count})' if passed else '✗ 文档无段落'

        return {
            'test_id': 'TC-007',
            'name': '段落数量',
            'passed': passed,
            'message': msg
        }

    def _test_table_content(self, blocks: List[Dict[str, Any]], access_token: str) -> Dict[str, Any]:
        """
        TC-008: 表格内容校验

        检查表格单元格是否有内容（不为空）
        """
        # 找所有表格块
        table_blocks = [b for b in blocks if b.get('block_type') == 31]

        if not table_blocks:
            return {
                'test_id': 'TC-008',
                'name': '表格内容校验',
                'passed': True,
                'message': '✓ 无表格需要校验'
            }

        total_cells = 0
        empty_cells = 0

        for table_block in table_blocks:
            cell_ids = table_block.get('children', [])
            total_cells += len(cell_ids)

            for cell_id in cell_ids:
                try:
                    # 使用 requests 库获取单元格
                    cell_url = f"{self.api_base}/open-apis/docx/v1/documents/{self._last_document_id}/blocks/{cell_id}"
                    response = requests.get(cell_url, headers=self.headers)
                    result = response.json()

                    if result.get('code') != 0:
                        empty_cells += 1
                        continue

                    child_ids = result.get('data', {}).get('block', {}).get('children', [])

                    if child_ids:
                        # 获取单元格内的段落
                        child_url = f"{self.api_base}/open-apis/docx/v1/documents/{self._last_document_id}/blocks/{child_ids[0]}"
                        response = requests.get(child_url, headers=self.headers)
                        child_result = response.json()

                        elements = child_result.get('data', {}).get('block', {}).get('text', {}).get('elements', [])
                        content = ''.join([e.get('text_run', {}).get('content', '') for e in elements if e.get('text_run')])

                        if not content.strip():
                            empty_cells += 1
                    else:
                        empty_cells += 1
                except Exception as e:
                    empty_cells += 1

        passed = empty_cells == 0
        return {
            'test_id': 'TC-008',
            'name': '表格内容校验',
            'passed': passed,
            'message': f'✓ 所有表格单元格均有内容 (共 {total_cells} 个单元格)' if passed else f'✗ 发现 {empty_cells}/{total_cells} 个空单元格'
        }

    def validate(
        self,
        document_id: str,
        expected_title: Optional[str] = None,
        key_text: Optional[str] = None,
        expected_paragraphs: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        执行快速校验

        Args:
            document_id: 文档 ID 或 token
            expected_title: 预期标题（可选）
            key_text: 关键文本（可选，用于验证内容）
            expected_paragraphs: 预期段落数（可选）

        Returns:
            校验结果字典 {
                'success': bool,
                'tests': List[Dict]
            }
        """
        print(f"[Validator] 开始校验文档: {document_id}")

        # 保存 document_id 供表格校验使用
        self._last_document_id = document_id

        # 获取文档内容
        blocks = self.fetch_document_blocks(document_id)

        # 执行测试用例
        tests = []

        # TC-001: 文档存在性
        tests.append(self._test_existence(blocks))

        # TC-002: 标题匹配（如果提供了预期标题）
        if expected_title:
            tests.append(self._test_title_match(blocks, expected_title))

        # TC-003: 内容非空
        tests.append(self._test_content_not_empty(blocks))

        # TC-004: 标题层级验证
        tests.append(self._test_heading_structure(blocks))

        # TC-005: 关键词存在（如果提供了关键文本）
        if key_text:
            tests.append(self._test_key_content(blocks, key_text))

        # TC-006: 代码块检测
        tests.append(self._test_code_blocks(blocks, expected_count=0))

        # TC-007: 段落数量
        tests.append(self._test_paragraph_count(blocks, expected_paragraphs))

        # TC-008: 表格内容校验（需要 access_token）
        if self.access_token:
            tests.append(self._test_table_content(blocks, self.access_token))

        # 汇总结果
        success = all(test['passed'] for test in tests)

        return {
            'success': success,
            'tests': tests
        }

    def print_validation_report(self, result: Dict[str, Any]):
        """
        打印校验报告

        Args:
            result: validate() 返回的结果
        """
        print("\n" + "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("校验报告:")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        for test in result['tests']:
            print(f"{test['test_id']}\t{test['name']:<20}\t{'✓ 通过' if test['passed'] else '✗ 失败'}")
            if not test['passed']:
                print(f"      {test['message']}")

        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        if result['success']:
            print("✓ 所有测试通过，文档导入成功！")
        else:
            print("✗ 部分测试失败，请检查文档内容")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")


# 测试代码
if __name__ == "__main__":
    # 配置（实际使用时从 config.json 读取）
    ACCESS_TOKEN = "your_access_token_here"

    validator = FeishuDocValidator(ACCESS_TOKEN)

    # 示例：校验文档
    # result = validator.validate(
    #     document_id="your_document_id",
    #     expected_title="测试文档"
    # )
    # validator.print_validation_report(result)
