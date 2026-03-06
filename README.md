# Markdown → 飞书文档

将 Markdown 文件导入为飞书云文档，支持：
- 自动 OAuth 授权与 Token 管理
- 标题、列表、表格、粗体等格式
- 文档所有权转移（导入时或独立操作）
- 8 项文档校验

## 功能特性

- ✅ 用户身份创建文档（文档归属用户）
- ✅ 应用身份创建文档（文档归属应用）
- ✅ 自动 Token 管理（OAuth 授权）
- ✅ Markdown 格式支持（标题、列表、表格、粗体）
- ✅ 所有权转移（导入时或独立操作）
- ✅ 会话记忆（只询问一次）
- ✅ 分享到群聊
- ✅ 文档校验（8 项快速校验）

## 安装依赖

```bash
pip install requests
```

## 配置

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

复制 `config.json.example` 为 `config.json` 并填写：

```json
{
  "app_id": "cli_xxxxxxxxxxxx",
  "app_secret": "xxxxxxxxxxxxxxxx",
  "oauth_redirect_uri": "https://open.feishu.cn/api-explorer/loading",
  "folder_token": "",
  "user_access_token": "",
  "token_expires_at": 0,
  "token_scope": ""
}
```

## 使用方式

### 1. 导入文档（用户身份）

```bash
# 首次使用：会提示 OAuth 授权
python md_to_feishu_doc.py \
  --source-type file \
  --file-path ./README.md \
  --title "项目文档"

# 授权后会自动询问是否转移所有权
```

### 2. 导入时自动转移所有权

```bash
# 跳过询问，自动转移所有权给当前用户
python md_to_feishu_doc.py \
  --source-type file \
  --file-path ./README.md \
  --title "项目文档" \
  --auto-transfer
```

### 3. 导入时跳过所有权转移

```bash
# 不转移所有权，也不询问
python md_to_feishu_doc.py \
  --source-type file \
  --file-path ./README.md \
  --title "项目文档" \
  --skip-transfer-prompt
```

### 4. 独立转移所有权

导入后，可以单独转移已有文档的所有权：

```bash
python md_to_feishu_doc.py \
  --transfer-ownership \
  --document-token "doccnxxxxxxxxxx"
```

### 5. 使用动态 Token（推荐）

```bash
python md_to_feishu_doc.py \
  --source-type file \
  --file-path ./README.md \
  --title "项目文档" \
  --token "u-xxxxxxxxxx" \
  --auto-transfer
```

### 6. 应用身份创建（不推荐）

```bash
python md_to_feishu_doc.py \
  --source-type file \
  --file-path ./report.md \
  --title "测试报告" \
  --use-app-identity
```

**注意**：应用身份创建的文档无法转移所有权给用户。

## 命令行参数

| 参数 | 必需 | 说明 |
|------|------|------|
| `--source-type` | ✅ | 来源类型：`text` / `file` / `url` |
| `--file-path` | - | `file` 类型的文件路径 |
| `--url` | - | `url` 类型的 URL 地址 |
| `--source-text` | - | `text` 类型的 Markdown 内容 |
| `--title` | ✅ | 文档标题 |
| `--folder-token` | - | 目标文件夹 token |
| `--use-app-identity` | - | 使用应用身份 |
| `--share-chat-id` | - | 分享到的群聊 ID |
| `--auto-transfer` | - | 自动转移所有权 |
| `--skip-transfer-prompt` | - | 跳过所有权询问 |
| `--transfer-ownership` | - | 独立模式：转移所有权 |
| `--document-token` | - | 要转移的文档 token |
| `--token` | - | user_access_token（动态传入） |
| `--debug` | - | 调试模式 |

## 所有权转移

### 功能说明

- 导入成功后，可以转移文档所有权给当前用户
- 默认询问一次，整个会话期间记住选择
- 转移后原所有者保留完整管理权限
- 新所有者会收到通知

### 转移参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `need_notification` | True | 通知新所有者 |
| `remove_old_owner` | False | 不移除原所有者 |
| `old_owner_perm` | full_access | 原所有者保留完整权限 |

### 使用场景

1. **导入时转移**：导入后立即转移
2. **导入后转移**：对已有文档执行独立转移操作

## Markdown 支持

| Markdown 语法 | 飞书文档效果 |
|--------------|-------------|
| `# 标题` | 标题 1 |
| `## 标题` | 标题 2 |
| `### 标题` | 标题 3-6 |
| `**粗体**` | 粗体文本 |
| `- 列表项` | 无序列表 |
| `1. 列表项` | 有序列表 |
| `| 表格 |` | 原生表格 |
| ` ```代码``` ` | 代码块 |

## 文档校验

导入后可执行 8 项快速校验：

| 用例 | 说明 |
|------|------|
| TC-001 | 文档存在性 |
| TC-002 | 标题匹配 |
| TC-003 | 内容非空 |
| TC-004 | 标题层级验证 |
| TC-005 | 关键词存在 |
| TC-006 | 代码块检测 |
| TC-007 | 段落数量 |
| TC-008 | 表格内容校验 |

## 文件结构

```
md2feishudoc-skill/
├── SKILL.md                    # Skill 定义
├── README.md                   # 本文档
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

## 故障排查

### 错误：缺少权限
**原因**：应用未开通所需权限，或权限未发布生效
**解决**：在开发者后台开通权限 → 创建版本 → 申请发布

### 错误：redirect_uri 不匹配
**原因**：回调 URL 未在安全设置中注册
**解决**：添加重定向 URL 到安全设置

### 错误：所有权转移失败
**原因**：可能使用的是 tenant_access_token
**解决**：确保使用 user_access_token（用户身份授权）

### 错误：token 过期
**现象**：提示需要重新授权
**解决**：删除 config.json 中的 user_access_token 后重新运行

更多问题请参考 [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)。

## 作为 Claude Code Skill 使用

本仓库是一个 Claude Code Skill，可以被 Claude Code 自动识别和调用。

### 安装方式

将本仓库克隆到 Claude Code 的 skills 目录：

```bash
cd ~/.claude/skills
git clone <repo-url> md-to-feishu-doc
```

### 触发方式

当用户说以下关键词时，Claude Code 会自动建议使用此 skill：
- "导入飞书"
- "上传飞书"
- "同步飞书"
- "md转飞书"
- "to feishu"

## License

MIT