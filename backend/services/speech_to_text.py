"""
语音转文字服务

使用腾讯云 ASR（录音文件识别）将音频转换为中文文字。
流程：CreateRecTask → 轮询 DescribeTaskStatus → 获取识别结果
"""
import os
import time
import logging

logger = logging.getLogger(__name__)


def _get_asr_client():
    """获取腾讯云 ASR 客户端"""
    from tencentcloud.common import credential
    from tencentcloud.common.profile.client_profile import ClientProfile
    from tencentcloud.common.profile.http_profile import HttpProfile
    from tencentcloud.asr.v20190614 import asr_client

    from config import Config

    secret_id = os.environ.get('TENCENT_SECRET_ID', Config.TENCENT_SECRET_ID)
    secret_key = os.environ.get('TENCENT_SECRET_KEY', Config.TENCENT_SECRET_KEY)

    if not secret_id or not secret_key:
        raise ValueError(
            '未配置腾讯云 API 密钥。请在环境变量中设置 TENCENT_SECRET_ID 和 TENCENT_SECRET_KEY，\n'
            '或在 .env 文件中添加：\n'
            '  TENCENT_SECRET_ID=your_secret_id\n'
            '  TENCENT_SECRET_KEY=your_secret_key\n'
            '获取密钥：https://console.cloud.tencent.com/cam/capi'
        )

    cred = credential.Credential(secret_id, secret_key)
    httpProfile = HttpProfile()
    httpProfile.endpoint = "asr.tencentcloudapi.com"
    clientProfile = ClientProfile()
    clientProfile.httpProfile = httpProfile
    clientProfile.signMethod = "TC3-HMAC-SHA256"

    region = os.environ.get('ASR_REGION', Config.ASR_REGION)
    return asr_client.AsrClient(cred, region, clientProfile)


def _create_recognition_task(audio_file_path):
    """
    创建录音文件识别任务

    对于小文件（≤5MB），直接 base64 上传；大文件需要先上传到 COS 再用 URL 方式。

    Args:
        audio_file_path: 音频文件绝对路径

    Returns:
        int: 任务 ID (task_id)

    Raises:
        Exception: API 调用失败
    """
    from tencentcloud.asr.v20190614 import models
    import base64

    client = _get_asr_client()
    req = models.CreateRecTaskRequest()
    file_size = os.path.getsize(audio_file_path)

    # base64 数据限制为 5MB，超过则使用 URL 方式（需要文件可公网访问）
    if file_size <= 5 * 1024 * 1024:
        # 本地 base64 上传方式（≤5MB）
        with open(audio_file_path, 'rb') as f:
            audio_data = base64.b64encode(f.read()).decode('utf-8')

        params = {"ChannelNum": 1, "ResTextFormat": 0, "SourceType": 1}
        req._deserialize(params)
        req.EngineModelType = "16k_zh"
        req.Data = audio_data
        logger.info(f'ASR: 使用本地 base64 方式上传，文件大小 {file_size / 1024:.1f}KB')
    else:
        # URL 方式（需文件可访问）
        raise ValueError(
            f'音频文件过大（{file_size / 1024 / 1024:.1f}MB），超过 base64 上传限制（5MB）。\n'
            '请先确保压缩后的音频文件小于 5MB，或将音频上传至 COS 后使用 URL 方式。'
        )

    resp = client.CreateRecTask(req)
    result = resp.to_json_string()
    import json
    data = json.loads(result)

    task_id = data.get('Data', {}).get('TaskId')
    if not task_id:
        raise Exception(f'创建识别任务失败：{result}')

    logger.info(f'ASR: 任务创建成功，TaskId={task_id}')
    return int(task_id)


def _poll_task_status(task_id, max_wait_seconds=300, poll_interval=3):
    """
    轮询录音识别任务状态，直到完成或超时

    Args:
        task_id: 任务 ID
        max_wait_seconds: 最长等待时间（秒），默认 5 分钟
        poll_interval: 轮询间隔（秒），默认 3 秒

    Returns:
        dict: 包含识别结果的字典
            {
                'status': int,    # 0=成功, 1=进行中, 2=失败
                'result': str,    # 识别文本（成功时）
                'duration': int,  # 音频时长（秒）
            }

    Raises:
        TimeoutError: 超时
        Exception: 识别失败
    """
    from tencentcloud.asr.v20190614 import models
    import json

    client = _get_asr_client()
    req = models.DescribeTaskStatusRequest()
    req.TaskId = task_id

    elapsed = 0
    while elapsed < max_wait_seconds:
        resp = client.DescribeTaskStatus(req)
        data = json.loads(resp.to_json_string())

        task_data = data.get('Data', {})
        status = task_data.get('Status', 1)

        if status == 2:  # 成功
            result_text = task_data.get('Result', '')
            # 去除开头的时间戳标记 [0:0.000,0:1.230,0]
            result_text = _clean_asr_result(result_text)
            duration = task_data.get('AudioDuration', 0)
            logger.info(f'ASR: 识别完成，文本长度 {len(result_text)} 字符，音频时长 {duration}s')
            return {
                'status': 0,
                'result': result_text,
                'duration': duration
            }
        elif status == 3:  # 失败
            error_msg = task_data.get('ErrorMsg', '未知错误')
            raise Exception(f'语音识别失败：{error_msg}')

        # status == 0 排队中 或 1 进行中
        time.sleep(poll_interval)
        elapsed += poll_interval

    raise TimeoutError(f'语音识别超时（等待 {max_wait_seconds} 秒），TaskId={task_id}')


def _clean_asr_result(text):
    """清理 ASR 返回文本中的时间戳标记"""
    import re
    # 去除形如 [0:0.000,0:1.230,0] 的时间戳标记
    text = re.sub(r'\[\d+:\d+\.\d+,\d+:\d+\.\d+,\d+\]', '', text)
    # 合并连续空行
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def transcribe_audio(audio_file_path):
    """
    高层接口：将音频文件转换为文字

    Args:
        audio_file_path: 音频文件绝对路径（建议 16kHz 单声道 WAV/Opus）

    Returns:
        dict: {
            'success': bool,
            'text': str,         # 转写文本
            'duration': float,   # 音频时长(秒)
            'task_id': int       # ASR 任务 ID
        }

    Raises:
        ValueError: API 密钥未配置
        Exception: 识别失败
    """
    # 创建识别任务
    task_id = _create_recognition_task(audio_file_path)

    # 轮询等待结果
    result = _poll_task_status(task_id, max_wait_seconds=300)

    return {
        'success': True,
        'text': result['result'],
        'duration': float(result.get('duration', 0)),
        'task_id': task_id
    }
