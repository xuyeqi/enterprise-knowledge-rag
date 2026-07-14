<!--
  前端根布局。

  这个组件只负责全局导航和页面容器，具体业务内容由 router-view 根据当前路由
  渲染。后续增加上传页和问答页时，可以继续复用同一套企业后台布局。
-->
<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
</script>

<template>
  <div class="app-shell">
    <aside class="app-sidebar">
      <div class="brand-block">
        <span class="brand-mark">KB</span>
        <div>
          <p class="brand-name">Knowledge Base</p>
          <p class="brand-caption">Enterprise RAG</p>
        </div>
      </div>

      <nav class="app-nav" aria-label="主导航">
        <RouterLink class="nav-item" to="/">
          <span class="nav-dot" aria-hidden="true"></span>
          系统概览
        </RouterLink>
        <RouterLink class="nav-item" to="/documents/upload">
          <span class="nav-dot" aria-hidden="true"></span>
          文档上传
        </RouterLink>
      </nav>

      <div class="sidebar-note">
        <span>阶段 3</span>
        <strong>前端最小界面</strong>
      </div>
    </aside>

    <main class="app-main">
      <header class="app-header">
        <div>
          <p class="header-eyebrow">ENTERPRISE KNOWLEDGE SYSTEM</p>
          <h1>企业知识库</h1>
        </div>
        <span class="environment-badge">Local</span>
      </header>

      <RouterView />
    </main>
  </div>
</template>
