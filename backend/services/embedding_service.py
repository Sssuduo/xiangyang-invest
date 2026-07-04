"""
向量化与语义搜索服务

通过 LLM API 的 /embeddings 端点将文本转换为向量，
并基于余弦相似度进行语义检索。
"""
import json
import math
import requests


def get_embedding(text, model_config, embedding_model=None):
    """调用 OpenAI 兼容的 /embeddings 端点获取向量

    Args:
        text: 待向量化的文本
        model_config: dict with api_base_url, api_key, model_name,
                      可选 embedding_api_url, embedding_api_key, embedding_model_name
        embedding_model: embedding 模型名（可选，默认自动推断）

    Returns:
        tuple: (embedding: list[float], model_name: str)

    Raises:
        requests.RequestException: 网络错误
        ValueError: API 返回错误
    """
    # 优先使用独立 embedding 配置，否则复用 chat 配置
    if model_config.get('embedding_api_url'):
        url = model_config['embedding_api_url'].rstrip('/').rstrip('/embeddings') + '/embeddings'
    else:
        url = f"{model_config['api_base_url'].rstrip('/')}/embeddings"

    api_key = model_config.get('embedding_api_key') or model_config['api_key']

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }

    # embedding 模型名：优先传入 > 独立配置 > 默认
    if embedding_model:
        model_name = embedding_model
    elif model_config.get('embedding_model_name'):
        model_name = model_config['embedding_model_name']
    else:
        model_name = model_config.get('model_name', 'text-embedding-3-small')

    payload = {
        'model': model_name,
        'input': text
    }

    response = requests.post(url, json=payload, headers=headers, timeout=60)
    response.raise_for_status()

    data = response.json()
    embedding = data['data'][0]['embedding']

    return embedding, model_name


def cosine_similarity(vec_a, vec_b):
    """计算两个向量的余弦相似度

    Args:
        vec_a: 向量 A
        vec_b: 向量 B

    Returns:
        float: 余弦相似度 (0-1)
    """
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0

    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot_product / (norm_a * norm_b)


def batch_embed_entries(entries, model_config, embedding_model=None):
    """批量向量化知识条目

    Args:
        entries: KnowledgeEntry 对象列表
        model_config: dict with api_base_url, api_key
        embedding_model: embedding 模型名

    Returns:
        int: 成功向量化的条目数
    """
    count = 0
    model_name = None
    for entry in entries:
        try:
            text = _build_entry_embedding_text(entry)
            vec, model_name = get_embedding(text, model_config, embedding_model)
            entry.embedding = json.dumps(vec)
            entry.embedding_model = model_name or ''
            count += 1
        except Exception:
            continue
    return count


def search_by_embedding(query_text, entries, model_config, embedding_model=None, top_k=5, min_score=0.3):
    """基于向量相似度的语义搜索

    Args:
        query_text: 查询文本
        entries: KnowledgeEntry 对象列表（需已有 embedding）
        model_config: dict with api_base_url, api_key
        embedding_model: embedding 模型名
        top_k: 返回前 K 条
        min_score: 最低相似度阈值，低于此值不返回

    Returns:
        list of (KnowledgeEntry, float): 按相似度降序排列的 (条目, 分数) 列表
    """
    if not entries:
        return []

    try:
        query_vec, _ = get_embedding(query_text, model_config, embedding_model)
    except Exception:
        return []

    scored = []
    for entry in entries:
        if not entry.embedding:
            continue
        try:
            entry_vec = json.loads(entry.embedding)
            sim = cosine_similarity(query_vec, entry_vec)
            if sim >= min_score:
                scored.append((entry, sim))
        except (json.JSONDecodeError, TypeError):
            continue

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k]


def _build_entry_embedding_text(entry):
    """构建用于向量化的条目文本（标题 + 分类 + 内容）"""
    parts = [entry.title]
    if entry.tags:
        try:
            tags = json.loads(entry.tags)
            if tags:
                parts.extend(tags)
        except Exception:
            pass
    parts.append(entry.content or '')
    return ' '.join(parts)
