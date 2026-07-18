<!--
  文档上传页。

  页面只负责选择文件、创建后台任务、轮询状态和展示结果。文档解析、
  切片、向量化与数据库事务由 RQ Worker 负责。
-->
<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'

import {
  enqueueDocument,
  getDocumentJob,
  type DocumentJobStatusResponse,
} from '../api/documents'

const MAX_UPLOAD_SIZE_BYTES = 2 * 1024 * 1024

const selectedFile = ref<File | null>(null)
const isUploading = ref(false)
const errorMessage = ref('')
const uploadResult = ref<DocumentJobStatusResponse | null>(null)
const deduplicated = ref(false)

// 每次上传或页面卸载时递增标识，让旧轮询循环及时退出。
let pollingToken = 0

const selectedFileSize = computed(() => {
  if (!selectedFile.value) {
    return ''
  }

  return `${(selectedFile.value.size / 1024).toFixed(1)} KB`
})

const processingLabel = computed(() => {
  if (uploadResult.value?.status === 'retrying') {
    return '失败后等待重试'
  }

  if (uploadResult.value?.status === 'started') {
    return '正在生成向量索引'
  }

  return '正在等待后台 Worker'
})

/** 保存用户本次选择的文件，并清理上一次请求留下的结果。 */
function handleFileChange(event: Event): void {
  const input = event.target as HTMLInputElement
  selectedFile.value = input.files?.[0] ?? null
  errorMessage.value = ''
  uploadResult.value = null
  deduplicated.value = false
}

/** 等待指定毫秒数，避免对状态接口进行无间隔请求。 */
function delay(milliseconds: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds))
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

  if (!/\.(txt|md|pdf)$/i.test(file.name)) {
    errorMessage.value = '仅支持 .txt、.md 和 .pdf 文件。'
    return
  }

  if (file.size > MAX_UPLOAD_SIZE_BYTES) {
    errorMessage.value = '文件不能超过 2 MB。'
    return
  }

  isUploading.value = true
  errorMessage.value = ''
  uploadResult.value = null
  deduplicated.value = false
  const currentPollingToken = ++pollingToken

  try {
    const createdJob = await enqueueDocument(file)
    deduplicated.value = createdJob.deduplicated

    while (currentPollingToken === pollingToken) {
      const currentJob = await getDocumentJob(createdJob.job_id)
      uploadResult.value = currentJob

      if (currentJob.status === 'finished') {
        return
      }

      if (currentJob.status === 'failed') {
        throw new Error(currentJob.error ?? '文档索引失败，请稍后重试。')
      }

      await delay(1000)
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '文档上传失败，请稍后重试。'
  } finally {
    if (currentPollingToken === pollingToken) {
      isUploading.value = false
    }
  }
}

onBeforeUnmount(() => {
  pollingToken += 1
})
</script>

<template>
  <section class="upload-page">
    <div class="page-intro">
      <div>
        <p class="section-kicker">DOCUMENT INGESTION</p>
        <h2>上传文档并建立向量索引</h2>
        <p>支持 UTF-8 编码的 TXT、Markdown 和文本型 PDF，单个文件最大 2 MB。</p>
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
          <span class="file-limit">TXT / MD / PDF · 2 MB</span>
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
            accept=".txt,.md,.pdf,text/plain,text/markdown,application/pdf"
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
          {{ isUploading ? processingLabel : '上传并写入知识库' }}
        </el-button>
      </el-card>

      <el-card v-if="uploadResult" class="upload-result-card" shadow="never">
        <p class="card-label">INDEX RESULT</p>
        <h3>{{ uploadResult.status === 'finished' ? '文档入库成功' : '文档正在后台处理' }}</h3>

        <p v-if="deduplicated" class="job-note">
          已存在相同内容的任务，本次直接跟踪原任务，不会重复生成向量。
        </p>

        <dl class="result-list">
          <div>
            <dt>文件名</dt>
            <dd>{{ uploadResult.filename }}</dd>
          </div>
          <div>
            <dt>处理状态</dt>
            <dd>
              <el-tag :type="uploadResult.status === 'finished' ? 'success' : 'warning'">
                {{ uploadResult.status }}
              </el-tag>
            </dd>
          </div>
          <div v-if="uploadResult.chunk_count !== null">
            <dt>切片数量</dt>
            <dd>{{ uploadResult.chunk_count }}</dd>
          </div>
          <div v-if="uploadResult.document_id">
            <dt>文档 ID</dt>
            <dd><code>{{ uploadResult.document_id }}</code></dd>
          </div>
          <div>
            <dt>任务 ID</dt>
            <dd><code>{{ uploadResult.job_id }}</code></dd>
          </div>
        </dl>
      </el-card>
    </div>
  </section>
</template>
