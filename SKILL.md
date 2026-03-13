---
name: feishu-md-converter
description: 飞书文档与 Markdown 双向转换工具。支持 Markdown→Feishu（导入）和 Feishu→Markdown（导出）两个方向。包含所有权转移功能、文档校验、OAuth授权、Token自动管理。支持 Wiki 和普通文档。触发词：导入飞书、导入文档、to feishu、上传飞书、同步飞书、md转飞书、markdown飞书、飞书文档、导出飞书、飞书转markdown、feishu to md、feishu2md、飞书导出。
---

# 飞书文档 ↔ Markdown 双向转换

支持飞书文档与 Markdown 之间的双向转换：
- **Markdown → 飞书**：导入 Markdown 文件到飞书云文档
- **飞书 → Markdown**：导出飞书文档为 Markdown 文件

功能包括：所有权转移、文档校验、OAuth授权、Token自动管理、Wiki支持、图片下载。

## 适用场景

### Markdown → Feishu
- 将本地 Markdown 文件同步到飞书个人空间
- 将项目 README 转为飞书文档分享
- 批量导入 Markdown 文档到飞书
- 导入后转移文档所有权给当前用户

### Feishu → Markdown
- 将飞书文档导出为 Markdown 存档
- 导出文档用于知识库导入（RAG）
- 将飞书 Wiki 内容转换为 Markdown
- 导出时下载文档中的图片

## 前置要求

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

### 方式一：Markdown → 飞书（导入）

```bash
# 使用 md_to_feishu_doc.py
python md_to_feishu_doc.py \
  --source-type file \
  --file-path ./README.md \
  --title "项目文档" \
  --auto-transfer
```

**参数说明**：
| 参数 | 必需 | 说明 |
|------|------|------|
| `--source-type` | ✅ | 来源类型：`text` / `file` / `url` |
| `--file-path` | - | `file` 类型的文件路径 |
| `--title` | ✅ | 文档标题 |
| `--auto-transfer` | - | 自动转移所有权 |
| `--token` | - | user_access_token（动态传入） |

### 方式二：飞书 → Markdown（导出）

```bash
# 使用 feishu_to_md.py
python feishu_to_md.py \
  --url "https://www.feishu.cn/docx/XXXXXXXXXXXXXXX" \
  --download-images
```

**参数说明**：
| 参数 | 必需 | 说明 |
|------|------|------|
| `--url` | ✅ | 飞书文档 URL（支持 docx 和 wiki） |
| `--output` | - | 输出文件路径 |
| `--download-images` | - | 下载图片到本地 |
| `--enable-heading-numbering` | - | 启用标题编号（仅当原文档无编号时使用） |
| `--image-dir` | - | 图片保存目录 |
| `--token` | - | 访问令牌（可选） |

**⚠️ 标题编号重要提示**：

飞书文档通过 Block 结构存储内容，标题编号的判断和处理逻辑如下：

1. **判断原文档是否自带序号**
   - 查看飞书原文档标题行的文本内容
   - 如果标题文本已包含序号（如"一、封面"、"二、目录"、"1. 背景"、"2. 目的"等），则不需要添加编号
   - 如果标题文本不含序号（如"封面"、"目录"、"背景"、"目的"等），则需要添加编号

2. **`--enable-heading-numbering` 参数行为**
   - 启用后，会为所有标题层级自动添加阿拉伯数字编号（如"1."、"1.1"、"1.1.1"等）
   - 这个编号是**叠加添加**到原文档标题文本上的，不会检测或移除原有的序号

3. **使用建议**
   - **原文档带序号**（如"六、具体需求"）：❌ 不要使用 `--enable-heading-numbering`，否则变成"6. 六、具体需求"
   - **原文档无序号**（如"具体需求"）：✅ 可以使用 `--enable-heading-numbering`，变成"1. 具体需求"

4. **判断方法**
   - 打开飞书原文档，查看标题行的实际文本内容
   - 如果标题行本身就包含"一、"、"1."、"2.1."等序号文本，则无需使用此参数

**支持的 URL 格式**：
- 普通文档：`https://www.feishu.cn/docx/doxcnXXXXXXXXXXXXXXX`
- Wiki 文档：`https://xxx.feishu.cn/wiki/XXXXXXXXXXXXXX`

### 方式三：所有权转移（独立操作）

对已有文档执行所有权转移：

```bash
python md_to_feishu_doc.py \
  --transfer-ownership \
  --document-token "doccnxxxxxxxxxx"
```

## 格式支持

### Markdown → Feishu

| Markdown 语法 | 飞书文档效果 |
|--------------|-------------|
| `# 标题` | 标题 1-6 |
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
| 数学公式 | `$$公式$$` |
| 图片 | `![alt](path)` 或下载到本地 |
| 表格 | 标准 Markdown 表格 |

## 所有权转移功能

- **导入时转移**：导入后立即转移，询问一次后记住会话偏好
- **独立转移**：对已有文档执行转移操作
- **默认设置**：保留原所有者完整权限、通知新所有者

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
├── SKILL.md                    # 本文档
├── README.md                   # 项目文档
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

## 注意事项

1. **Token 有效期**：user_access_token 约有效期 2 小时，过期需重新授权
2. **权限需发布生效**：在开发者后台创建版本并发布
3. **Wiki 支持**：飞书 → Markdown 支持从 Wiki URL 导出文档
4. **图片下载**：导出时可选择是否下载图片到本地
5. **标题编号功能**：
   - 自动检测标题文本是否已带序号（中文如"一、"或阿拉伯数字如"1."）
   - 如原文档标题已带序号，则不添加额外编号
   - 如原文档标题无序号，则添加阿拉伯数字层级编号
   - 有序列表按父级独立编号，每个父级下从 1 开始

## Wiki 文档访问的关键秘诀

### 核心原理

飞书 Wiki 文档本质上是存储在 Wiki 空间中的普通文档，可以通过以下两种方式访问：

```
方式 A：Wiki API（复杂）
Wiki URL → Wiki 节点 API → 获取文档 ID → 文档 API
         ↓ 需要空间权限，容易失败

方式 B：直接访问（推荐）✅
Wiki URL → 直接用 token 作为文档 ID → 文档 API
         ↓ 简单直接，绕过空间限制
```

### 关键要点

| 要点 | 说明 |
|------|------|
| **使用 user_access_token** | 私有 Wiki 空间必须使用用户身份权限 |
| **Wiki token = 文档 ID** | URL 中的 token 可直接作为文档 ID 使用 |
| **绕过 Wiki API** | 不需要调用复杂的 Wiki 节点 API |

### Token 优先级

系统按以下优先级选择访问令牌：

1. **命令行传入的 token**（`--token` 参数）
2. **配置文件中的 user_access_token**
3. **tenant_access_token**（回退方案，仅限公开文档）

### 配置示例

```json
{
  "user_access_token": "u-ccfdsDqk959FK7uvIilKm_k0n7exkhoXNUGa3N200CDq",
  "app_id": "cli_a8fecf133d129013",
  "app_secret": "EB1Rgv8ttxg5haAIP1AMz8Q5su0Gi2vp"
}
```

### 常见错误处理

| 错误 | 原因 | 解决方法 |
|------|------|----------|
| 找到 0 个 Wiki 空间 | 使用了 tenant_access_token | 配置 user_access_token |
| HTTP 400: Bad Request | Wiki API 调用失败 | 使用直接访问方式 |
| 无法从 Wiki 节点获取文档 ID | 节点权限不足 | 使用 token 直接访问 |

## 故障排查

### 错误：缺少权限
**解决**：开发者后台开通权限 → 创建版本 → 申请发布

### 错误：所有权转移失败
**原因**：可能使用了 tenant_access_token
**解决**：确保完成 OAuth 授权获取 user_access_token

### 错误：URL 无法识别
**解决**：检查 URL 格式是否为 `https://www.feishu.cn/docx/...` 或 `https://xxx.feishu.cn/wiki/...`

更多问题请参考 [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)。
