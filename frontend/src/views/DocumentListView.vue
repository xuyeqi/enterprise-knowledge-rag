<!--
  文档列表页。

  页面读取后端聚合后的文档摘要，只展示元数据和切片数量，不请求切片正文或
  embedding。当前数据量较小，先完成无分页的最小闭环。
-->
<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { getDocuments, type DocumentListItem } from '../api/documents'

const documents = ref<DocumentListItem[]>([])
const isLoading = ref(false)
const errorMessage = ref('')

/** 从后端刷新文档摘要，失败时保留明确错误状态供用户重试。 */
async function loadDocuments(): Promise<void> {
  isLoading.value = true
  errorMessage.value = ''

  try {
    documents.value = await getDocuments()
  } catch (error) {
    documents.value = []
    errorMessage.value = error instanceof Error ? error.message : '文档列表加载失败。'
  } finally {
    isLoading.value = false
  }
}

/** 把后端 ISO 时间转换为当前浏览器所在时区的中文时间。 */
function formatCreatedAt(value: string): string {
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

onMounted(() => {
  void loadDocuments()
})
</script>

<template>
  <section class="document-list-page">
    <div class="page-intro">
      <div>
        <p class="section-kicker">DOCUMENT LIBRARY</p>
        <h2>知识库文档</h2>
        <p>查看已经完成向量入库的文档及其切片数量。</p>
      </div>
      <span class="phase-number">02</span>
    </div>

    <el-card class="document-table-card" shadow="never">
      <div class="list-toolbar">
        <div>
          <p class="card-label">INDEXED DOCUMENTS</p>
          <h3>共 {{ documents.length }} 份文档</h3>
        </div>
        <el-button :loading="isLoading" @click="loadDocuments">刷新列表</el-button>
      </div>

      <p v-if="errorMessage" class="table-message table-message--error" role="alert">
        {{ errorMessage }}
      </p>

      <el-table
        v-else
        v-loading="isLoading"
        :data="documents"
        empty-text="知识库中还没有文档"
        class="document-table"
      >
        <el-table-column label="文件名" min-width="220">
          <template #default="scope">
            <span class="document-name">{{ scope.row.filename }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="120">
          <template #default="scope">
            <el-tag type="success" effect="light">{{ scope.row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="chunk_count" label="切片数量" width="120" />
        <el-table-column label="入库时间" min-width="180">
          <template #default="scope">
            {{ formatCreatedAt(scope.row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="文档 ID" min-width="280">
          <template #default="scope">
            <code class="document-id">{{ scope.row.document_id }}</code>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </section>
</template>
