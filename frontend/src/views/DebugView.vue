<template>
  <div class="debug-page">
    <div class="debug-card">
      <h2>🐛 Debug 调试模式</h2>

      <div class="debug-status">
        <div class="status-row">
          <span>当前状态：</span>
          <el-tag :type="debug.isDebugEnabled.value ? 'danger' : 'info'" size="large">
            {{ debug.isDebugEnabled.value ? '🔴 已开启' : '⚪ 已关闭' }}
          </el-tag>
        </div>

        <p class="status-desc" v-if="debug.isDebugEnabled.value">
          调试模式已开启，所有错误将显示完整的堆栈信息和服务器响应。
        </p>
        <p class="status-desc" v-else>
          调试模式已关闭，仅显示简化的错误提示。
        </p>
      </div>

      <div class="debug-actions">
        <el-button
          :type="debug.isDebugEnabled.value ? 'warning' : 'primary'"
          size="large"
          @click="debug.toggle()"
        >
          {{ debug.isDebugEnabled.value ? '关闭调试模式' : '开启调试模式' }}
        </el-button>
      </div>

      <el-divider />

      <div class="debug-info">
        <h4>系统信息</h4>
        <el-descriptions :column="1" border size="small">
          <el-descriptions-item label="前端地址">
            {{ window.location.origin }}
          </el-descriptions-item>
          <el-descriptions-item label="API 代理">
            /api → localhost:5000
          </el-descriptions-item>
          <el-descriptions-item label="User Agent">
            {{ navigator.userAgent }}
          </el-descriptions-item>
        </el-descriptions>

        <div style="margin-top: 20px">
          <h4>后端状态检测</h4>
          <el-button @click="checkBackend" :loading="checking">
            检测后端连接
          </el-button>
          <div v-if="backendStatus" style="margin-top: 10px">
            <el-alert
              :type="backendStatus === 'ok' ? 'success' : 'error'"
              :title="backendStatus === 'ok' ? '后端连接正常' : '后端连接失败'"
              :description="backendMsg"
              show-icon
            />
          </div>
        </div>

        <div style="margin-top: 20px">
          <h4>浏览器控制台</h4>
          <p class="hint-text">
            按 <kbd>F12</kbd> 打开开发者工具 → Console 面板查看详细日志
          </p>
        </div>
      </div>

      <el-divider />

      <div class="debug-footer">
        <el-button @click="$router.push('/')">返回首页</el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useDebug } from '@/utils/debug'

const debug = useDebug()
const checking = ref(false)
const backendStatus = ref(null)
const backendMsg = ref('')

async function checkBackend() {
  checking.value = true
  backendStatus.value = null
  try {
    const res = await fetch('/api/homepage')
    const data = await res.json()
    if (data.code === 0) {
      backendStatus.value = 'ok'
      backendMsg.value = `API 响应正常，首页标题："${data.data.title_text}"`
    } else {
      backendStatus.value = 'error'
      backendMsg.value = 'API 返回异常：' + JSON.stringify(data)
    }
  } catch (err) {
    backendStatus.value = 'error'
    backendMsg.value = '无法连接后端：' + err.message
  } finally {
    checking.value = false
  }
}
</script>

<style scoped>
.debug-page {
  min-height: 100vh;
  background: #f0f2f5;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
}

.debug-card {
  background: #fff;
  border-radius: 16px;
  padding: 40px;
  max-width: 700px;
  width: 100%;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.1);
}

h2 {
  color: #333;
  margin-bottom: 24px;
}

.status-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}

.status-desc {
  font-size: 14px;
  color: #666;
  margin-top: 8px;
}

.debug-actions {
  margin: 24px 0;
}

.debug-info h4 {
  margin-bottom: 12px;
  color: #555;
}

.hint-text {
  font-size: 13px;
  color: #888;
}

kbd {
  background: #eee;
  border: 1px solid #ccc;
  border-radius: 3px;
  padding: 1px 6px;
  font-size: 12px;
}

.debug-footer {
  text-align: center;
}
</style>
