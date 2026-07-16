/**
 * 文档接口。
 *
 * 文档列表页通过这里读取文档摘要；上传页则把浏览器选中的文件包装为
 * multipart/form-data，并请求后端 `POST /documents`。浏览器会自动生成
 * multipart boundary，因此上传时不能手动设置 `Content-Type` 请求头。
 */
import { request } from './http'

/** 后端完成文档切片、向量化和数据库写入后返回的结果。 */
export interface DocumentIndexResponse {
  document_id: string
  filename: string
  status: string
  chunk_count: number
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
 * 上传一份 UTF-8 文本文档并等待后端完成向量入库。
 *
 * @param file 用户在上传页选择的 `.txt`、`.md` 或文本型 `.pdf` 文件。
 * @returns 后端生成的文档 ID、文件名、状态和切片数量。
 */
export function uploadDocument(file: File): Promise<DocumentIndexResponse> {
  const formData = new FormData()
  formData.append('file', file)

  return request<DocumentIndexResponse>('/documents', {
    method: 'POST',
    body: formData,
  })
}
