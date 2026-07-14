/**
 * 统一的前端 HTTP 请求入口。
 *
 * 所有业务接口都从 `/api` 开始，由 Vite 开发代理转发给 FastAPI。这里集中处理
 * HTTP 非成功状态，页面和 Store 只关心业务数据或捕获异常。
 */

const API_PREFIX = '/api'

export async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_PREFIX}${path}`, options)

  if (!response.ok) {
    throw new Error(`请求失败：HTTP ${response.status}`)
  }

  return (await response.json()) as T
}
