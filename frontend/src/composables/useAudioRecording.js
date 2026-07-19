/**
 * 录音识别总结的可复用 composable
 * 用于活动台账 / 招商动态等页面，提供：
 *  - 录音文件上传（串行队列 + 每个文件独立进度）
 *  - 转写状态轮询
 *  - 人工重试、取消、删除
 *  - 转写/总结内容展示
 *
 * @param {Object} opts
 * @param {Function} opts.getItemId - 获取当前编辑项 ID 的函数
 * @param {Function} opts.apiUpload - (itemId, file, onProgress, appendMode) => Promise
 * @param {Function} opts.apiDetail - (itemId) => Promise
 * @param {Function} opts.apiRetry - (itemId) => Promise
 * @param {Function} opts.apiCancel - (itemId) => Promise
 * @param {Function} opts.apiDelete - (itemId) => Promise
 * @param {Function} opts.apiDeleteFile - (itemId, fileIndex) => Promise
 */
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

export function useAudioRecording(opts) {
  const {
    getItemId,
    apiUpload,
    apiDetail,
    apiRetry,
    apiCancel,
    apiDelete,
    apiDeleteFile,
  } = opts

  // ---- 状态 ----
  const audioUploading = ref(false)
  const audioUploadList = ref([])   // [{ name, progress }]
  const audioLoading = ref(false)
  const audioProcessing = ref(false)
  const audioStatus = ref(null)
  const audioFiles = ref([])
  const audioDetail = ref(null)

  // ---- 轮询 ----
  let _pollTimer = null

  function stopPolling() {
    if (_pollTimer) { clearInterval(_pollTimer); _pollTimer = null }
  }

  async function startPolling(itemId) {
    stopPolling()
    if (!itemId) return
    _pollTimer = setInterval(async () => {
      try {
        const res = await apiDetail(itemId)
        if (res.code === 0 && res.data) {
          audioDetail.value = res.data
          audioFiles.value = res.data.audio_files || []
          audioStatus.value = res.data.audio_status
          if (['completed', 'summary_failed', 'asr_failed', 'failed', 'cancelled', 'asr_completed'].includes(res.data.audio_status)) {
            stopPolling()
            audioProcessing.value = false
          }
        }
      } catch { /* ignore */ }
    }, 3000)
  }

  // ---- 上传队列（串行，确保多文件依次追加） ----
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
          audioStatus.value = 'processing'
          audioProcessing.value = true
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
    if (itemId) startPolling(itemId)
  }

  function enqueueUpload(file) {
    _uploadQueue.push(file)
    _processQueue()
  }

  // ---- 公开操作 ----
  async function loadAudioDetail(itemId) {
    if (!itemId) return
    audioLoading.value = true
    try {
      const res = await apiDetail(itemId)
      if (res.code === 0 && res.data) {
        audioFiles.value = res.data.audio_files || []
        audioDetail.value = res.data
        audioStatus.value = res.data.audio_status
        if (['asr_processing', 'summarizing', 'processing'].includes(res.data.audio_status)) {
          audioProcessing.value = true
          startPolling(itemId)
        } else {
          audioProcessing.value = false
        }
      }
    } catch {
      audioDetail.value = null
    } finally {
      audioLoading.value = false
    }
  }

  async function retryAudio(itemId) {
    if (!itemId) return
    stopPolling()
    try {
      const res = await apiRetry(itemId)
      if (res.code === 0) {
        audioStatus.value = 'asr_processing'  // 对齐后端状态，确保前端显示'正在识别...'而非'正在总结...'
        audioProcessing.value = true
        startPolling(itemId)
      } else {
        // 后端返回业务错误（如 503 ASR 不可用）→ 抛出给调用方显示友好提示
        throw new Error(res.message || '操作失败')
      }
    } catch (e) {
      // 网络错误或业务错误都向上抛出，由调用方（ActivityView.handleRetryAudio）捕获并 ElMessage 提示
      throw e
    }
  }

  async function cancelAudio(itemId) {
    if (!itemId) return
    stopPolling()
    try {
      await apiCancel(itemId)
      audioStatus.value = 'cancelled'
      audioProcessing.value = false
    } catch { /* ignore */ }
  }

  async function deleteAudio(itemId) {
    if (!itemId) return
    stopPolling()
    try {
      await apiDelete(itemId)
      audioFiles.value = []
      audioDetail.value = null
      audioStatus.value = null
      audioProcessing.value = false
      audioUploadList.value = []
    } catch { /* ignore */ }
  }

  async function deleteAudioFile(itemId, fileIndex) {
    if (!itemId) return
    try {
      const res = await apiDeleteFile(itemId, fileIndex)
      if (res.code === 0) {
        audioFiles.value = res.data?.audio_files || []
      }
    } catch { /* ignore */ }
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
  }

  return {
    audioUploading, audioUploadList, audioLoading, audioProcessing,
    audioStatus, audioFiles, audioDetail,
    enqueueUpload, loadAudioDetail, retryAudio, cancelAudio,
    deleteAudio, deleteAudioFile, startPolling, stopPolling, resetAudio,
  }
}
