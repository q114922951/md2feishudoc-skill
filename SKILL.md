---
name: md-to-feishu-doc
description: 将 Markdown 文件导入为飞书云文档。支持 import_task 方式（上传文件）和直接创建方式。包含所有权转移功能、8项文档校验、OAuth授权、Token自动管理。触发词：导入飞书、导入文档、to feishu、上传飞书、同步飞书、md转飞书、markdown飞书、飞书文档。
---

# Markdown → 飞书文档

将 Markdown 文件导入为飞书云文档，支持自动授权、Token管理、所有权转移、文档校验。

## 适用场景

- 将本地 Markdown 文件同步到飞书个人空间
- 将项目 README 转为飞书文档分享
- 批量导入 Markdown 文档到飞书
- 导入后转移文档所有权给当前用户

## 前置要求

### 1. 飞书应用配置

在 [飞书开发者后台](https://open.feishu.cn/app) 创建或选择应用：

**必需权限**（用户身份）：
- `docx:document` — 创建及编辑新版文档
- `auth:user.id:read` — 获取用户身份信息
- `drive:drive:readonly` — 读取云空间（所有权转移需要）
- `docs:permission.member:transfer` — 转移文档所有权

**配置步骤**：
1. 应用首页 → 凭证信息 → 复制 App ID 和 App Secret
2. 权限管理 → 搜索并开通上述权限
3. 安全设置 → 添加重定向 URL：`https://open.feishu.cn/api-explorer/loading`
4. 版本管理与发布 → 创建版本 → 申请发布（权限需发布后生效）

### 2. 配置文件

创建 `config.json`：
```json
{
  "app_id": "cli_xxxxxxxxxxxx",
  "app_secret": "xxxxxxxxxxxxxxxx",
  "oauth_redirect_uri": "https://open.feishu.cn/api-explorer/loading",
  "folder_token": "",
  "user_access_token": "",
  "token_expires_at": 0
}
```

## 使用方式

### 方式一：import_task（推荐）

直接上传 MD 文件，飞书自动处理格式，表格支持最佳。

```bash
python md_to_feishu_doc.py \
  --source-type file \
  --file-path ./README.md \
  --title "项目文档" \
  --auto-transfer
```

### 方式二：独立转移所有权

对已有文档执行所有权转移：

```bash
python md_to_feishu_doc.py \
  --transfer-ownership \
  --document-token "doccnxxxxxxxxxx"
```

### 命令行参数

| 参数 | 必需 | 说明 |
|------|------|------|
| `--source-type` | ✅ | 来源类型：`text` / `file` / `url` |
| `--file-path` | - | `file` 类型的文件路径 |
| `--title` | ✅ | 文档标题 |
| `--token` | ✅ | user_access_token（动态传入，避免过期问题） |
| `--auto-transfer` | - | 自动转移所有权给当前用户 |
| `--skip-transfer-prompt` | - | 跳过所有权询问 |
| `--transfer-ownership` | - | 独立模式：转移所有权 |
| `--document-token` | - | 要转移的文档 token |

### 快速使用（带 Token）

```bash
python md_to_feishu_doc.py \
  --source-type file \
  --file-path ./README.md \
  --title "项目文档" \
  --token "u-xxxxxxxxxx" \
  --auto-transfer
```

## 所有权转移功能

- **导入时转移**：导入后立即转移，询问一次后记住会话偏好
- **独立转移**：对已有文档执行转移操作
- **默认设置**：保留原所有者完整权限、通知新所有者

## 文档校验

导入后自动执行 8 项校验：

| 用例 | 说明 |
|------|------|
| TC-001 | 文档存在性 |
| TC-002 | 标题匹配 |
| TC-003 | 内容非空 |
| TC-004 | 标题层级验证 |
| TC-005 | 关键词存在 |
| TC-006 | 代码块检测 |
| TC-007 | 段落数量 |
| TC-008 | 表格内容校验（单元格非空） |

## 文件结构

```
md2feishudoc-skill/
├── SKILL.md                    # 本文档
├── README.md                   # 项目文档
├── skill-rules.json            # Skill 触发规则
├── config.json.example         # 配置模板
├── md_to_feishu_doc.py         # 主入口
├── feishu_import_client.py     # import_task API 客户端
├── feishu_ownership_transfer.py # 所有权转移模块
├── feishu_validator.py         # 文档校验器
└── docs/
    ├── API_REFERENCE.md        # API 参考
    └── TROUBLESHOOTING.md      # 故障排查
```

## 注意事项

1. **必须使用 user_access_token**：所有权转移需要用户身份授权
2. **权限需发布生效**：在开发者后台创建版本并发布
3. **Token 有效期**：约 2 小时，过期需重新授权

## 故障排查

### 错误：缺少权限
**解决**：开发者后台开通权限 → 创建版本 → 申请发布

### 错误：所有权转移失败
**原因**：可能使用了 tenant_access_token
**解决**：确保完成 OAuth 授权获取 user_access_token

### 错误：表格内容为空
**解决**：使用 import_task 方式（上传文件），飞书自动处理表格格式

更多问题请参考 [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)。