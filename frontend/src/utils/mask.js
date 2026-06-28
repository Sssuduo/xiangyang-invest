/**
 * 数据脱敏工具（访客模式）
 */

/**
 * 名称脱敏：保留首尾字符，中间用 * 替换
 * "某建设集团" → "某****团"
 * "张三" → "张*"
 * "" → "***"
 */
export function maskName(name) {
  if (!name) return '***'
  const s = String(name)
  if (s.length <= 1) return '*'
  if (s.length === 2) return s[0] + '*'
  return s[0] + '*'.repeat(Math.min(s.length - 2, 6)) + s[s.length - 1]
}

/**
 * 电话脱敏：保留前3后4，中间用 **** 替换
 * "13912345678" → "139****5678"
 * "" → "****"
 */
export function maskPhone(phone) {
  if (!phone) return '****'
  const s = String(phone)
  if (s.length <= 7) return s.slice(0, 3) + '****'
  return s.slice(0, 3) + '****' + s.slice(-4)
}

/**
 * 长文本脱敏：保留前5后5字符，中间用 *** 替换
 * "这是一段很长的项目内容描述文本..." → "这是一段很***述文本..."
 * "" → "***"
 */
export function maskContent(content) {
  if (!content) return '***'
  const s = String(content)
  if (s.length <= 6) return s[0] + '***' + s[s.length - 1]
  return s.slice(0, 5) + '***' + s.slice(-5)
}
