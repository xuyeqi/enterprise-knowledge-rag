/**
 * 应用级状态 Store。
 *
 * 当前只保存后端连接状态。把状态集中在 Pinia 中，可以让页头、概览页或后续其它
 * 页面共享同一份连接结果，避免每个组件分别请求健康接口。
 */
import { defineStore } from 'pinia'

import { getBackendHealth } from '../api/health'

export type BackendStatus = 'checking' | 'connected' | 'disconnected'

export const useAppStore = defineStore('app', {
  state: () => ({
    backendStatus: 'checking' as BackendStatus,
    backendMessage: '正在检查 FastAPI 服务……',
  }),
  actions: {
    async checkBackend(): Promise<void> {
      this.backendStatus = 'checking'
      this.backendMessage = '正在检查 FastAPI 服务……'

      try {
        const health = await getBackendHealth()
        if (health.status !== 'ok') {
          throw new Error(`未知健康状态：${health.status}`)
        }

        this.backendStatus = 'connected'
        this.backendMessage = 'FastAPI 服务连接正常'
      } catch (error) {
        this.backendStatus = 'disconnected'
        this.backendMessage =
          error instanceof Error ? error.message : '无法连接 FastAPI 服务'
      }
    },
  },
})
