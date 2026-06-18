<template>
  <div class="homepage" :style="bgStyle">
    <div class="homepage-overlay">
      <div class="homepage-content">
        <h1 class="homepage-title">{{ config.title_text || '襄阳农高区' }}</h1>
        <p class="homepage-subtitle">{{ config.subtitle_text || '招商服务一站式平台' }}</p>
        <div class="homepage-buttons">
          <el-button
            class="homepage-btn"
            size="large"
            @click="$router.push('/intro')"
          >
            {{ config.button1_text || '襄阳农高区介绍' }}
          </el-button>
          <el-button
            class="homepage-btn"
            size="large"
            @click="$router.push('/toolbox')"
          >
            {{ config.button2_text || '招商工具箱' }}
          </el-button>
        </div>
      </div>
      <footer class="homepage-footer">
        <router-link to="/admin/login" class="admin-link">管理入口</router-link>
      </footer>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getHomepageConfig } from '@/api/homepage'

const config = ref({
  background_image: '',
  title_text: '襄阳农高区',
  subtitle_text: '招商服务一站式平台',
  button1_text: '襄阳农高区介绍',
  button2_text: '招商工具箱'
})

const bgStyle = computed(() => {
  if (config.value.background_image) {
    return {
      backgroundImage: `url(${config.value.background_image})`,
      backgroundSize: 'cover',
      backgroundPosition: 'center',
      backgroundRepeat: 'no-repeat'
    }
  }
  return {
    background: 'linear-gradient(135deg, #1a3a5c 0%, #2a5a8c 50%, #0d2137 100%)'
  }
})

onMounted(async () => {
  try {
    const res = await getHomepageConfig()
    if (res.code === 0 && res.data) {
      config.value = res.data
    }
  } catch {
    // 使用默认配置
  }
})
</script>

<style scoped>
.homepage {
  width: 100vw;
  height: 100vh;
  position: relative;
  overflow: hidden;
}

.homepage-overlay {
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.35);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.homepage-content {
  text-align: center;
  color: #fff;
  animation: fadeInUp 1s ease;
}

.homepage-title {
  font-size: 56px;
  font-weight: 700;
  letter-spacing: 8px;
  margin-bottom: 16px;
  text-shadow: 0 2px 12px rgba(0, 0, 0, 0.3);
}

.homepage-subtitle {
  font-size: 20px;
  font-weight: 300;
  letter-spacing: 4px;
  margin-bottom: 60px;
  opacity: 0.9;
  text-shadow: 0 1px 6px rgba(0, 0, 0, 0.2);
}

.homepage-buttons {
  display: flex;
  gap: 32px;
  justify-content: center;
}

.homepage-btn {
  padding: 18px 48px !important;
  font-size: 18px !important;
  border-radius: 8px !important;
  letter-spacing: 2px;
  transition: all 0.3s ease;
  border: 2px solid rgba(255, 255, 255, 0.6) !important;
  background: rgba(255, 255, 255, 0.1) !important;
  color: #fff !important;
  backdrop-filter: blur(4px);
}

.homepage-btn:hover {
  background: rgba(255, 255, 255, 0.25) !important;
  border-color: #fff !important;
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
}

.homepage-footer {
  position: absolute;
  bottom: 32px;
  right: 40px;
}

.admin-link {
  color: rgba(255, 255, 255, 0.4);
  font-size: 13px;
  transition: color 0.3s;
}
.admin-link:hover {
  color: rgba(255, 255, 255, 0.8);
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
