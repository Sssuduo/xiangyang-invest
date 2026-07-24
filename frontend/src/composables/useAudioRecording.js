/**
 * 录音识别 / 转写 / 总结 的共享 composable
 * --------------------------------------------------
 * 以「活动台账」的录音模块为基准抽取，招商动态直接复用，
 * 两端共用同一套状态与操作，避免此前「两份手抄代码、修一边漏一边」的问题。
 *
 * 所有与具体业务相关的接口都通过 opts 注入，composable 本身不耦合任何 api 模块：
 *  - 上传 / 详情 / 重试识别 / 取消 / 删除 / 删单文件
 *  - 多版本拉取 / 开始总结(与 ASR 解耦) / 保存转写 / LLM 模型列表 / docx 下载地址
 *  - 术语校正（接口为两端共用的 /api/admin/term-corrections，直接在此 import）
 *
 * @param {Object} opts
 * @param {Function} opts.getItemId            - () => 当前编辑项 id（ref.value）
 * @param {Function} opts.apiUpload            - (itemId, file, onProgress, appendMode) => Promise
 * @param {Function} opts.apiDetail            - (itemId) => Promise  (返回 {code, data:{audio_files, audio_status, ...}})
 * @param {Function} opts.apiRetry             - (itemId) => Promise  (开始识别)
 * @param {Function} opts.apiCancel            - (itemId) => Promise  (取消处理)
 * @param {Function} opts.apiDelete            - (itemId) => Promise  (删除全部录音)
 * @param {Function} opts.apiDeleteFile        - (itemId, fileIndex) => Promise  (删除单个录音文件)
 * @param {Function} [opts.apiVersions]        - (itemId) => Promise  (拉取结构化多版本：segmented/clean/structured)
 * @param {Function} [opts.apiRetrySummary]    - (itemId, payload|null) => Promise  (仅开始总结)
 * @param {Function} [opts.apiUpdateTranscript]- (itemId, {transcript}) => Promise  (保存转写文本)
 * @param {Function} [opts.apiLLMModels]       - () => Promise  (返回 {code, data:[{id,name}...]})
 * @param {Function} [opts.apiDocxUrl]         - (itemId) => string  (docx 下载地址)
 * @param {Function} [opts.onRefresh]          - () => void  完成后刷新列表（fetchData）
 * @param {Function} [opts.getEditTranscript]  - (detail) => string  回填可编辑转写的字段来源
 * @param {Function} [opts.getEditSummary]     - (detail) => string  回填可编辑总结的字段来源
 * @param {string}   [opts.saveHint]           - 未保存时上传录音的提示文案
 */
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import MarkdownIt from 'markdown-it'
import {
  getTermCorrections, createTermCorrection, deleteTermCorrection, applyTermCorrections,
} from '@/api/activity'

const AUDIO_EXTS = ['wav', 'mp3', 'm4a', 'ogg', 'flac', 'wma', 'aac', 'amr', 'opus', 'webm', 'weba']

export function useAudioRecording(opts) {
  const {
    getItemId,
    apiUpload,
    apiDetail,
    apiRetry,
    apiCancel,
    apiDelete,
    apiDeleteFile,
    apiVersions,
    apiRetrySummary,
    apiUpdateTranscript,
    apiLLMModels,
    apiDocxUrl,
    onRefresh,
    getEditTranscript = (d) => d?.audio_transcript_segmented || d?.audio_transcript || '',
    getEditSummary = (d) => d?.audio_summary_structured || d?.audio_summary || '',
    saveHint = '请先保存后再上传录音文件',
  } = opts

  // ---------- 状态（两端共用） ----------
  const audioUploading = ref(false)
  const audioUploadList = ref([])        // [{ name, progress }]
  const audioLoading = ref(false)
  const audioProcessing = ref(false)
  const audioStatus = ref(null)          // null|processing|asr_processing|summarizing|completed|asr_completed|summary_failed|asr_failed|failed|cancelled
  const audioFiles = ref([])             // [{ name, url, duration, status }]
  const audioDetail = ref(null)
  const audioActiveTab = ref('segmented')

  // 转写 / 总结 可编辑副本 + 脏标记
  const editTranscript = ref('')
  const editSummary = ref('')
  const _originalTranscript = ref('')
  const _originalSummary = ref('')
  const transcriptModified = ref(false)
  const summaryModified = ref(false)

  // LLM 模型选择
  const llmModels = ref([])
  const selectedLlmModel = ref(null)

  // 术语校正
  const termDrawerVisible = ref(false)
  const termCorrections = ref([])
  const termLoading = ref(false)
  const termForm = reactive({ original: '', replacement: '', scope: 'all' })

  // ---------- 轮询 ----------
  let _pollTimer = null

  function stopPolling() {
    if (_pollTimer) { clearInterval(_pollTimer); _pollTimer = null }
  }

  // 模板按钮调用时通常不带 itemId（传入的是事件对象），统一回退到 getItemId()
  function _resolveId(passed) {
    if (passed != null && typeof passed === 'number' && !Number.isNaN(passed)) return passed
    if (typeof passed === 'string' && /^\d+$/.test(String(passed).trim())) return Number(passed)
    return getItemId ? getItemId() : passed
  }

  async function startPolling(itemId) {
    stopPolling()
    if (!itemId) return
    _pollTimer = setInterval(async () => {
      try {
        const res = await apiDetail(itemId)
        if (res.code === 0 && res.data) {
          const status = res.data.audio_status
          if (['completed', 'asr_completed', 'summary_failed', 'asr_failed', 'failed', 'cancelled'].includes(status)) {
            await _onPollComplete(itemId, res.data)
          } else {
            audioDetail.value = res.data
            audioStatus.value = status
          }
        }
      } catch { /* ignore */ }
    }, 3000)
  }

  async function _onPollComplete(itemId, detail) {
    stopPolling()
    audioProcessing.value = false
    audioStatus.value = detail.audio_status
    audioDetail.value = detail

    if (['completed', 'asr_completed', 'summary_failed'].includes(detail.audio_status)) {
      // 拉取结构化多版本
      if (apiVersions) {
        try {
          const vRes = await apiVersions(itemId)
          if (vRes?.code === 0 && vRes.data) audioDetail.value = { ...audioDetail.value, ...vRes.data }
        } catch { /* ignore */ }
      }
      _backfillEdit(audioDetail.value)
      if (detail.audio_status === 'asr_completed') {
        ElMessage.success('转写完成，请点击“开始总结”生成结构化总结')
      } else if (detail.audio_status === 'completed') {
        ElMessage.success('录音转写和总结完成！')
      } else if (detail.audio_status === 'summary_failed') {
        ElMessage.error('结构化总结失败，请检查大模型服务后点击“开始总结”')
      }
    } else if (['asr_failed', 'failed'].includes(detail.audio_status)) {
      ElMessage.error('后台转写失败，可删除后重新上传或点击开始识别')
    }
    onRefresh?.()
  }

  // 回填可编辑副本（加载详情 / 轮询完成时调用）
  function _backfillEdit(detail) {
    if (!detail) return
    const t = getEditTranscript(detail)
    const s = getEditSummary(detail)
    editTranscript.value = t
    editSummary.value = s
    _originalTranscript.value = t
    _originalSummary.value = s
    transcriptModified.value = false
    summaryModified.value = false
  }

  // ---------- 上传队列（串行，确保多文件依次追加，每个文件独立进度） ----------
  const _uploadQueue = []
  let _uploading = false

  async function _processQueue() {
    if (_uploading) return
    _uploading = true
    audioUploading.value = true

    while (_uploadQueue.length > 0) {
      const file = _uploadQueue.shift()
      const itemId = getItemId()
      if (!itemId) continue

      const uploadItem = { name: file.name, progress: 0 }
      audioUploadList.value = [...audioUploadList.value, uploadItem]

      try {
        const appendMode = audioFiles.value.length > 0
        const res = await apiUpload(itemId, file, (progressEvent) => {
          uploadItem.progress = Math.round((progressEvent.loaded / progressEvent.total) * 100)
          audioUploadList.value = [...audioUploadList.value]
        }, appendMode)
        if (res.code === 0) {
          audioFiles.value = res.data.audio_files || []
          audioDetail.value = { audio_transcript: null, audio_summary: null }
          audioStatus.value = 'uploaded'
          audioProcessing.value = false
        } else {
          ElMessage.error(res.message || '录音处理失败')
        }
      } catch (err) {
        ElMessage.error('录音上传失败：' + (err.message || '网络错误'))
      } finally {
        audioUploadList.value = audioUploadList.value.filter(item => item.name !== file.name)
      }
    }

    audioUploading.value = false
    _uploading = false
    const itemId = getItemId()
    if (itemId) {
      startPolling(itemId)
      onRefresh?.()
    }
  }

  function enqueueUpload(file) {
    _uploadQueue.push(file)
    _processQueue()
  }

  // 选择音频文件：校验格式 + 入队（供 el-upload :on-change 调用）
  function selectAudioFile(file) {
    const f = file?.raw || file
    if (!f || !f.name) return
    if (!getItemId()) {
      ElMessage.warning(saveHint)
      return
    }
    const ext = f.name.split('.').pop().toLowerCase()
    if (!AUDIO_EXTS.includes(ext)) {
      ElMessage.error('不支持的音频格式：.' + ext + '，支持：' + AUDIO_EXTS.join(', '))
      return
    }
    stopPolling()
    enqueueUpload(f)
  }

  // ---------- 公开操作 ----------
  async function loadAudioDetail(itemId) {
    if (!itemId) return
    audioLoading.value = true
    try {
      const res = await apiDetail(itemId)
      if (res.code === 0 && res.data) {
        audioFiles.value = res.data.audio_files || []
        audioDetail.value = res.data
        audioStatus.value = res.data.audio_status
        // 回填上次总结使用的模型
        if (!selectedLlmModel.value && res.data.summary_model_id) {
          selectedLlmModel.value = res.data.summary_model_id
        }
        if (['asr_processing', 'summarizing', 'processing'].includes(res.data.audio_status)) {
          audioProcessing.value = true
          startPolling(itemId)
        } else {
          audioProcessing.value = false
          if (apiVersions) {
            try {
              const vRes = await apiVersions(itemId)
              if (vRes?.code === 0 && vRes.data) audioDetail.value = { ...audioDetail.value, ...vRes.data }
            } catch { /* ignore */ }
          }
          _backfillEdit(audioDetail.value)
        }
      } else {
        audioDetail.value = null
        audioFiles.value = []
        audioStatus.value = null
        audioProcessing.value = false
      }
    } catch {
      audioDetail.value = null
      audioFiles.value = []
      audioStatus.value = null
      audioProcessing.value = false
    } finally {
      audioLoading.value = false
    }
  }

  async function retryAudio(itemId) {
    const id = _resolveId(itemId)
    if (!id) return
    stopPolling()
    try {
      const res = await apiRetry(id)
      if (res.code === 0) {
        ElMessage.success('已重新开始语音识别')
        audioStatus.value = 'asr_processing'
        audioProcessing.value = true
        editTranscript.value = ''
        editSummary.value = ''
        _originalTranscript.value = ''
        _originalSummary.value = ''
        transcriptModified.value = false
        summaryModified.value = false
        startPolling(id)
      } else {
        ElMessage.error(res.message || '开始识别失败')
      }
    } catch (err) {
      ElMessage.error('开始识别失败：' + (err.message || '未知错误'))
    }
  }

  async function cancelAudio(itemId) {
    const id = _resolveId(itemId)
    if (!id) return
    stopPolling()
    try {
      await apiCancel(id)
      ElMessage.success('已取消处理')
      audioStatus.value = 'cancelled'
      audioProcessing.value = false
    } catch (err) {
      ElMessage.error('取消失败：' + (err.message || ''))
    }
  }

  async function deleteAudio(itemId) {
    const id = _resolveId(itemId)
    if (!id) return
    stopPolling()
    try {
      const res = await apiDelete(id)
      if (res.code === 0) {
        ElMessage.success('录音已删除')
        audioFiles.value = []
        audioDetail.value = null
        audioStatus.value = null
        audioProcessing.value = false
        audioUploadList.value = []
        onRefresh?.()
      } else {
        ElMessage.error(res.message || '删除失败')
      }
    } catch (err) {
      ElMessage.error('删除失败：' + (err.message || '未知错误'))
    }
  }

  async function deleteAudioFile(fileIndex) {
    const id = getItemId ? getItemId() : null
    if (id == null) return
    try {
      const res = await apiDeleteFile(id, fileIndex)
      if (res.code === 0) {
        audioFiles.value = res.data?.audio_files || []
        if (audioFiles.value.length === 0) {
          audioDetail.value = null
          audioStatus.value = null
          audioProcessing.value = false
        } else {
          await loadAudioDetail(id)
        }
        ElMessage.success('文件已删除')
        onRefresh?.()
      }
    } catch (err) {
      ElMessage.error('删除失败：' + (err.message || '未知错误'))
    }
  }

  // 开始总结（与 ASR 解耦）
  async function retrySummary(itemId) {
    const id = _resolveId(itemId)
    if (!id) return
    const hasTranscript = (audioDetail.value?.audio_transcript && audioDetail.value.audio_transcript.trim()) ||
                          (audioDetail.value?.audio_transcript_segmented && audioDetail.value.audio_transcript_segmented.trim())
    const isCompleted = audioStatus.value === 'completed' || audioStatus.value === 'asr_completed'
    if (!hasTranscript && !isCompleted) {
      ElMessage.warning('没有转写内容，请先完成识别或手动输入转写文本')
      return
    }
    stopPolling()
    try {
      const payload = selectedLlmModel.value ? { model_id: selectedLlmModel.value } : null
      const res = await apiRetrySummary(id, payload)
      if (res.code === 0) {
        ElMessage.success('正在重新生成总结（与 ASR 服务独立）')
        audioStatus.value = 'summarizing'
        audioProcessing.value = true
        startPolling(id)
      } else {
        ElMessage.error(res.message || '操作失败')
      }
    } catch (err) {
      ElMessage.error('请求失败：' + (err.message || ''))
    }
  }

  // 保存转写文本
  async function saveTranscript(itemId) {
    const id = _resolveId(itemId)
    if (!id) return
    try {
      const res = await apiUpdateTranscript(id, { transcript: editTranscript.value })
      if (res.code === 0) {
        ElMessage.success('转写文本已保存')
        _originalTranscript.value = editTranscript.value
        transcriptModified.value = false
        onRefresh?.()
      } else {
        ElMessage.error(res.message || '保存失败')
      }
    } catch (err) {
      ElMessage.error('保存失败：' + (err.message || '未知错误'))
    }
  }

  function watchTranscriptEdit() { transcriptModified.value = editTranscript.value !== _originalTranscript.value }
  function cancelTranscriptEdit() { editTranscript.value = _originalTranscript.value; transcriptModified.value = false }

  // LLM 模型列表
  async function loadLLMModels() {
    if (!apiLLMModels) return
    try {
      const res = await apiLLMModels()
      if (res.code === 0) llmModels.value = res.data || []
    } catch { /* ignore */ }
  }

  // 下载 Word（用 fetch + blob 避免 <a> 包裹 <el-button> 点击穿透）
  async function downloadDocx(itemId, filename) {
    const id = _resolveId(itemId)
    if (!id || !apiDocxUrl) return
    const url = apiDocxUrl(id)
    if (!url) return
    try {
      const res = await fetch(url)
      if (!res.ok) {
        ElMessage.error('文件下载失败，请重新生成总结')
        return
      }
      const blob = await res.blob()
      const objectUrl = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = objectUrl
      a.download = filename || `audio_${id}.docx`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(objectUrl)
    } catch (err) {
      ElMessage.error('下载失败：' + (err.message || ''))
    }
  }

  // ---------- 术语校正（两端共用接口） ----------
  function openTermDrawer() {
    termDrawerVisible.value = true
    loadTermCorrections()
  }
  async function loadTermCorrections() {
    try {
      const res = await getTermCorrections()
      if (res.code === 0) termCorrections.value = res.data || []
    } catch { /* ignore */ }
  }
  async function saveTerm() {
    const { original, replacement, scope } = termForm
    if (!original || !replacement) {
      ElMessage.warning('原文和替换词不能为空')
      return
    }
    try {
      const res = await createTermCorrection({ original, replacement, scope })
      if (res.code === 0) {
        ElMessage.success('已保存')
        termForm.original = ''
        termForm.replacement = ''
        termForm.scope = 'all'
        loadTermCorrections()
      } else {
        ElMessage.error(res.message || '保存失败')
      }
    } catch (err) {
      ElMessage.error('保存失败：' + (err.message || ''))
    }
  }
  async function deleteTerm(id) {
    try {
      await deleteTermCorrection(id)
      ElMessage.success('已删除')
      loadTermCorrections()
    } catch { /* ignore */ }
  }
  async function applyTerms(itemId) {
    const id = _resolveId(itemId)
    if (!id) return
    termLoading.value = true
    try {
      const res = await applyTermCorrections(id)
      if (res.code === 0) {
        ElMessage.success(res.message || '已应用')
        await loadAudioDetail(id)
      } else {
        ElMessage.error(res.message || '应用失败')
      }
    } catch (err) {
      ElMessage.error('应用失败：' + (err.message || ''))
    } finally {
      termLoading.value = false
    }
  }

  // ---------- 纯格式工具（两端共用，消除重复） ----------
  function formatDuration(seconds) {
    if (!seconds) return ''
    const m = Math.floor(seconds / 60)
    const s = Math.floor(seconds % 60)
    return m > 0 ? `${m}分${s}秒` : `${s}秒`
  }
  function formatEstimate(seconds) {
    if (!seconds) return ''
    if (seconds < 60) return `约 ${seconds} 秒`
    return `约 ${Math.ceil(seconds / 60)} 分钟`
  }
  function formatFileSize(bytes) {
    if (!bytes) return ''
    if (bytes < 1024) return bytes + 'B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + 'KB'
    return (bytes / 1024 / 1024).toFixed(1) + 'MB'
  }
  function scopeLabel(scope) {
    return { all: '全部', summary: '摘要版', clean: '清洁版', segmented: '分段原文' }[scope] || scope
  }
  let _md = null
  function renderMd(text) {
    if (!text) return ''
    if (!_md) _md = new MarkdownIt({ html: false, linkify: true, typographer: true, breaks: true })
    try { return _md.render(String(text)) } catch { return String(text).replace(/</g, '&lt;').replace(/>/g, '&gt;') }
  }

  function resetAudio() {
    stopPolling()
    audioUploading.value = false
    audioUploadList.value = []
    audioLoading.value = false
    audioProcessing.value = false
    audioStatus.value = null
    audioFiles.value = []
    audioDetail.value = null
    audioActiveTab.value = 'segmented'
    editTranscript.value = ''
    editSummary.value = ''
    _originalTranscript.value = ''
    _originalSummary.value = ''
    transcriptModified.value = false
    summaryModified.value = false
    termDrawerVisible.value = false
    termCorrections.value = []
    termLoading.value = false
    termForm.original = ''
    termForm.replacement = ''
    termForm.scope = 'all'
  }

  return {
    // 状态
    audioUploading, audioUploadList, audioLoading, audioProcessing,
    audioStatus, audioFiles, audioDetail, audioActiveTab,
    editTranscript, editSummary, transcriptModified, summaryModified,
    llmModels, selectedLlmModel,
    termDrawerVisible, termCorrections, termLoading, termForm,
    // 操作
    selectAudioFile, enqueueUpload, loadAudioDetail, retryAudio, cancelAudio,
    deleteAudio, deleteAudioFile, retrySummary, saveTranscript,
    watchTranscriptEdit, cancelTranscriptEdit, loadLLMModels, downloadDocx,
    openTermDrawer, loadTermCorrections, saveTerm, deleteTerm, applyTerms,
    startPolling, stopPolling, resetAudio,
    // 工具
    formatDuration, formatEstimate, formatFileSize, scopeLabel, renderMd,
  }
}
