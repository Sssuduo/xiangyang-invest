import api from './index'

// 获取指定字典类型的所有条目
export function getDictItems(dictType) {
  return api.get(`/admin/dicts/${dictType}`)
}

// 新增字典条目
export function createDictItem(dictType, data) {
  return api.post(`/admin/dicts/${dictType}`, data)
}

// 更新字典条目
export function updateDictItem(dictType, id, data) {
  return api.put(`/admin/dicts/${dictType}/${id}`, data)
}

// 删除字典条目
export function deleteDictItem(dictType, id) {
  return api.delete(`/admin/dicts/${dictType}/${id}`)
}

// 批量排序
export function reorderDictItems(dictType, ids) {
  return api.post(`/admin/dicts/${dictType}/reorder`, { ids })
}
