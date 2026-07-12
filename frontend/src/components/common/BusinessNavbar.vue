<template>
  <header class="top-nav" :class="[navClass, { scrolled: props.scrolled }]">
    <div class="nav-inner">
      <router-link to="/" class="nav-brand">
        <span class="brand-text">襄阳农高区</span>
      </router-link>
      <nav class="nav-menu">
        <router-link to="/national" class="nav-item" active-class="active-item">国家农高区</router-link>
        <router-link to="/promo-video" class="nav-item" active-class="active-item">招商宣传视频</router-link>
        <!-- <router-link to="/intro" class="nav-item" active-class="active-item">襄阳农高区介绍</router-link> -->
        <!-- 招商项目库 下拉菜单 — 仅登录后可见 -->
        <el-dropdown v-if="businessAuth.isLoggedIn" trigger="hover" class="nav-dropdown" @command="handleCommand">
          <span class="nav-item nav-dropdown-trigger" :class="{ 'is-active': isInvestmentRoute }">
            招商项目库
            <el-icon class="dropdown-arrow"><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="/investment-dashboard">数据看板</el-dropdown-item>
              <el-dropdown-item command="/investment">招商项目管理</el-dropdown-item>
              <el-dropdown-item command="/investment-activity">招商动态管理</el-dropdown-item>
              <el-dropdown-item command="/investment-demand">企业诉求管理</el-dropdown-item>
              <el-dropdown-item command="/investment-activity-ledger">活动台账管理</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <!-- 在建项目库 下拉菜单 — 仅登录后可见 -->
        <el-dropdown v-if="businessAuth.isLoggedIn" trigger="hover" class="nav-dropdown" @command="handleCommand">
          <span class="nav-item nav-dropdown-trigger" :class="{ 'is-active': isConstructionRoute }">
            在建项目库
            <el-icon class="dropdown-arrow"><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="/construction-dashboard">数据看板</el-dropdown-item>
              <el-dropdown-item command="/construction">在建项目管理</el-dropdown-item>
              <el-dropdown-item command="/construction-progress">工作进展管理</el-dropdown-item>
              <el-dropdown-item command="/construction-issues">调度问题管理</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <!-- AI 工具箱 下拉菜单 — 仅登录后可见 -->
        <el-dropdown v-if="businessAuth.isLoggedIn" trigger="hover" class="nav-dropdown" @command="handleCommand">
          <span class="nav-item nav-dropdown-trigger" :class="{ 'is-active': isToolboxRoute }">
            AI 工具箱
            <el-icon class="dropdown-arrow"><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="/lead">招商线索研判</el-dropdown-item>
              <el-dropdown-item command="/knowledge">本地招商知识库</el-dropdown-item>
              <el-dropdown-item command="/knowledge/drafts">知识沉淀审核</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <router-link to="/contact" class="nav-item" active-class="active-item">联系我们</router-link>
        <!-- 登录 / 用户信息 -->
        <template v-if="businessAuth.isLoggedIn">
          <span class="nav-item nav-user nav-user-clickable" @click="showProfileDialog = true">
            <el-icon><UserFilled /></el-icon>
            {{ businessAuth.user?.display_name || businessAuth.user?.username }}
            <el-tag v-if="businessAuth.isVisitor" size="small" type="warning" effect="plain" style="margin-left: 6px;">访客</el-tag>
          </span>
          <span class="nav-item nav-logout" @click="handleLogout">退出</span>
        </template>
        <span v-else class="nav-item nav-login" @click="showLoginDialog = true">登录</span>
      </nav>
    </div>
  </header>

  <!-- 登录弹窗 -->
  <el-dialog
    v-model="showLoginDialog"
    title="用户登录"
    width="400px"
    :close-on-click-modal="false"
    append-to-body
  >
    <el-form ref="loginFormRef" :model="loginForm" :rules="loginRules" label-position="top" @submit.prevent="handleLogin">
      <el-form-item label="用户名" prop="username">
        <el-input v-model="loginForm.username" placeholder="请输入用户名" :prefix-icon="User" />
      </el-form-item>
      <el-form-item label="密码" prop="password">
        <el-input v-model="loginForm.password" type="password" placeholder="请输入密码" show-password :prefix-icon="Lock" @keyup.enter="handleLogin" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="loginLoading" style="width: 100%" @click="handleLogin">
          登 录
        </el-button>
      </el-form-item>
      <p v-if="loginError" class="login-error">{{ loginError }}</p>
    </el-form>
  </el-dialog>

  <!-- 个人资料弹窗 -->
  <el-dialog
    v-model="showProfileDialog"
    title="个人资料"
    width="450px"
    :close-on-click-modal="false"
    append-to-body
  >
    <el-tabs v-model="profileTab">
      <el-tab-pane label="修改显示名称" name="display">
        <el-form ref="profileFormRef" :model="profileForm" :rules="profileRules" label-position="top">
          <el-form-item label="显示名称" prop="display_name">
            <el-input v-model="profileForm.display_name" placeholder="请输入新的显示名称" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="profileLoading" @click="handleUpdateProfile">保存</el-button>
          </el-form-item>
          <p v-if="profileError" class="login-error">{{ profileError }}</p>
          <p v-if="profileSuccess" class="profile-success">{{ profileSuccess }}</p>
        </el-form>
      </el-tab-pane>
      <el-tab-pane label="修改密码" name="password">
        <el-form ref="passwordFormRef" :model="passwordForm" :rules="passwordRules" label-position="top">
          <el-form-item label="原密码" prop="old_password">
            <el-input v-model="passwordForm.old_password" type="password" placeholder="请输入原密码" show-password />
          </el-form-item>
          <el-form-item label="新密码" prop="new_password">
            <el-input v-model="passwordForm.new_password" type="password" placeholder="请输入新密码（至少6位）" show-password />
          </el-form-item>
          <el-form-item label="确认新密码" prop="confirm_password">
            <el-input v-model="passwordForm.confirm_password" type="password" placeholder="请再次输入新密码" show-password />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="passwordLoading" @click="handleChangePassword">修改密码</el-button>
          </el-form-item>
          <p v-if="passwordError" class="login-error">{{ passwordError }}</p>
        </el-form>
      </el-tab-pane>
    </el-tabs>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowDown, UserFilled, User, Lock } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useBusinessAuthStore } from '@/stores/businessAuth'
import { clearAuthCache } from '@/router'

const props = defineProps({
  variant: { type: String, default: 'light' }, // 'home' | 'light' | 'overlay' | 'contact'
  scrolled: { type: Boolean, default: false }
})

const route = useRoute()
const router = useRouter()
const businessAuth = useBusinessAuthStore()

const isInvestmentRoute = computed(() => route.path.startsWith('/investment'))
const isConstructionRoute = computed(() => route.path.startsWith('/construction'))
const isToolboxRoute = computed(() => route.path.startsWith('/lead') || route.path.startsWith('/knowledge'))

function handleCommand(path) {
  if (route.path !== path) {
    router.push(path)
  }
}

const navClass = computed(() => `nav-${props.variant}`)

// ===== 登录弹窗 =====
const showLoginDialog = ref(false)
const loginLoading = ref(false)
const loginError = ref('')
const loginFormRef = ref(null)
const loginForm = ref({
  username: '',
  password: ''
})
const loginRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

// 检查登录状态
onMounted(() => {
  businessAuth.check()
})

async function handleLogin() {
  if (!loginFormRef.value) return
  try {
    await loginFormRef.value.validate()
  } catch {
    return
  }

  loginLoading.value = true
  loginError.value = ''
  const result = await businessAuth.login(loginForm.value.username, loginForm.value.password)
  loginLoading.value = false

  if (result.success) {
    showLoginDialog.value = false
    loginForm.value = { username: '', password: '' }
    clearAuthCache()
    ElMessage.success('登录成功')
  } else {
    loginError.value = result.message || '登录失败'
  }
}

async function handleLogout() {
  await businessAuth.logout()
  clearAuthCache()
  ElMessage.success('已退出登录')
  // 如果在需要登录的页面，跳回首页
  if (route.meta.requiresBusinessAuth) {
    router.push('/')
  }
}

// ===== 个人资料弹窗 =====
const showProfileDialog = ref(false)
const profileTab = ref('display')
const profileLoading = ref(false)
const passwordLoading = ref(false)
const profileError = ref('')
const profileSuccess = ref('')
const passwordError = ref('')
const profileFormRef = ref(null)
const passwordFormRef = ref(null)
const profileForm = ref({ display_name: '' })
const passwordForm = ref({ old_password: '', new_password: '', confirm_password: '' })

const profileRules = {
  display_name: [{ required: true, message: '请输入显示名称', trigger: 'blur' }]
}

const validateConfirmPassword = (rule, value, callback) => {
  if (value !== passwordForm.value.new_password) {
    callback(new Error('两次输入的新密码不一致'))
  } else {
    callback()
  }
}

const passwordRules = {
  old_password: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '新密码至少6位', trigger: 'blur' }
  ],
  confirm_password: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' }
  ]
}

watch(showProfileDialog, (val) => {
  if (val) {
    profileForm.value.display_name = businessAuth.user?.display_name || ''
    profileError.value = ''
    profileSuccess.value = ''
    passwordError.value = ''
    passwordForm.value = { old_password: '', new_password: '', confirm_password: '' }
    profileTab.value = 'display'
  }
})

async function handleUpdateProfile() {
  if (!profileFormRef.value) return
  try { await profileFormRef.value.validate() } catch { return }
  profileLoading.value = true
  profileError.value = ''
  profileSuccess.value = ''
  const result = await businessAuth.updateProfile(profileForm.value.display_name)
  profileLoading.value = false
  if (result.success) {
    profileSuccess.value = '显示名称已更新'
    ElMessage.success('显示名称已更新')
  } else {
    profileError.value = result.message || '更新失败'
  }
}

async function handleChangePassword() {
  if (!passwordFormRef.value) return
  try { await passwordFormRef.value.validate() } catch { return }
  passwordLoading.value = true
  passwordError.value = ''
  const result = await businessAuth.changePassword(
    passwordForm.value.old_password,
    passwordForm.value.new_password
  )
  passwordLoading.value = false
  if (result.success) {
    ElMessage.success('密码已修改，请重新登录')
    showProfileDialog.value = false
    if (route.meta.requiresBusinessAuth) {
      router.push('/')
    }
  } else {
    passwordError.value = result.message || '修改失败'
  }
}
</script>

<style scoped>
/* ===== 基础共用 ===== */
.top-nav { top: 0; left: 0; right: 0; z-index: 100; display: flex; align-items: center; padding: 0 48px; }
.nav-inner { width: 100%; margin: 0 auto; display: flex; align-items: center; justify-content: space-between; }
.nav-brand { text-decoration: none; font-weight: 700; letter-spacing: 3px; }
.brand-text { background: linear-gradient(90deg, #1a3a5c, #2a5a8c); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
.nav-menu { display: flex; align-items: center; }
.nav-item {
  text-decoration: none; font-weight: 400; letter-spacing: 1px;
  padding: 4px 0; position: relative; transition: color 0.3s; cursor: pointer;
}
.nav-item::after {
  content: ''; position: absolute; bottom: -2px; left: 0; width: 0; height: 2px;
  border-radius: 1px; transition: width 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}
.nav-item:hover::after { width: 100%; }
.active-item::after { width: 100%; }

/* 下拉触发器 */
.nav-dropdown { display: flex; align-items: center; }
.nav-dropdown-trigger { display: inline-flex; align-items: center; gap: 2px; }
.dropdown-arrow { font-size: 12px; transition: transform 0.2s; }

/* 登录/用户相关 */
.nav-login { cursor: pointer; }
.nav-user { display: inline-flex; align-items: center; gap: 4px; cursor: default; }
.nav-logout { cursor: pointer; }

.login-error { color: #f56c6c; font-size: 13px; text-align: center; margin: 0; }
.profile-success { color: #67c23a; font-size: 13px; text-align: center; margin: 0; }
.nav-user-clickable { cursor: pointer !important; }

/* ===== home 变体（深色透明→毛玻璃） ===== */
.nav-home {
  position: fixed; z-index: 1000; height: 72px;
  background: transparent; transition: background 0.4s, backdrop-filter 0.4s, box-shadow 0.4s;
}
.nav-home.scrolled {
  background: rgba(15, 25, 35, 0.85);
  backdrop-filter: saturate(180%) blur(20px);
  box-shadow: 0 1px 0 rgba(255,255,255,0.06);
}
.nav-home .nav-inner { max-width: 1280px; }
.nav-home .nav-brand { font-size: 22px; }
.nav-home .brand-text { background: linear-gradient(90deg, #fff, #cfd9e6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
.nav-home .nav-menu { gap: 40px; }
.nav-home .nav-item { color: rgba(255,255,255,0.75); font-size: 15px; padding: 6px 0; }
.nav-home .nav-item::after { bottom: 0; background: #fff; }
.nav-home .nav-item:hover { color: #fff; }
.nav-home .active-item { color: #fff; }
.nav-home .nav-login,
.nav-home .nav-logout { color: rgba(255,255,255,0.75); }
.nav-home .nav-login:hover,
.nav-home .nav-logout:hover { color: #fff; }
.nav-home .nav-user { color: rgba(255,255,255,0.9); }

/* ===== light 变体（粘性白色毛玻璃） ===== */
.nav-light {
  position: sticky; height: 64px;
  background: rgba(255,255,255,0.72); backdrop-filter: saturate(180%) blur(16px);
  box-shadow: 0 1px 0 rgba(0,0,0,0.06);
}
.nav-light .nav-inner { max-width: 1600px; }
.nav-light .nav-brand { font-size: 20px; }
.nav-light .nav-menu { gap: 36px; }
.nav-light .nav-item { color: #4a5568; font-size: 14px; }
.nav-light .nav-item::after { background: #1a3a5c; }
.nav-light .nav-item:hover { color: #1a3a5c; }
.nav-light .active-item { color: #1a3a5c; font-weight: 600; }
.nav-light .is-active { color: #1a3a5c; font-weight: 600; }
.nav-light .is-active::after { width: 100%; }
.nav-light .nav-login,
.nav-light .nav-logout { color: #4a5568; }
.nav-light .nav-login:hover,
.nav-light .nav-logout:hover { color: #1a3a5c; }
.nav-light .nav-user { color: #1a3a5c; font-weight: 500; }

/* ===== overlay 变体（绝对定位，透明叠加） ===== */
.nav-overlay {
  position: absolute; height: 64px;
  background: rgba(255,255,255,0.55); backdrop-filter: saturate(180%) blur(12px);
  box-shadow: 0 1px 0 rgba(0,0,0,0.04);
}
.nav-overlay .nav-inner { max-width: 1600px; }
.nav-overlay .nav-brand { font-size: 20px; }
.nav-overlay .nav-menu { gap: 36px; }
.nav-overlay .nav-item { color: #4a5568; font-size: 14px; }
.nav-overlay .nav-item::after { background: #1a3a5c; }
.nav-overlay .nav-item:hover { color: #1a3a5c; }
.nav-overlay .active-item { color: #1a3a5c; font-weight: 600; }
.nav-overlay .is-active { color: #1a3a5c; font-weight: 600; }
.nav-overlay .is-active::after { width: 100%; }
.nav-overlay .nav-login,
.nav-overlay .nav-logout { color: #4a5568; }
.nav-overlay .nav-login:hover,
.nav-overlay .nav-logout:hover { color: #1a3a5c; }
.nav-overlay .nav-user { color: #1a3a5c; font-weight: 500; }

/* ===== contact 变体（固定白色毛玻璃 72px） ===== */
.nav-contact {
  position: fixed; z-index: 1000; height: 72px;
  background: rgba(255,255,255,0.82); backdrop-filter: saturate(180%) blur(20px);
  box-shadow: 0 1px 0 rgba(0,0,0,0.06);
}
.nav-contact .nav-inner { max-width: 1280px; }
.nav-contact .nav-brand { font-size: 22px; }
.nav-contact .nav-menu { gap: 40px; }
.nav-contact .nav-item { color: #4a5568; font-size: 15px; padding: 6px 0; }
.nav-contact .nav-item::after { bottom: 0; background: #1a3a5c; }
.nav-contact .nav-item:hover { color: #1a3a5c; }
.nav-contact .active-item { color: #1a3a5c; font-weight: 600; }
.nav-contact .is-active { color: #1a3a5c; font-weight: 600; }
.nav-contact .is-active::after { width: 100%; }
.nav-contact .nav-login,
.nav-contact .nav-logout { color: #4a5568; }
.nav-contact .nav-login:hover,
.nav-contact .nav-logout:hover { color: #1a3a5c; }
.nav-contact .nav-user { color: #1a3a5c; font-weight: 500; }
</style>
