import requests
import json

response = requests.post(
    'https://openrouter.ai/api/v1/responses',
    headers={
        'Authorization': 'Bearer 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',
        'Content-Type': 'application/json',
    },
    json={
        'model': 'openai/o4-mini',
        'input': 'Solve this step by step: If a train travels 60 mph for 2.5 hours, how far does it go?',
        'reasoning': {
            'effort': 'high'
        },
        'stream': True,
        'max_output_tokens': 9000,
    },
    stream=True
)

print(f"Status Code: {response.status_code}\n")
print("=" * 80)

for line in response.iter_lines():
    if line:
        line_str = line.decode('utf-8')
        if line_str.startswith('data: '):
            data = line_str[6:]
            if data == '[DONE]':
                print("\n" + "=" * 80)
                print("Stream finished")
                print("=" * 80)
                break
            try:
                parsed = json.loads(data)
                # 打印格式化的 JSON
                print(json.dumps(parsed, indent=2, ensure_ascii=False))
                print("-" * 80)
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}")
                print(f"Raw data: {data}")
                print("-" * 80)