# API 参考

本文档提供 md-to-feishu-doc 使用的飞书 API 参考。

## 目录

- [核心 API](#核心-api)
  - [OAuth 授权](#1-oauth-授权)
  - [文档操作](#2-文档操作)
  - [导入任务 API](#3-导入任务-api)
  - [所有权转移 API](#4-所有权转移-api)
- [Block 类型参考](#block-类型参考)
- [权限说明](#权限说明)
- [错误码参考](#错误码参考)
- [速率限制](#速率限制)

## 核心 API

### 1. OAuth 授权

#### 生成授权 URL

```
GET https://open.feishu.cn/open-apis/authen/v1/authorize
```

**参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| app_id | string | 应用 ID |
| redirect_uri | string | 回调 URL |
| scope | string | 权限范围 |
| state | string | 状态参数 |

#### 获取用户 Token

```
POST https://open.feishu.cn/open-apis/authen/v2/oauth/token
```

**请求体**：
```json
{
  "grant_type": "authorization_code",
  "client_id": "app_id",
  "client_secret": "app_secret",
  "code": "authorization_code",
  "redirect_uri": "callback_url"
}
```

**响应**：
```json
{
  "code": 0,
  "access_token": "u-xxx",
  "expires_in": 7200,
  "scope": "docx:document"
}
```

### 2. 文档操作

#### 创建文档

```
POST https://open.feishu.cn/open-apis/docx/v1/documents
```

**请求头**：
```
Authorization: Bearer {access_token}
```

**请求体**：
```json
{
  "title": "文档标题",
  "folder_token": "folder_token"
}
```

**响应**：
```json
{
  "code": 0,
  "data": {
    "document": {
      "document_id": "doccnxxx"
    }
  }
}
```

#### 插入内容块

```
POST https://open.feishu.cn/open-apis/docx/v1/documents/{document_id}/blocks/{block_id}/children
```

**请求体**：
```json
{
  "index": 0,
  "children": [
    {
      "block_type": 2,
      "text": {
        "elements": [
          {"text_run": {"content": "段落内容"}}
        ]
      }
    }
  ]
}
```

### 3. 导入任务 API

#### 上传文件

```
POST https://open.feishu.cn/open-apis/drive/v1/medias/upload_all
```

**Content-Type**: `multipart/form-data`

**表单字段**：
| 字段 | 类型 | 说明 |
|------|------|------|
| file_name | string | 文件名 |
| parent_type | string | 固定值 `ccm_import_open` |
| size | number | 文件大小 |
| extra | string | JSON 字符串 |
| file | binary | 文件内容 |

#### 创建导入任务

```
POST https://open.feishu.cn/open-apis/drive/v1/import_tasks
```

**请求体**：
```json
{
  "file_extension": "md",
  "file_token": "file_token",
  "type": "docx",
  "point": {
    "mount_type": 1,
    "mount_key": "folder_token"
  }
}
```

#### 查询导入结果

```
GET https://open.feishu.cn/open-apis/drive/v1/import_tasks/{ticket}
```

**响应**：
```json
{
  "code": 0,
  "data": {
    "result": {
      "job_status": 0,
      "token": "doccnxxx",
      "url": "https://www.feishu.cn/docx/doccnxxx"
    }
  }
}
```

**job_status 状态码**：
| 状态码 | 说明 |
|--------|------|
| 0 | 导入成功 |
| 1 | 初始化 |
| 2 | 处理中 |
| 3+ | 导入失败 |

### 4. 所有权转移 API

#### 转移文档所有权

```
POST https://open.feishu.cn/open-apis/drive/v1/permissions/{token}/members/transfer_owner
```

**查询参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| type | string | 文档类型 (docx/sheet等) |
| need_notification | boolean | 是否通知新所有者 |
| remove_old_owner | boolean | 是否移除原所有者 |
| old_owner_perm | string | 原所有者权限 |

**请求体**：
```json
{
  "member_type": "openid",
  "member_id": "ou_xxx"
}
```

#### 获取当前用户信息

```
GET https://open.feishu.cn/open-apis/authen/v1/user_info
```

**响应**：
```json
{
  "code": 0,
  "data": {
    "user_id": "xxx",
    "open_id": "ou_xxx",
    "name": "用户名"
  }
}
```

## Block 类型参考

| block_type | 类型名称 | 说明 |
|------------|----------|------|
| 1 | page | 页面 |
| 2 | text | 段落 |
| 3 | heading1 | 一级标题 |
| 4 | heading2 | 二级标题 |
| 5 | heading3 | 三级标题 |
| 6 | heading4 | 四级标题 |
| 7 | heading5 | 五级标题 |
| 8 | heading6 | 六级标题 |
| 12 | bullet | 无序列表 |
| 13 | ordered | 有序列表 |
| 31 | table | 表格 |

## 权限说明

### 必需权限

| 权限 | 说明 | 用途 |
|------|------|------|
| docx:document | 创建及编辑文档 | 创建、编辑飞书文档 |
| auth:user.id:read | 获取用户身份 | OAuth 授权 |
| drive:drive:readonly | 读取云空间 | 所有权转移 |
| docs:permission.member:transfer | 转移文档所有权 | 所有权转移 |

### 权限配置步骤

1. 登录 [飞书开发者后台](https://open.feishu.cn/app)
2. 选择应用 → 权限管理
3. 搜索并开通所需权限
4. 创建版本并发布（权限需发布后生效）

## 错误码参考

| 错误码 | 说明 |
|--------|------|
| 0 | 成功 |
| 99991663 | 权限不足 |
| 99991661 | Token 无效或过期 |
| 99991400 | 参数错误 |
| 99991406 | 资源不存在 |

## 速率限制

- API 调用频率限制：每分钟 60 次
- 建议在批量操作时添加适当延迟