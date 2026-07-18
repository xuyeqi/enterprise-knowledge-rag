/**
 * 文档接口。
 *
 * 文档列表页通过这里读取文档摘要；上传页则把浏览器选中的文件包装为
 * multipart/form-data，并请求后端异步索引队列。浏览器会自动生成
 * multipart boundary，因此上传时不能手动设置 `Content-Type` 请求头。
 */
import { request } from './http'

export type DocumentJobStatus = 'queued' | 'started' | 'retrying' | 'finished' | 'failed'

/** 文档已被 Redis 后台队列接收后立即返回的结果。 */
export interface DocumentJobCreateResponse {
  job_id: string
  status: DocumentJobStatus
  deduplicated: boolean
}

/** 前端轮询的文档索引任务快照。 */
export interface DocumentJobStatusResponse {
  job_id: string
  filename: string
  status: DocumentJobStatus
  document_id: string | null
  chunk_count: number | null
  error: string | null
}

/** 文档列表中的摘要字段；不包含切片正文和 embedding。 */
export interface DocumentListItem {
  document_id: string
  filename: string
  status: string
  chunk_count: number
  created_at: string
}

/** 读取按入库时间倒序排列的全部文档摘要。 */
export function getDocuments(): Promise<DocumentListItem[]> {
  return request<DocumentListItem[]>('/documents')
}

/**
 * 上传一份文档并交给后台队列，不等待向量入库。
 *
 * @param file 用户在上传页选择的 `.txt`、`.md` 或文本型 `.pdf` 文件。
 * @returns 后台任务 ID、初始状态和是否命中重复任务。
 */
export function enqueueDocument(file: File): Promise<DocumentJobCreateResponse> {
  const formData = new FormData()
  formData.append('file', file)

  return request<DocumentJobCreateResponse>('/documents/jobs', {
    method: 'POST',
    body: formData,
  })
}

/** 读取一个后台文档索引任务的最新状态。 */
export function getDocumentJob(jobId: string): Promise<DocumentJobStatusResponse> {
  return request<DocumentJobStatusResponse>(`/documents/jobs/${encodeURIComponent(jobId)}`)
}
