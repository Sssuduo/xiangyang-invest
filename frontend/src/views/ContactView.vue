<template>
  <div class="contact-page">
    <!-- ===== 顶部导航栏（复用首页风格） ===== -->
    <header class="top-nav">
      <div class="nav-inner">
        <router-link to="/" class="nav-brand">
          <span class="brand-text">襄阳农高区</span>
        </router-link>
        <nav class="nav-menu">
          <router-link to="/national" class="nav-item">国家农高区</router-link>
          <router-link to="/intro" class="nav-item">襄阳农高区介绍</router-link>
          <router-link to="/toolbox" class="nav-item">招商工具箱</router-link>
          <router-link to="/contact" class="nav-item">联系我们</router-link>
        </nav>
      </div>
    </header>

    <!-- ===== 主体内容 ===== -->
    <div class="contact-body">
      <div class="contact-card-wrapper">
        <!-- 加载中 -->
        <div v-if="loading" class="loading-state">
          <el-icon class="is-loading" :size="32"><Loading /></el-icon>
          <p>加载中...</p>
        </div>

        <!-- 名片卡片 -->
        <div v-else class="business-card">
          <!-- 头像区 -->
          <div class="card-avatar">
            <div class="avatar-placeholder">
              <span>{{ info.name ? info.name.charAt(0) : '联' }}</span>
            </div>
          </div>

          <!-- 姓名 & 职务 -->
          <div class="card-header-text">
            <h2 class="card-name">{{ info.name || '未设置姓名' }}</h2>
            <p class="card-title">{{ info.title || '未设置职务' }}</p>
          </div>

          <div class="card-divider" />

          <!-- 联系方式 -->
          <div class="card-contact">
            <div v-if="info.phone" class="contact-row">
              <span class="contact-icon">📞</span>
              <span class="contact-text">{{ info.phone }}</span>
            </div>
            <div v-if="info.email" class="contact-row">
              <span class="contact-icon">📧</span>
              <span class="contact-text">{{ info.email }}</span>
            </div>
          </div>

          <!-- 个人介绍 -->
          <div v-if="info.intro" class="card-intro">
            <p>{{ info.intro }}</p>
          </div>

          <!-- 微信二维码 -->
          <div v-if="info.wechat_qr_image" class="card-qr">
            <div class="qr-label">微信扫码联系</div>
            <img :src="info.wechat_qr_image" class="qr-image" alt="微信二维码" />
          </div>

          <!-- 空状态 -->
          <div v-if="isEmpty" class="card-empty">
            <p>👋 暂未配置联系信息</p>
            <p class="empty-hint">请管理员在后台设置</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Loading } from '@element-plus/icons-vue'
import { getContactInfo } from '@/api/contact'

const info = ref({
  name: '',
  title: '',
  phone: '',
  email: '',
  intro: '',
  wechat_qr_image: ''
})
const loading = ref(true)

const isEmpty = computed(() => {
  return !info.value.name && !info.value.title && !info.value.phone &&
         !info.value.email && !info.value.intro && !info.value.wechat_qr_image
})

onMounted(async () => {
  try {
    const res = await getContactInfo()
    if (res.code === 0 && res.data) {
      info.value = res.data
    }
  } catch { /* fallback */ } finally {
    loading.value = false
  }
})
</script>

<style scoped>
/* ============================================================
   整体
   ============================================================ */
.contact-page {
  width: 100vw; min-height: 100vh;
  background: linear-gradient(160deg, #f5f7fa 0%, #e8ecf1 40%, #dce2e8 100%);
  font-family: 'PingFang SC', 'Microsoft YaHei', 'Helvetica Neue', sans-serif;
  display: flex; flex-direction: column;
}

/* ============================================================
   顶部导航栏
   ============================================================ */
.top-nav {
  position: fixed; top: 0; left: 0; right: 0; z-index: 1000;
  padding: 0 48px; height: 72px;
  display: flex; align-items: center;
  background: rgba(255,255,255,0.85);
  backdrop-filter: saturate(180%) blur(20px);
  -webkit-backdrop-filter: saturate(180%) blur(20px);
  box-shadow: 0 1px 0 rgba(0,0,0,0.06);
}
.nav-inner {
  width: 100%; max-width: 1280px; margin: 0 auto;
  display: flex; align-items: center; justify-content: space-between;
}
.nav-brand { text-decoration: none; font-size: 22px; font-weight: 700; letter-spacing: 3px; }
.brand-text {
  background: linear-gradient(90deg, #1a3a5c, #2a5a8c);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  background-clip: text;
}
.nav-menu { display: flex; gap: 40px; align-items: center; }
.nav-item {
  text-decoration: none; color: #4a5568; font-size: 15px;
  font-weight: 400; letter-spacing: 1px; padding: 6px 0;
  position: relative; transition: color 0.3s;
}
.nav-item::after {
  content: ''; position: absolute; bottom: 0; left: 0; width: 0; height: 2px;
  background: #1a3a5c; border-radius: 1px;
  transition: width 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}
.nav-item:hover { color: #1a3a5c; }
.nav-item:hover::after { width: 100%; }
.nav-item.router-link-active { color: #1a3a5c; font-weight: 600; }
.nav-item.router-link-active::after { width: 100%; }

/* ============================================================
   主体内容
   ============================================================ */
.contact-body {
  flex: 1; display: flex; align-items: center; justify-content: center;
  padding: 120px 32px 64px;
}
.contact-card-wrapper { width: 100%; max-width: 480px; }

/* ============================================================
   名片卡片
   ============================================================ */
.business-card {
  background: #fff; border-radius: 20px;
  padding: 48px 40px 40px;
  box-shadow: 0 2px 24px rgba(0,0,0,0.06), 0 8px 48px rgba(0,0,0,0.04);
  display: flex; flex-direction: column; align-items: center;
  text-align: center;
  animation: cardIn 0.7s cubic-bezier(0.16, 1, 0.3, 1);
}

/* 头像 */
.card-avatar { margin-bottom: 20px; }
.avatar-placeholder {
  width: 88px; height: 88px; border-radius: 50%;
  background: linear-gradient(135deg, #1a3a5c 0%, #2a5a8c 100%);
  display: flex; align-items: center; justify-content: center;
  color: #fff; font-size: 36px; font-weight: 700;
  box-shadow: 0 4px 16px rgba(26,58,92,0.3);
}

/* 姓名 & 职务 */
.card-header-text { margin-bottom: 0; }
.card-name {
  font-size: 26px; font-weight: 700; color: #1a202c;
  letter-spacing: 2px; margin-bottom: 6px;
}
.card-title {
  font-size: 14px; color: #718096; letter-spacing: 1px;
  font-weight: 400;
}

/* 分割线 */
.card-divider {
  width: 48px; height: 2px;
  background: linear-gradient(90deg, #cbd5e0, #1a3a5c, #cbd5e0);
  margin: 24px 0; border-radius: 1px;
}

/* 联系方式 */
.card-contact {
  width: 100%; margin-bottom: 20px;
}
.contact-row {
  display: flex; align-items: center; justify-content: center;
  gap: 10px; margin-bottom: 10px;
}
.contact-icon { font-size: 16px; }
.contact-text { font-size: 15px; color: #4a5568; letter-spacing: 0.5px; }

/* 个人介绍 */
.card-intro {
  width: 100%; background: #f7f8fa; border-radius: 12px;
  padding: 18px 20px; margin-bottom: 24px;
}
.card-intro p {
  font-size: 14px; color: #4a5568; line-height: 1.8;
  margin: 0; text-align: left;
}

/* 微信二维码 */
.card-qr {
  display: flex; flex-direction: column; align-items: center;
  gap: 12px;
}
.qr-label {
  font-size: 13px; color: #a0aec0; letter-spacing: 1px;
}
.qr-image {
  width: 160px; height: 160px; object-fit: contain;
  border-radius: 12px; border: 1px solid #e2e8f0;
  padding: 8px; background: #fff;
}

/* 空状态 */
.card-empty { padding: 32px 0 8px; }
.card-empty p { font-size: 16px; color: #a0aec0; margin-bottom: 6px; }
.empty-hint { font-size: 13px !important; }

/* Loading */
.loading-state {
  display: flex; flex-direction: column; align-items: center; gap: 16px;
  color: #718096; padding: 64px 0;
}

/* 动画 */
@keyframes cardIn {
  from { opacity: 0; transform: translateY(32px); }
  to   { opacity: 1; transform: translateY(0); }
}
</style>
