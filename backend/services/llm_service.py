import requests
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


def call_llm(model_config, messages, temperature=None, max_tokens=None):
    """
    统一调用 OpenAI 兼容 / 国产大模型 API

    支持的 provider：
    - custom / deepseek：标准 OpenAI 兼容格式
    - wenxin：百度文心（需 Bearer token + 千帆 API 格式）
    - qwen：通义千问（OpenAI 兼容，enable_search 开启联网搜索）
    - glm：智谱 GLM（OpenAI 兼容，tools 添加 web_search）

    Args:
        model_config: dict with api_base_url, api_key, model_name, provider
        messages: list of {"role": ..., "content": ...}
        temperature: float
        max_tokens: int

    Returns:
        str: 模型回复文本
    """
    provider = model_config.get('provider', 'custom')

    if provider == 'wenxin':
        return _call_wenxin(model_config, messages, temperature, max_tokens)
    elif provider == 'qwen':
        return _call_qwen(model_config, messages, temperature, max_tokens)
    elif provider == 'glm':
        return _call_glm(model_config, messages, temperature, max_tokens)
    else:
        # custom / deepseek / 其他 OpenAI 兼容
        return _call_openai_compatible(model_config, messages, temperature, max_tokens)


def _call_openai_compatible(model_config, messages, temperature=None, max_tokens=None):
    """OpenAI 兼容格式（DeepSeek 等）"""
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

    response = requests.post(url, json=payload, headers=headers, timeout=300, verify=True)
    response.raise_for_status()
    data = response.json()
    return data['choices'][0]['message']['content']


def _call_qwen(model_config, messages, temperature=None, max_tokens=None):
    """通义千问 — 开启 enable_search 联网搜索参数

    API 文档：https://help.aliyun.com/zh/model-studio/
    关键参数：enable_search=True 启用联网搜索
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
        'max_tokens': max_tokens if max_tokens is not None else 4096,
        'enable_search': True  # 通义千问联网搜索
    }

    response = requests.post(url, json=payload, headers=headers, timeout=300, verify=True)
    response.raise_for_status()
    data = response.json()

    # 提取搜索引用（如有）
    search_info = data.get('search_info', {})
    if search_info and search_info.get('search_results'):
        logger.info(f"Qwen web search returned {len(search_info['search_results'])} results")

    return data['choices'][0]['message']['content']


def _call_glm(model_config, messages, temperature=None, max_tokens=None):
    """智谱 GLM — 注入独立 Web Search API 结果到 prompt

    智谱的 tools 模式 web_search 需要 model 返回 tool_calls 后才能获取结果，
    但 GLM-4-Flash 的 tools 模式不稳定。

    改用独立 Web Search API（POST /api/paas/v4/web_search），
    在调用 Chat API 之前先执行搜索，将搜索结果作为联网信息注入 system prompt。

    API 文档：https://docs.bigmodel.cn/cn/guide/models/free/glm-4-flash-250414
    """
    import json

    api_key = model_config['api_key']
    base_url = model_config['api_base_url'].rstrip('/')

    # Step 1: 提取搜索查询词
    search_query = ''
    for msg in reversed(messages):
        if msg.get('role') == 'user':
            search_query = msg.get('content', '')[:200]
            break
    if not search_query:
        search_query = '招商引资 企业信息'

    # Step 2: 调用独立的 Web Search API
    search_results = _glm_web_search(api_key, search_query, count=5)

    # Step 3: 将搜索结果注入到 messages 中
    enriched_messages = list(messages)
    if search_results:
        search_context = '【以下为互联网最新搜索结果，请参考这些信息进行研判分析】\n\n'
        for i, r in enumerate(search_results[:5], 1):
            title = r.get('title', '无标题')
            content = r.get('content', '')[:300]
            link = r.get('link', '')
            search_context += f'{i}. **{title}**\n'
            search_context += f'   {content}\n'
            if link:
                search_context += f'   来源：{link}\n'
            search_context += '\n'
        # 注入到 system prompt 或第一条消息之前
        if enriched_messages and enriched_messages[0].get('role') == 'system':
            enriched_messages[0]['content'] = enriched_messages[0]['content'] + '\n\n' + search_context
        else:
            enriched_messages.insert(0, {'role': 'system', 'content': search_context})

    # Step 4: 调用 Chat API
    url = f'{base_url}/chat/completions'
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    payload = {
        'model': model_config['model_name'],
        'messages': enriched_messages,
        'temperature': temperature if temperature is not None else 0.7,
        'max_tokens': max_tokens if max_tokens is not None else 4096
    }

    response = requests.post(url, json=payload, headers=headers, timeout=300, verify=True)
    response.raise_for_status()
    data = response.json()
    return data['choices'][0]['message']['content']


def _glm_web_search(api_key, query, count=5):
    """调用智谱 Web Search 独立 API

    POST https://open.bigmodel.cn/api/paas/v4/web_search

    返回格式：
    [
      {"title": "标题", "content": "摘要", "link": "URL", "publish_date": "...", ...},
      ...
    ]
    """
    import uuid
    web_search_url = 'https://open.bigmodel.cn/api/paas/v4/web_search'
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    payload = {
        'search_query': query,
        'search_engine': 'search_std',
        'search_intent': False,
        'count': count,
        'search_recency_filter': 'noLimit',
        'request_id': str(uuid.uuid4())
    }
    try:
        resp = requests.post(web_search_url, json=payload, headers=headers, timeout=30, verify=True)
        resp.raise_for_status()
        data = resp.json()
        results = data.get('search_result', [])
        logger.info(f'GLM Web Search: query="{query}", results={len(results)}')
        return results
    except Exception as e:
        logger.warning(f'GLM Web Search failed: {e}')
        return []


def _extract_search_queries(lead_context):
    """从线索上下文中提取 3-5 个搜索关键词，用于联网搜索。

    从大段文本中用规则提取：企业名、项目名、行业关键词等。
    返回 list[str]，每个不超过 70 字符。
    """
    queries = []
    lines = lead_context.split('\n')
    enterprise = ''
    project = ''
    content = ''

    for line in lines:
        s = line.strip()
        if s.startswith('【企业名称】'):
            enterprise = s.replace('【企业名称】', '').strip()
        elif s.startswith('【项目名称】'):
            project = s.replace('【项目名称】', '').strip()
        elif s.startswith('【项目内容】'):
            content = s.replace('【项目内容】', '').strip()[:100]

    # Query 1: 企业舆情
    if enterprise:
        queries.append(f'{enterprise} 经营风险 舆情')
        queries.append(f'{enterprise} 最新新闻 投资')
    # Query 2: 项目市场调研
    if enterprise and project:
        queries.append(f'{project} 市场分析 行业前景')
    # Query 3: 区域布局
    if enterprise:
        queries.append(f'{enterprise} 湖北 产业布局 投资')
    # Query 4: 从项目内容中提取关键词
    if content:
        # 取前 40 字作为搜索 query
        queries.append(content[:60])

    # 去重并限制长度
    seen = set()
    result = []
    for q in queries:
        q = q.strip()[:70]
        if q and q not in seen:
            seen.add(q)
            result.append(q)
    return result[:5]


def _glm_web_search_batch(api_key, lead_context, count_per_query=5):
    """从线索中提取搜索关键词，并行发起多个 Web Search 请求。

    Args:
        api_key: 智谱 API key（用于 Web Search API）
        lead_context: 线索信息文本块
        count_per_query: 每个 query 返回的结果数

    Returns:
        str: 格式化后的搜索结果文本（用于注入 prompt），失败时返回空字符串
    """
    queries = _extract_search_queries(lead_context)
    if not queries:
        logger.info('GLM Web Search Batch: no queries extracted')
        return ''

    logger.info(f'GLM Web Search Batch: {len(queries)} queries -> {queries}')

    # 并行搜索（max 3 并发，避免 QPS 限制）
    all_results = []  # [(query, results), ...]
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(_glm_web_search, api_key, q, count_per_query): q
            for q in queries
        }
        for future in as_completed(futures):
            query = futures[future]
            try:
                results = future.result()
                if results:
                    all_results.append((query, results))
            except Exception as e:
                logger.warning(f'GLM Web Search Batch: query "{query}" failed: {e}')

    if not all_results:
        return ''

    # 格式化搜索结果
    return _format_batch_search_results(all_results)


def _format_batch_search_results(all_results):
    """将多组搜索结果格式化为统一的 Markdown 文本。

    Args:
        all_results: [(query, [result_dict, ...]), ...]

    Returns:
        str: Markdown 格式的搜索结果
    """
    # 去重（按 URL）
    seen_urls = set()
    deduped = []

    for query, results in all_results:
        fresh = []
        for r in results:
            url = r.get('link', '')
            if url and url in seen_urls:
                continue
            if url:
                seen_urls.add(url)
            fresh.append(r)
        if fresh:
            deduped.append((query, fresh))

    if not deduped:
        return ''

    lines = ['【以下为互联网最新搜索结果，请参考这些信息进行研判分析】', '']
    idx = 1
    for query, results in deduped:
        lines.append(f'## 搜索主题：{query}')
        for r in results[:5]:
            title = r.get('title', '无标题')
            content = r.get('content', '')[:200]
            link = r.get('link', '')
            date = r.get('publish_date', '')
            date_str = f' ({date})' if date else ''
            media = r.get('media', '')
            media_str = f' — {media}' if media else ''
            lines.append(f'{idx}. **{title}**{media_str}{date_str}')
            lines.append(f'   {content}')
            if link:
                lines.append(f'   来源：{link}')
            lines.append('')
            idx += 1

    return '\n'.join(lines)


def call_llm_with_web_search(main_config, search_config, messages,
                              temperature=None, max_tokens=None,
                              lead_context=''):
    """两阶段异步研判：联网搜索 → DeepSeek 合成。

    Phase 1: 使用 GLM-4-Flash Web Search API 获取联网数据
    Phase 2: 将搜索结果注入 messages，调用主模型（DeepSeek）生成研判报告

    如果搜索阶段失败或 search_config 为空，降级为直接调用主模型。

    Args:
        main_config: dict with api_base_url, api_key, model_name (主模型)
        search_config: dict with api_base_url, api_key, model_name (搜索模型)
                      可为 None，此时跳过搜索阶段
        messages: list of {"role": ..., "content": ...}
        temperature: float
        max_tokens: int
        lead_context: str，线索信息文本（用于提取搜索关键词）

    Returns:
        dict: {'result': '模型回复文本', 'search_results_text': '搜索格式化文本(空则无)'}
    """
    search_results_text = ''

    # 阶段一：联网搜索
    if search_config and search_config.get('api_key'):
        try:
            search_results_text = _glm_web_search_batch(
                search_config['api_key'],
                lead_context,
                count_per_query=5
            )
        except Exception as e:
            logger.warning(f'Web search phase failed, falling back to direct call: {e}')
            search_results_text = ''

    # 阶段二：注入搜索结果 + 调用主模型
    enriched_messages = list(messages)
    if search_results_text:
        if enriched_messages and enriched_messages[0].get('role') == 'system':
            enriched_messages[0]['content'] = (
                enriched_messages[0]['content'] + '\n\n' + search_results_text
            )
        else:
            enriched_messages.insert(0, {'role': 'system', 'content': search_results_text})

    result = call_llm(main_config, enriched_messages, temperature, max_tokens)
    return {
        'result': result,
        'search_results_text': search_results_text
    }


def _call_wenxin(model_config, messages, temperature=None, max_tokens=None):
    """百度文心 — 千帆 API 格式，自动携带 searchInfo

    API 文档：https://cloud.baidu.com/doc/WENXINWORKSHOP/
    百度文心会自动在回复中携带 search_info，无需额外参数
    但请求格式与 OpenAI 不同，需要先获取 access_token，再调用模型端点
    """
    # 1. Get access_token
    api_key = model_config['api_key']      # 千帆格式：client_id
    secret_key = model_config.get('secret_key', '')  # 千帆格式：client_secret
    if not secret_key:
        # 如果没有 secret_key，尝试用 api_key 作为 bearer token（兼容旧配置）
        return _call_openai_compatible(model_config, messages, temperature, max_tokens)

    token_url = f'https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={api_key}&client_secret={secret_key}'
    token_resp = requests.post(token_url, timeout=30)
    token_resp.raise_for_status()
    access_token = token_resp.json().get('access_token')

    if not access_token:
        raise ValueError(f'获取百度 access_token 失败: {token_resp.text}')

    # 2. Call chat endpoint
    model_name = model_config.get('model_name', 'ernie-4.0-turbo-128k')
    url = f'https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/{model_name}?access_token={access_token}'

    # Convert messages to 千帆 format
    system_prompt = ''
    user_messages = []
    for msg in messages:
        if msg['role'] == 'system':
            system_prompt = msg['content']
        else:
            user_messages.append({'role': msg['role'], 'content': msg['content']})

    payload = {
        'messages': user_messages,
        'system': system_prompt,
        'temperature': temperature if temperature is not None else 0.7
    }
    if max_tokens:
        payload['max_output_tokens'] = max_tokens

    response = requests.post(url, json=payload, timeout=300, verify=True)
    response.raise_for_status()
    data = response.json()

    # 百度文心自动返回 search_info
    search_info = data.get('search_info', {})
    if search_info and search_info.get('search_results'):
        logger.info(f"Wenxin search returned {len(search_info['search_results'])} results")

    return data.get('result', '')


def build_messages(user_input, prompt_template=None, system_prompt=None):
    """构建 messages 数组"""
    messages = []
    if system_prompt:
        messages.append({'role': 'system', 'content': system_prompt})
    if prompt_template:
        full_prompt = prompt_template.replace('{{user_input}}', user_input)
    else:
        full_prompt = user_input
    messages.append({'role': 'user', 'content': full_prompt})
    return messages
