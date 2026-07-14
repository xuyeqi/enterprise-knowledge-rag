/**
 * 文档接口。
 *
 * 上传页通过这里把浏览器选中的文件包装为 multipart/form-data，并请求后端
 * `POST /documents`。浏览器会自动生成 multipart boundary，因此不能手动设置
 * `Content-Type` 请求头。
 */
import { request } from './http'

/** 后端完成文档切片、向量化和数据库写入后返回的结果。 */
export interface DocumentIndexResponse {
  document_id: string
  filename: string
  status: string
  chunk_count: number
}

/**
 * 上传一份 UTF-8 文本文档并等待后端完成向量入库。
 *
 * @param file 用户在上传页选择的 `.txt` 或 `.md` 文件。
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
