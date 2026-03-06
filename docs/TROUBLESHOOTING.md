# 故障排查指南

本文档提供 md-to-feishu-doc 常见问题的排查方法。

## 目录

- [常见错误](#常见错误)
  - [1. 权限相关错误](#1-权限相关错误)
  - [2. Token 相关错误](#2-token-相关错误)
  - [3. 导入相关错误](#3-导入相关错误)
  - [4. 表格相关错误](#4-表格相关错误)
  - [5. 所有权转移错误](#5-所有权转移错误)
- [调试技巧](#调试技巧)
- [日志分析](#日志分析)
- [获取帮助](#获取帮助)

## 常见错误

### 1. 权限相关错误

#### 错误：缺少权限

**错误信息**：
```
错误: 缺少权限 (code: 99991663)
```

**原因**：
- 应用未开通所需权限
- 权限未发布生效

**解决步骤**：
1. 登录 [飞书开发者后台](https://open.feishu.cn/app)
2. 选择应用 → 权限管理
3. 搜索并开通以下权限：
   - `docx:document`
   - `auth:user.id:read`
   - `drive:drive:readonly`
   - `docs:permission.member:transfer`
4. 版本管理与发布 → 创建版本 → 申请发布
5. 等待审核通过后重新尝试

#### 错误：redirect_uri 不匹配

**错误信息**：
```
错误: redirect_uri 不匹配
```

**原因**：
回调 URL 未在安全设置中注册

**解决步骤**：
1. 开发者后台 → 应用 → 安全设置
2. 添加重定向 URL：`https://open.feishu.cn/api-explorer/loading`
3. 保存并重新尝试

### 2. Token 相关错误

#### 错误：Token 无效或过期

**错误信息**：
```
错误: Token 无效或过期 (code: 99991661)
```

**原因**：
- user_access_token 已过期（有效期约 2 小时）
- 使用了错误的 Token 类型

**解决步骤**：
1. 删除 `config.json` 中的 `user_access_token` 字段
2. 重新运行脚本，完成 OAuth 授权
3. 或使用 `--token` 参数动态传入有效的 Token

#### 错误：使用了错误的 Token 类型

**错误信息**：
```
错误: 所有权转移失败 - 无权限
```

**原因**：
所有权转移需要 `user_access_token`，但可能使用了 `tenant_access_token`

**解决步骤**：
1. 确保使用用户身份授权（不要使用 `--use-app-identity`）
2. 完成 OAuth 授权获取 `user_access_token`

### 3. 导入相关错误

#### 错误：文件上传失败

**错误信息**：
```
错误: 文件上传失败
```

**可能原因**：
- 文件过大（限制 20MB）
- 文件格式不支持
- 网络问题

**解决步骤**：
1. 检查文件大小，确保不超过 20MB
2. 确保文件扩展名为 `.md` 或 `.markdown`
3. 检查网络连接
4. 查看详细错误信息

#### 错误：导入任务失败

**错误信息**：
```
导入任务失败: xxx (status: xxx)
```

**状态码含义**：
| 状态码 | 说明 | 解决方法 |
|--------|------|----------|
| 100 | 文档已加密 | 移除文档加密 |
| 108 | 处理超时 | 稍后重试 |
| 110 | 无权限 | 检查权限配置 |
| 112 | 格式不支持 | 检查文件格式 |
| 115 | 文件过大 | 压缩或拆分文件 |
| 129 | 文件损坏 | 修复文件内容 |

### 4. 表格相关错误

#### 错误：表格内容为空

**现象**：
导入成功但表格单元格为空

**原因**：
直接创建 API 对表格支持有限

**解决方法**：
使用 `import_task` 方式（上传文件），飞书会自动处理表格格式：

```bash
python md_to_feishu_doc.py \
  --source-type file \
  --file-path ./with-tables.md \
  --title "表格文档"
```

#### 错误：表格格式不正确

**现象**：
表格显示异常

**解决方法**：
1. 确保 Markdown 表格格式正确：
   ```markdown
   | 列1 | 列2 | 列3 |
   |-----|-----|-----|
   | 内容1 | 内容2 | 内容3 |
   ```
2. 使用 `--debug` 参数查看解析结果
3. 复杂表格建议使用 import_task 方式

### 5. 所有权转移错误

#### 错误：转移失败 - 无法获取用户信息

**错误信息**：
```
获取用户信息失败: xxx
```

**原因**：
- Token 无效或过期
- 缺少 `auth:user.id:read` 权限

**解决步骤**：
1. 重新获取 Token
2. 检查权限配置

#### 错误：转移失败 - 无权限转移

**错误信息**：
```
转移所有权失败: 无权限
```

**原因**：
- 缺少 `docs:permission.member:transfer` 权限
- 使用了 `tenant_access_token`

**解决步骤**：
1. 确保使用 `user_access_token`
2. 开通 `docs:permission.member:transfer` 权限
3. 创建版本并发布

## 调试技巧

### 1. 使用调试模式

```bash
python md_to_feishu_doc.py \
  --source-type file \
  --file-path ./test.md \
  --title "调试测试" \
  --debug
```

调试模式会输出：
- 解析后的文档结构
- API 请求详情
- 错误堆栈

### 2. 检查 Token 有效性

```python
import requests

token = "your_token"
url = "https://open.feishu.cn/open-apis/authen/v1/user_info"
headers = {"Authorization": f"Bearer {token}"}

response = requests.get(url, headers=headers)
print(response.json())
```

### 3. 验证权限配置

在飞书开发者后台检查：
- 权限管理 → 查看已开通权限
- 版本管理 → 确认最新版本已发布

### 4. 检查文件编码

确保 Markdown 文件使用 UTF-8 编码：
```bash
file -i your_file.md
# 应显示: text/plain; charset=utf-8
```

## 日志分析

### 启用详细日志

```bash
PYTHONPATH=. python -u md_to_feishu_doc.py ... 2>&1 | tee debug.log
```

### 常见日志信息

| 日志 | 说明 |
|------|------|
| `使用已保存的用户 token` | Token 有效，跳过授权 |
| `需要飞书用户授权` | 需要完成 OAuth 流程 |
| `文档已创建` | 文档创建成功 |
| `内容已写入完成` | 内容写入成功 |
| `所有权转移成功` | 所有权转移成功 |

## 获取帮助

如果以上方法无法解决问题：

1. 收集以下信息：
   - 完整的错误信息
   - 使用的命令和参数
   - `--debug` 模式的输出
   - 飞书应用配置截图

2. 提交 Issue：
   - 描述问题
   - 附上收集的信息
   - 说明已尝试的解决方法