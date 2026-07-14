<!--
  文档上传页。

  页面只负责选择文件、调用文档 API 和展示入库结果。文件解析、切片、向量化与
  数据库事务仍全部由 FastAPI 负责，避免在前后端重复实现业务规则。
-->
<script setup lang="ts">
import { computed, ref } from 'vue'

import {
  uploadDocument,
  type DocumentIndexResponse,
} from '../api/documents'

const MAX_UPLOAD_SIZE_BYTES = 2 * 1024 * 1024

const selectedFile = ref<File | null>(null)
const isUploading = ref(false)
const errorMessage = ref('')
const uploadResult = ref<DocumentIndexResponse | null>(null)

const selectedFileSize = computed(() => {
  if (!selectedFile.value) {
    return ''
  }

  return `${(selectedFile.value.size / 1024).toFixed(1)} KB`
})

/** 保存用户本次选择的文件，并清理上一次请求留下的结果。 */
function handleFileChange(event: Event): void {
  const input = event.target as HTMLInputElement
  selectedFile.value = input.files?.[0] ?? null
  errorMessage.value = ''
  uploadResult.value = null
}

/**
 * 完成最小前端校验后调用正式入库接口。
 *
 * 后端仍会重复校验扩展名、大小、编码和空内容；前端校验只用于更快地给用户反馈。
 */
async function handleUpload(): Promise<void> {
  const file = selectedFile.value

  if (!file) {
    errorMessage.value = '请先选择需要上传的文档。'
    return
  }

  if (!/\.(txt|md)$/i.test(file.name)) {
    errorMessage.value = '仅支持 .txt 和 .md 文件。'
    return
  }

  if (file.size > MAX_UPLOAD_SIZE_BYTES) {
    errorMessage.value = '文件不能超过 2 MB。'
    return
  }

  isUploading.value = true
  errorMessage.value = ''
  uploadResult.value = null

  try {
    uploadResult.value = await uploadDocument(file)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '文档上传失败，请稍后重试。'
  } finally {
    isUploading.value = false
  }
}
</script>

<template>
  <section class="upload-page">
    <div class="page-intro">
      <div>
        <p class="section-kicker">DOCUMENT INGESTION</p>
        <h2>上传文档并建立向量索引</h2>
        <p>支持 UTF-8 编码的 TXT 和 Markdown 文件，单个文件最大 2 MB。</p>
      </div>
      <span class="phase-number">01</span>
    </div>

    <div class="upload-layout">
      <el-card class="upload-card" shadow="never">
        <div class="upload-card__header">
          <div>
            <p class="card-label">SOURCE FILE</p>
            <h3>选择知识库文档</h3>
          </div>
          <span class="file-limit">TXT / MD · 2 MB</span>
        </div>

        <label class="file-picker">
          <span class="file-picker__title">
            {{ selectedFile ? selectedFile.name : '点击选择本地文档' }}
          </span>
          <span class="file-picker__hint">
            {{ selectedFile ? selectedFileSize : '文件将经过切片、向量化并写入 pgvector' }}
          </span>
          <input
            type="file"
            accept=".txt,.md,text/plain,text/markdown"
            :disabled="isUploading"
            @change="handleFileChange"
          />
        </label>

        <p v-if="errorMessage" class="form-message form-message--error" role="alert">
          {{ errorMessage }}
        </p>

        <el-button
          type="primary"
          size="large"
          :loading="isUploading"
          :disabled="!selectedFile"
          @click="handleUpload"
        >
          {{ isUploading ? '正在生成向量索引' : '上传并写入知识库' }}
        </el-button>
      </el-card>

      <el-card v-if="uploadResult" class="upload-result-card" shadow="never">
        <p class="card-label">INDEX RESULT</p>
        <h3>文档入库成功</h3>

        <dl class="result-list">
          <div>
            <dt>文件名</dt>
            <dd>{{ uploadResult.filename }}</dd>
          </div>
          <div>
            <dt>处理状态</dt>
            <dd><el-tag type="success">{{ uploadResult.status }}</el-tag></dd>
          </div>
          <div>
            <dt>切片数量</dt>
            <dd>{{ uploadResult.chunk_count }}</dd>
          </div>
          <div>
            <dt>文档 ID</dt>
            <dd><code>{{ uploadResult.document_id }}</code></dd>
          </div>
        </dl>
      </el-card>
    </div>
  </section>
</template>
