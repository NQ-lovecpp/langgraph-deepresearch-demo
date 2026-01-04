import requests
import json
import os
from flask import Flask, request, Response, stream_with_context, send_file
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# OpenRouter API 配置
OPENROUTER_API_KEY = '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'
OPENROUTER_URL = 'https://openrouter.ai/api/v1/responses'
MODEL = 'openai/o4-mini'

@app.route('/')
def index():
    return '''
    <html>
        <head><title>OpenRouter Chat Server</title></head>
        <body>
            <h1>OpenRouter Chat Server is Running!</h1>
            <p>Open <a href="/chat.html">chat.html</a> to start chatting.</p>
        </body>
    </html>
    '''

@app.route('/chat.html')
def chat_page():
    """提供聊天界面"""
    chat_html_path = os.path.join(os.path.dirname(__file__), 'chat.html')
    return send_file(chat_html_path)

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message', '')
    effort = data.get('effort', 'medium')
    
    if not user_message:
        return {'error': 'No message provided'}, 400
    
    def generate():
        try:
            # 调用 OpenRouter API
            response = requests.post(
                OPENROUTER_URL,
                headers={
                    'Authorization': f'Bearer {OPENROUTER_API_KEY}',
                    'Content-Type': 'application/json',
                },
                json={
                    'model': MODEL,
                    'input': user_message,
                    'reasoning': {
                        'effort': effort
                    },
                    'stream': True,
                    'max_output_tokens': 9000,
                },
                stream=True
            )
            
            if response.status_code != 200:
                yield f'data: {json.dumps({"type": "error", "content": f"API Error: {response.status_code}"})}\n\n'
                return
            
            reasoning_text = ""
            answer_text = ""
            
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    
                    # 跳过 OPENROUTER PROCESSING 消息
                    if line_str.startswith(': OPENROUTER'):
                        continue
                    
                    if line_str.startswith('data: '):
                        data = line_str[6:]
                        if data == '[DONE]':
                            yield f'data: [DONE]\n\n'
                            break
                        
                        try:
                            parsed = json.loads(data)
                            event_type = parsed.get('type')
                            
                            # 处理推理摘要文本增量
                            if event_type == 'response.reasoning_summary_text.delta':
                                delta = parsed.get('delta', '')
                                reasoning_text += delta
                                yield f'data: {json.dumps({"type": "reasoning", "content": delta})}\n\n'
                            
                            # 处理输出文本增量
                            elif event_type == 'response.output_text.delta':
                                delta = parsed.get('delta', '')
                                answer_text += delta
                                yield f'data: {json.dumps({"type": "answer", "content": delta})}\n\n'
                            
                            # 处理完成的推理摘要
                            elif event_type == 'response.reasoning_summary_text.done':
                                full_text = parsed.get('text', '')
                                if full_text and not reasoning_text:
                                    # 如果没有增量更新，一次性发送完整文本
                                    reasoning_text = full_text
                                    yield f'data: {json.dumps({"type": "reasoning", "content": full_text})}\n\n'
                            
                        except json.JSONDecodeError:
                            continue
        
        except Exception as e:
            yield f'data: {json.dumps({"type": "error", "content": str(e)})}\n\n'
    
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )

if __name__ == '__main__':
    print("🚀 Server starting at http://localhost:5000")
    print("📱 Open http://localhost:5000/chat.html in your browser")
    app.run(debug=True, port=5000, threaded=True)

