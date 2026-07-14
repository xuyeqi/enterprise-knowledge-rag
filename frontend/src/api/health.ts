/**
 * 后端健康检查接口。
 *
 * HomeView 通过 Pinia Store 调用这里，确认浏览器、Vite 代理和 FastAPI 三段链路
 * 都能正常工作。接口只读取状态，不会访问数据库或产生模型调用费用。
 */
import { request } from './http'

export interface HealthResponse {
  status: string
}

export function getBackendHealth(): Promise<HealthResponse> {
  return request<HealthResponse>('/health')
}
