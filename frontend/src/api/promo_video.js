import axios from 'axios'

const BASE = '/api'

export function getPublicVideos() {
  return axios.get(`${BASE}/promo-videos`)
}

export function getManageVideos() {
  return axios.get(`${BASE}/promo-videos/manage`)
}

export function createVideo(data) {
  return axios.post(`${BASE}/promo-videos/manage`, data)
}

export function updateVideo(id, data) {
  return axios.put(`${BASE}/promo-videos/manage/${id}`, data)
}

export function deleteVideo(id) {
  return axios.delete(`${BASE}/promo-videos/manage/${id}`)
}

export function sortVideos(data) {
  return axios.put(`${BASE}/promo-videos/manage/sort`, data)
}
