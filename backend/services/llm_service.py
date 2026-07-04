import requests


def call_llm(model_config, messages, temperature=None, max_tokens=None):
    """
    统一调用 OpenAI 兼容 API

    Args:
        model_config: dict with api_base_url, api_key, model_name
        messages: list of {"role": "system"|"user"|"assistant", "content": "..."}
        temperature: float
        max_tokens: int

    Returns:
        str: 模型回复文本

    Raises:
        requests.RequestException: 网络错误
        ValueError: API 返回错误
    """
    base_url = model_config['api_base_url'].rstrip('/')
    url = f'{base_url}/chat/completions'

    headers = {
        'Authorization': f'Bearer {model_config["api_key"]}',
        'Content-Type': 'application/json'
    }

    payload = {
        'model': model_config['model_name'],
        'messages': messages,
        'temperature': temperature if temperature is not None else 0.7,
        'max_tokens': max_tokens if max_tokens is not None else 4096
    }

    response = requests.post(url, json=payload, headers=headers, timeout=300)
    response.raise_for_status()

    data = response.json()
    return data['choices'][0]['message']['content']


def build_messages(user_input, prompt_template=None, system_prompt=None):
    """
    构建 messages 数组

    Args:
        user_input: 用户输入的原始文本
        prompt_template: 提示词模板（含 {{user_input}} 占位符）
        system_prompt: 系统提示词

    Returns:
        list: messages 数组
    """
    messages = []

    if system_prompt:
        messages.append({'role': 'system', 'content': system_prompt})

    if prompt_template:
        full_prompt = prompt_template.replace('{{user_input}}', user_input)
    else:
        full_prompt = user_input

    messages.append({'role': 'user', 'content': full_prompt})

    return messages
