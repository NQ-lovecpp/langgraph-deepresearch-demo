# OpenRouter O4 推理助手

一个美观的聊天界面，用于与 OpenRouter 的 O4-mini 模型对话，实时展示 AI 的推理过程。

## 功能特点

- 🎨 **美观的现代化界面** - 渐变色设计，流畅的动画效果
- 🧠 **实时推理展示** - 流式输出 AI 的思考过程
- ✨ **清晰的答案展示** - 分离展示推理过程和最终答案
- ⚡ **三种推理强度** - Low/Medium/High Effort 可选
- 📱 **响应式设计** - 支持桌面和移动设备

## 文件说明

- `chat.html` - 前端聊天界面（单文件，无需构建）
- `server.py` - Flask 后端服务器，处理 OpenRouter API 调用
- `test_orouter.py` - 原始测试脚本（用于调试）

## 快速开始

### 1. 安装依赖

```bash
pip install flask flask-cors requests
```

### 2. 启动服务器

```bash
cd playground
python server.py
```

服务器将在 `http://localhost:5000` 启动

### 3. 打开聊天界面

在浏览器中打开：
```
http://localhost:5000/chat.html
```

或者直接用浏览器打开 `chat.html` 文件（需要服务器在后台运行）

## 使用说明

1. **选择推理强度**：
   - Low Effort - 快速简单的回答
   - Medium Effort - 平衡的推理深度（默认）
   - High Effort - 深度详细的推理过程

2. **输入问题**：在输入框中输入你的问题

3. **查看结果**：
   - 🧠 推理过程 - 展示 AI 的思考步骤
   - ✨ 答案 - 最终的完整答案

## API 端点

### POST /chat

发送聊天消息并获取流式响应。

**请求体：**
```json
{
  "message": "用户问题",
  "effort": "medium"  // low, medium, 或 high
}
```

**响应：**
Server-Sent Events (SSE) 流，包含以下事件类型：

```javascript
// 推理过程增量
data: {"type": "reasoning", "content": "推理文本片段"}

// 答案增量
data: {"type": "answer", "content": "答案文本片段"}

// 完成
data: [DONE]
```

## 技术栈

**前端：**
- 纯 HTML/CSS/JavaScript
- 无需任何框架或构建工具
- Server-Sent Events (SSE) 用于流式更新

**后端：**
- Python 3.x
- Flask - Web 框架
- Flask-CORS - 跨域支持
- Requests - HTTP 客户端

## 注意事项

⚠️ **重要：** 请将 `server.py` 中的 `OPENROUTER_API_KEY` 替换为你自己的 API 密钥。

建议使用环境变量管理 API 密钥：

```python
import os
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')
```

然后在启动服务器前设置环境变量：
```bash
export OPENROUTER_API_KEY="your-api-key-here"
python server.py
```

## 示例问题

- "如果一列火车以 60 英里/小时的速度行驶 2.5 小时，它走了多远？"
- "解释量子纠缠的基本原理"
- "设计一个简单的排序算法并分析其时间复杂度"

## 故障排除

**端口已被占用：**
修改 `server.py` 中的端口号：
```python
app.run(debug=True, port=8080, threaded=True)
```

**CORS 错误：**
确保已安装并启用 Flask-CORS：
```bash
pip install flask-cors
```

**连接超时：**
检查网络连接和 OpenRouter API 状态。

## License

MIT License




