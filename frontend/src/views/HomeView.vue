<!--
  系统概览页。

  页面挂载后调用 Pinia 的健康检查 action，验证 Vue、状态管理、Vite 代理与
  FastAPI 已形成最小前后端闭环。后续功能页完成前，这里只展示真实可验证状态。
-->
<script setup lang="ts">
import { onMounted } from 'vue'
import { storeToRefs } from 'pinia'

import BackendStatusCard from '../components/BackendStatusCard.vue'
import { useAppStore } from '../stores/app'

const appStore = useAppStore()
const { backendStatus, backendMessage } = storeToRefs(appStore)

onMounted(() => {
  void appStore.checkBackend()
})
</script>

<template>
  <section class="overview-page">
    <div class="overview-intro">
      <div>
        <p class="section-kicker">SYSTEM OVERVIEW</p>
        <h2>知识从文档进入，答案从证据产生。</h2>
        <p>
          当前工作台已接入文档上传、文档列表和带引用知识问答，可以验证从资料
          入库到基于证据生成答案的完整 RAG 链路。
        </p>
      </div>
      <span class="phase-number">04</span>
    </div>

    <div class="overview-grid">
      <BackendStatusCard
        :status="backendStatus"
        :message="backendMessage"
        @retry="appStore.checkBackend"
      />

      <el-card class="capability-card" shadow="never">
        <p class="card-label">RAG PIPELINE</p>
        <h2>后端能力</h2>
        <ol class="pipeline-list">
          <li><span>01</span>UTF-8 文档上传与中文切片</li>
          <li><span>02</span>百炼 embedding 与 pgvector 检索</li>
          <li><span>03</span>LangChain 问答与引用来源</li>
        </ol>
      </el-card>
    </div>
  </section>
</template>
