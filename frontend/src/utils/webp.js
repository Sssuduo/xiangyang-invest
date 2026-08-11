// WebP 支持检测 + 自动转换图片 URL
let webpSupported = null
let checkPromise = null

export function supportsWebp() {
  if (webpSupported !== null) return Promise.resolve(webpSupported)
  if (checkPromise) return checkPromise

  checkPromise = new Promise(resolve => {
    const img = new Image()
    img.onload = () => {
      webpSupported = img.width > 0 && img.height > 0
      resolve(webpSupported)
    }
    img.onerror = () => {
      webpSupported = false
      resolve(false)
    }
    // 1x1 WebP 测试图
    img.src = 'data:image/webp;base64,UklGRiQAAABXRUJQVlA4IBgAAAAwAQCdASoCAAEAAQAcJaQAA3AA/vp1tAA='
  })
  return checkPromise
}

// 将图片 URL 转换为 WebP（如果浏览器支持）
// 仅对 static/uploads 路径下的图片生效
// 返回 Promise<url>：转换后若 webp 文件不存在（404），自动回退原图
export function toWebpUrl(url) {
  if (!url) return Promise.resolve(url)
  // 跳过已经是 webp 的、base64 的、外部链接
  if (url.includes('.webp') || url.startsWith('data:') || url.startsWith('http')) return Promise.resolve(url)
  // 只处理 static/uploads 下的图片
  if (!url.includes('/static/uploads/')) return Promise.resolve(url)

  return supportsWebp().then(supported => {
    if (!supported) return url
    const lastDot = url.lastIndexOf('.')
    if (lastDot <= 0) return url
    const webpUrl = url.substring(0, lastDot) + '.webp'
    // 探测 webp 文件是否存在，404 则回退原图
    return new Promise(resolve => {
      const img = new Image()
      img.onload = () => resolve(webpUrl)
      img.onerror = () => resolve(url)
      img.src = webpUrl
    })
  })
}

// 同步版本（用在 computed 中，需要先初始化）
let _webpReady = false
export async function initWebp() {
  await supportsWebp()
  _webpReady = true
}

export function isWebpReady() {
  return _webpReady
}

export function toWebpUrlSync(url) {
  if (!url || !_webpReady) return url
  if (url.includes('.webp') || url.startsWith('data:') || url.startsWith('http')) return url
  if (!url.includes('/static/uploads/')) return url
  const lastDot = url.lastIndexOf('.')
  if (lastDot > 0) {
    return url.substring(0, lastDot) + '.webp'
  }
  return url
}
