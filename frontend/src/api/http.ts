/**
 * 统一的前端 HTTP 请求入口。
 *
 * 所有业务接口都从 `/api` 开始，由 Vite 开发代理转发给 FastAPI。这里集中处理
 * HTTP 非成功状态，页面和 Store 只关心业务数据或捕获异常。
 */

const API_PREFIX = '/api'

/** 发送请求并在成功时保留原始 Response，供流式接口读取 response.body。 */
export async function requestResponse(
  path: string,
  options?: RequestInit,
): Promise<Response> {
  const response = await fetch(`${API_PREFIX}${path}`, options)

  if (!response.ok) {
    let detail = ''

    try {
      const errorBody = (await response.json()) as { detail?: unknown }
      if (typeof errorBody.detail === 'string') {
        detail = errorBody.detail
      }
    } catch {
      // 非 JSON 错误响应没有可提取的业务信息，下面统一回退到 HTTP 状态码。
    }

    throw new Error(detail || `请求失败：HTTP ${response.status}`)
  }

  return response
}

export async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await requestResponse(path, options)

  return (await response.json()) as T
}
