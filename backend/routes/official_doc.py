"""
公文写作 API 路由
"""
import json
import os
import re

from flask import request, jsonify, session, current_app, send_file, abort
from werkzeug.utils import safe_join

from models import LLMModel
from models.official_doc import OfficialDocTemplate
from extensions import db
from routes import api_bp
from routes.business_auth import business_login_required
from services.llm_service import call_llm
from services.official_doc_rules import (
    build_outline_system_prompt,
    build_outline_user_prompt,
    build_document_system_prompt,
    build_document_user_prompt
)


def current_user_id():
    """获取当前用户ID"""
    return session.get('business_user_id')


# ============================================================
# 模板（范本）管理
# ============================================================
@api_bp.route('/official-doc/templates', methods=['GET'])
@business_login_required
def list_official_doc_templates():
    """获取公文模板列表（非删除）"""
    templates = OfficialDocTemplate.query.filter_by(is_deleted=False) \
        .order_by(OfficialDocTemplate.created_at.desc()).all()
    return jsonify({'code': 0, 'data': [t.to_dict() for t in templates]})


@api_bp.route('/official-doc/templates', methods=['POST'])
@business_login_required
def upload_official_doc_template():
    """上传公文模板（范本）"""
    if 'file' not in request.files:
        return jsonify({'code': 1, 'message': '请选择文件'}), 400

    file = request.files['file']
    name = request.form.get('name', '').strip()
    doc_type = request.form.get('doc_type', '').strip()

    if not file or not name:
        return jsonify({'code': 1, 'message': '参数不完整'}), 400

    # 读取文件内容
    try:
        content = read_uploaded_file(file)
    except ValueError as e:
        return jsonify({'code': 1, 'message': str(e)}), 400

    # 解析结构
    structure = parse_document_structure(content, doc_type)

    template = OfficialDocTemplate(
        name=name,
        doc_type=doc_type,
        content=content,
        structure=structure,
        file_name=file.filename,
        file_size=len(content),
        created_by=current_user_id()
    )
    db.session.add(template)
    db.session.commit()

    return jsonify({
        'code': 0,
        'data': template.to_dict(),
        'message': '上传成功'
    })


@api_bp.route('/official-doc/templates/<int:template_id>', methods=['DELETE'])
@business_login_required
def delete_official_doc_template(template_id):
    """删除公文模板"""
    template = OfficialDocTemplate.query.get_or_404(template_id)

    # 只能删除自己创建的模板
    if template.created_by != current_user_id():
        return jsonify({'code': 1, 'message': '无权删除'}), 403

    template.is_deleted = True
    db.session.commit()

    return jsonify({'code': 0, 'message': '删除成功'})


# ============================================================
# 素材上传
# ============================================================
@api_bp.route('/official-doc/upload-material', methods=['POST'])
@business_login_required
def upload_material():
    """上传素材文件"""
    if 'file' not in request.files:
        return jsonify({'code': 1, 'message': '请选择文件'}), 400

    file = request.files['file']

    try:
        content = read_uploaded_file(file)
    except ValueError as e:
        return jsonify({'code': 1, 'message': str(e)}), 400

    # 提取标题（第一行）
    title = ''
    lines = content.strip().split('\n')
    if lines:
        title = lines[0].strip().lstrip('#').strip()

    return jsonify({
        'code': 0,
        'data': {
            'content': content,
            'title': title,
            'file_name': file.filename
        }
    })


# ============================================================
# 生成提纲
# ============================================================
@api_bp.route('/official-doc/generate-outline', methods=['POST'])
@business_login_required
def generate_outline():
    """生成公文提纲（提示词由服务端按规则组装）"""
    data = request.get_json(silent=True) or {}

    model_id = data.get('model_id')
    doc_type = data.get('doc_type', '')
    style_config = data.get('style_config') or {}
    material = data.get('material') or {}
    projects_text = (data.get('projects_text') or '').strip()
    template_content = (data.get('template_content') or '').strip()

    if not model_id:
        return jsonify({'code': 1, 'message': '请选择模型'}), 400

    model = LLMModel.query.get(model_id)
    if not model or not model.is_active:
        return jsonify({'code': 1, 'message': '模型不存在或已禁用'}), 400

    system_prompt = build_outline_system_prompt(doc_type, style_config)
    user_prompt = build_outline_user_prompt(material, projects_text, template_content)

    messages = [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': user_prompt}
    ]

    try:
        result = call_llm(
            model_config={
                'api_base_url': model.api_base_url,
                'api_key': model.api_key,
                'model_name': model.model_name,
                'provider': model.provider
            },
            messages=messages,
            temperature=0.5,
            max_tokens=4096
        )

        outline = parse_outline_result(result)

        return jsonify({
            'code': 0,
            'data': {'outline': outline}
        })
    except ValueError as e:
        return jsonify({'code': 1, 'message': f'生成失败：{str(e)}'}), 500
    except Exception as e:
        return jsonify({'code': 1, 'message': f'生成失败：{str(e)}'}), 500


# ============================================================
# 生成成文
# ============================================================
@api_bp.route('/official-doc/generate-document', methods=['POST'])
@business_login_required
def generate_document():
    """生成公文成文（提示词由服务端按规则组装）"""
    data = request.get_json(silent=True) or {}

    model_id = data.get('model_id')
    doc_type = data.get('doc_type', '')
    style_config = data.get('style_config') or {}
    material = data.get('material') or {}
    projects_text = (data.get('projects_text') or '').strip()
    template_content = (data.get('template_content') or '').strip()
    outline = data.get('outline') or []

    if not model_id:
        return jsonify({'code': 1, 'message': '请选择模型'}), 400

    model = LLMModel.query.get(model_id)
    if not model or not model.is_active:
        return jsonify({'code': 1, 'message': '模型不存在或已禁用'}), 400

    system_prompt = build_document_system_prompt(doc_type, style_config)
    outline_text = json.dumps(outline, ensure_ascii=False, indent=2) if outline else ''
    user_prompt = build_document_user_prompt(outline_text, material, projects_text, template_content)

    messages = [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': user_prompt}
    ]

    try:
        result = call_llm(
            model_config={
                'api_base_url': model.api_base_url,
                'api_key': model.api_key,
                'model_name': model.model_name,
                'provider': model.provider
            },
            messages=messages,
            temperature=0.5,
            max_tokens=8000
        )

        return jsonify({
            'code': 0,
            'data': {'document': result}
        })
    except Exception as e:
        return jsonify({'code': 1, 'message': f'生成失败：{str(e)}'}), 500


# ============================================================
# 下载文档
# ============================================================
@api_bp.route('/official-doc/download-word', methods=['POST'])
@business_login_required
def download_word():
    """生成并下载 Word 文档"""
    data = request.get_json(silent=True) or {}
    content = data.get('content', '')
    title = data.get('title', '公文文档')

    if not content:
        return jsonify({'code': 1, 'message': '内容不能为空'}), 400

    try:
        from services.docx_service import generate_docx
        filename = generate_docx(content, title)
        return jsonify({
            'code': 0,
            'data': {'download_url': f'/official-doc/file/{filename}'}
        })
    except Exception as e:
        return jsonify({'code': 1, 'message': f'生成失败：{str(e)}'}), 500


@api_bp.route('/official-doc/file/<filename>', methods=['GET'])
@business_login_required
def serve_official_doc_file(filename):
    """签发生成的 .docx 文件（防目录穿越）"""
    base = os.path.join(current_app.instance_path, 'generated_docs')
    path = safe_join(base, filename)
    if not path or not os.path.isfile(path):
        abort(404)
    return send_file(path, as_attachment=True, mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')


# ============================================================
# 辅助函数
# ============================================================
def read_uploaded_file(file):
    """读取上传文件内容"""
    filename = (file.filename or '').lower()

    if filename.endswith('.txt') or filename.endswith('.md'):
        return file.read().decode('utf-8')
    elif filename.endswith('.docx'):
        try:
            from docx import Document
            doc = Document(file)
            return '\n'.join([p.text for p in doc.paragraphs])
        except ImportError:
            raise ValueError('服务器未安装 python-docx，无法解析 .docx 文件')
    elif filename.endswith('.doc'):
        raise ValueError('不支持 .doc 格式，请转换为 .docx')
    else:
        raise ValueError('不支持的文件格式')


def parse_document_structure(content, doc_type):
    """解析文档结构（提取标题层级，用于范本骨架预览）"""
    structure = []
    lines = content.split('\n')

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if re.match(r'^[一二三四五六七八九十]、', line) or re.match(r'^#+\s', line):
            structure.append({'level': 1, 'title': line.lstrip('#').strip()})
        elif re.match(r'^（[一二三四五六七八九十]+）', line):
            structure.append({'level': 2, 'title': line})
        elif re.match(r'^\d+[\.、]', line):
            structure.append({'level': 3, 'title': line})

    return json.dumps(structure, ensure_ascii=False)


def parse_outline_result(result):
    """解析模型返回的提纲 JSON；无法解析时抛出错误（避免静默兜底掩盖异常）"""
    if not result:
        raise ValueError('模型返回为空')

    # 尝试直接解析 JSON
    try:
        parsed = json.loads(result)
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        pass

    # 尝试从 Markdown 代码块中提取
    match = re.search(r'```json\s*([\s\S]*?)\s*```', result)
    if match:
        try:
            parsed = json.loads(match.group(1))
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass

    # 尝试从纯文本中提取
    match = re.search(r'\[[\s\S]*\]', result)
    if match:
        try:
            parsed = json.loads(match.group(0))
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass

    raise ValueError('模型未返回可解析的提纲 JSON，请重新生成')
