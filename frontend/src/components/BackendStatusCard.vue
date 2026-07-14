<!--
  后端连接状态卡片。

  父页面传入 Pinia 中的状态和说明文字，组件负责把它们转换成视觉反馈。重试按钮
  只发送事件，实际请求仍由 HomeView 调用 Store 完成，避免展示组件耦合业务逻辑。
-->
<script setup lang="ts">
import type { BackendStatus } from '../stores/app'

defineProps<{
  status: BackendStatus
  message: string
}>()

const emit = defineEmits<{
  retry: []
}>()
</script>

<template>
  <el-card class="status-card" shadow="never">
    <div class="status-card__header">
      <div>
        <p class="card-label">BACKEND CONNECTION</p>
        <h2>后端服务状态</h2>
      </div>
      <span :class="['status-indicator', `status-indicator--${status}`]">
        <span class="status-indicator__dot" aria-hidden="true"></span>
        {{ status === 'connected' ? '正常' : status === 'checking' ? '检查中' : '异常' }}
      </span>
    </div>

    <p class="status-message">{{ message }}</p>

    <div class="status-card__footer">
      <code>GET /api/health</code>
      <el-button
        type="primary"
        plain
        :loading="status === 'checking'"
        @click="emit('retry')"
      >
        重新检查
      </el-button>
    </div>
  </el-card>
</template>
