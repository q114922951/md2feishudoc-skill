# 飞书文档 ↔ Markdown 双向转换

将飞书文档与 Markdown 文件进行双向转换：
- **Markdown → 飞书**：导入 Markdown 到飞书云文档
- **飞书 → Markdown**：导出飞书文档为 Markdown

## 功能特性

### Markdown → Feishu
- ✅ 用户身份创建文档（文档归属用户）
- ✅ 应用身份创建文档（文档归属应用）
- ✅ 自动 Token 管理（OAuth 授权）
- ✅ Markdown 格式支持（标题、列表、表格、粗体）
- ✅ 所有权转移（导入时或独立操作）
- ✅ 会话记忆（只询问一次）
- ✅ 分享到群聊
- ✅ 文档校验（8 项快速校验）

### Feishu → Markdown
- ✅ 支持普通文档（docx）和 Wiki
- ✅ 完整格式保留（标题、列表、表格、代码块）
- ✅ 图片下载到本地（可选）
- ✅ 纯文本模式（可选）
- ✅ 数学公式支持
- ✅ 文件夹递归查找（Wiki）
- ✅ Windows 编码支持

## 安装依赖

```bash
pip install requests
```

## 配置

### 1. 飞书应用配置

在 [飞书开发者后台](https://open.feishu.cn/app) 创建或选择应用：

**必需权限**：
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

### 方向一：Markdown → 飞书

#### 1. 导入文档（用户身份）

```bash
# 首次使用：会提示 OAuth 授权
python md_to_feishu_doc.py \
  --source-type file \
  --file-path ./README.md \
  --title "项目文档"

# 授权后会自动询问是否转移所有权
```

#### 2. 导入时自动转移所有权

```bash
python md_to_feishu_doc.py \
  --source-type file \
  --file-path ./README.md \
  --title "项目文档" \
  --auto-transfer
```

#### 3. 使用动态 Token（推荐）

```bash
python md_to_feishu_doc.py \
  --source-type file \
  --file-path ./README.md \
  --title "项目文档" \
  --token "u-xxxxxxxxxx" \
  --auto-transfer
```

#### 4. 独立转移所有权

对已有文档执行所有权转移：

```bash
python md_to_feishu_doc.py \
  --transfer-ownership \
  --document-token "doccnxxxxxxxxxx"
```

**命令行参数**：
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

### 方向二：Feishu → Markdown

#### 1. 导出普通文档

```bash
python feishu_to_md.py \
  --url "https://www.feishu.cn/docx/XXXXXXXXXXXXXXX"
```

#### 2. 导出 Wiki 文档

```bash
python feishu_to_md.py \
  --url "https://xxx.feishu.cn/wiki/XXXXXXXXXXXXXX"
```

#### 3. 导出并下载图片

```bash
python feishu_to_md.py \
  --url "https://www.feishu.cn/docx/XXXXXXXXXXXXXXX" \
  --download-images
```

#### 4. 指定输出路径

```bash
python feishu_to_md.py \
  --url "https://www.feishu.cn/docx/XXXXXXXXXXXXXXX" \
  --output my_document.md
```

**命令行参数**：
| 参数 | 必需 | 说明 |
|------|------|------|
| `--url` | ✅ | 飞书文档 URL（支持 docx 和 wiki） |
| `--output` | - | 输出文件路径 |
| `--config` | - | 配置文件路径 |
| `--token` | - | 访问令牌（可选） |
| `--use-raw` | - | 使用纯文本模式 |
| `--api-base` | - | API 基础地址 |
| `--download-images` | - | 下载图片到本地 |
| `--enable-heading-numbering` | - | 启用标题编号 |
| `--image-dir` | - | 图片保存目录 |
| `--output-folder` | - | 输出文件夹路径 |

**支持的 URL 格式**：
- 普通文档：`https://www.feishu.cn/docx/doxcnXXXXXXXXXXXXXXX`
- Wiki 文档：`https://xxx.feishu.cn/wiki/XXXXXXXXXXXXXX`

## 格式支持

### Markdown → Feishu

| Markdown 语法 | 飞书文档效果 |
|--------------|-------------|
| `# 标题` | 标题 1-6 |
| `## 标题` | 标题 2-6 |
| `**粗体**` | 粗体文本 |
| `- 列表项` | 无序列表 |
| `1. 列表项` | 有序列表 |
| `| 表格 |` | 原生表格 |
| ` ```代码``` ` | 代码块 |

### Feishu → Markdown

| 飞书元素 | Markdown 输出 |
|-----------|--------------|
| 标题 1-9 | `#` 到 `#########` |
| 文本段落 | 普通文本 |
| 无序列表 | `- 列表项` |
| 有序列表 | `1. 列表项` |
| 代码块 | ` ```language\ncode\n``` ` |
| 引用块 | `> 文本` |
| 待办事项 | `- [ ]` / `- [x]` |
| 高亮块 | `> emoji 文本` |
| 数学公式 | `$$公式$$` |
| 图片 | `![alt](path)` 或原始 URL |
| 表格 | 标准 Markdown 表格 |

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
├── md_to_feishu_doc.py         # Markdown → 飞书
├── feishu_to_md.py            # 飞书 → Markdown
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

### 错误：URL 无法识别
**原因**：URL 格式不正确
**解决**：检查 URL 格式是否为 `https://www.feishu.cn/docx/...` 或 `https://xxx.feishu.cn/wiki/...`

更多问题请参考 [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)。

## 作为 Claude Code Skill 使用

本仓库是一个 Claude Code Skill，可以被 Claude Code 自动识别和调用。

### 安装方式

将本仓库克隆或复制到 Claude Code 的 skills 目录：

```bash
cd ~/.claude/skills
git clone <repo-url> feishu-md-converter
```

或者复制整个目录：

```bash
cp -r /path/to/md2feishudoc-skill ~/.claude/skills/feishu-md-converter
```

### 添加到 skill-rules.json

在 `.claude/skills/skill-rules.json` 中添加以下配置：

```json
{
  "version": "1.0",
  "skills": {
    "feishu-md-converter": {
      "type": "domain",
      "enforcement": "suggest",
      "priority": "high",
      "promptTriggers": {
        "keywords": [
          "导入飞书",
          "导入文档",
          "convert to feishu",
          "to feishu",
          "上传飞书",
          "同步飞书",
          "md转飞书",
          "markdown飞书",
          "飞书文档",
          "导出飞书",
          "飞书转markdown",
          "feishu to md",
          "feishu2md",
          "飞书导出"
        ],
        "intentPatterns": [
          "导入.*md",
          "导入.*markdown",
          "上传.*飞书",
          "同步.*飞书",
          "转换.*飞书",
          "创建飞书文档",
          "md.*飞书",
          "markdown.*飞书",
          "飞书.*md",
          "飞书.*markdown",
          "导出.*md",
          "导出.*markdown",
          "飞书.*导出",
          "转换.*md"
        ]
      },
      "fileTriggers": {
        "pathPatterns": [
          "**/*.md",
          "**/*.markdown"
        ],
        "contentPatterns": [
          "导入.*飞书",
          "上传.*文档",
          "同步.*飞书",
          "飞书.*导出",
          "飞书.*转换"
        ]
      }
    }
  }
}
```

**注意**: 也可以使用 `skill-rules-claude.json` 文件，该文件已包含正确的 Claude Code 格式配置。

### 验证安装

```bash
# 检查 JSON 语法
cat ~/.claude/skills/skill-rules.json | jq .
```

### 触发方式

当用户说以下关键词时，Claude Code 会自动建议使用此 skill：

**Markdown → Feishu**：
- "导入飞书"
- "上传飞书"
- "同步飞书"
- "md转飞书"
- "to feishu"

**Feishu → Markdown**：
- "导出飞书"
- "飞书转markdown"
- "feishu to md"
- "feishu2md"
- "飞书导出"

## License

MIT
