# NovelAI 请求队列系统

## 概述

为了解决 NovelAI 不支持并发调用的问题，我们实现了一个请求队列系统。该系统确保同时只有一个请求在处理，其他请求在队列中等待。

## 功能特性

- **队列管理**: 最大队列长度为 10 个请求
- **并发控制**: 确保同时只有一个请求在处理
- **状态跟踪**: 实时跟踪请求状态（排队中、处理中、已完成、失败）
- **自动清理**: 自动清理超过 1 小时的过期请求
- **队列满处理**: 当队列满时返回 HTTP 423 状态码

## API 端点

### 1. 同步图像生成请求（推荐）
```
GET /generate/img/priv?prompt=<prompt>&seed=<seed>&model=<model>
```

**特点**:
- 直接在同一请求中返回生成的图像
- 请求会在队列中等待，直到处理完成
- 响应时间通常为5-10秒（取决于队列长度）

**响应**:
- 成功: 直接返回生成的图像 (image/png)
- 队列满: HTTP 423 "Request queue is full. Please try again later."
- 失败: HTTP 500 包含错误信息

### 2. 异步图像生成请求
```
GET /generate/img/async?prompt=<prompt>&seed=<seed>&model=<model>
```

**响应示例**:
```json
{
  "request_id": "uuid-string",
  "status": "queued",
  "message": "Request added to queue. Use /status/{request_id} to check progress.",
  "queue_status": {
    "queue_size": 1,
    "max_queue_size": 10,
    "is_processing": false,
    "current_request_id": null
  }
}
```

### 2. 查询请求状态
```
GET /status/{request_id}
```

**响应示例**:
```json
{
  "request_id": "uuid-string",
  "status": "processing",
  "timestamp": 1234567890.123,
  "queue_status": {
    "queue_size": 0,
    "max_queue_size": 10,
    "is_processing": true,
    "current_request_id": "uuid-string"
  }
}
```

### 3. 获取请求结果
```
GET /result/{request_id}
```

**响应**:
- 成功: 返回生成的图像 (image/png)
- 排队中: HTTP 202 "Request is still in queue"
- 处理中: HTTP 202 "Request is being processed"
- 失败: HTTP 500 包含错误信息

### 4. 查询队列状态
```
GET /queue/status
```

**响应示例**:
```json
{
  "queue_size": 2,
  "max_queue_size": 10,
  "is_processing": true,
  "current_request_id": "uuid-string"
}
```

### 5. 清空队列（管理用）
```
DELETE /queue/clear
```

## 请求状态说明

- `queued`: 请求已提交，在队列中等待
- `processing`: 请求正在处理中
- `completed`: 请求处理完成，可以获取结果
- `failed`: 请求处理失败

## 使用流程

### 同步模式（推荐）
1. **直接调用**: 调用 `/generate/img/priv`
2. **等待响应**: 请求会在队列中等待并直接返回图像结果
3. **处理结果**: 直接获得生成的图像数据

### 异步模式
1. **提交请求**: 调用 `/generate/img/async` 获取 `request_id`
2. **轮询状态**: 使用 `request_id` 调用 `/status/{request_id}` 检查状态
3. **获取结果**: 当状态为 `completed` 时，调用 `/result/{request_id}` 获取图像

## 错误处理

- **HTTP 423**: 队列已满，请稍后重试
- **HTTP 404**: 请求 ID 不存在
- **HTTP 202**: 请求仍在处理中
- **HTTP 500**: 服务器内部错误

## 配置参数

- **最大队列长度**: 10 个请求
- **请求过期时间**: 1 小时
- **清理间隔**: 10 分钟

## 测试

运行测试脚本来验证队列功能:

```bash
python test_queue.py
```

## 启动服务器

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## 注意事项

1. 请求结果会在内存中保存 1 小时，之后自动清理
2. 服务器重启会丢失所有队列中的请求
3. 建议客户端实现适当的重试机制
4. 对于长时间运行的服务，建议监控队列状态避免积压
