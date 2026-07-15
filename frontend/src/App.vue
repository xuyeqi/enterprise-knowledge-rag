<!--
  前端根布局。

  这个组件只负责全局导航和页面容器，具体业务内容由 router-view 根据当前路由
  渲染。概览、文档管理和知识问答共用这套企业后台布局。
-->
<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'

import naturalStoneProductsUrl from './assets/natural-stone-products.jpg'
import BrandLogo from './components/BrandLogo.vue'
</script>

<template>
  <div class="app-shell">
    <aside class="app-sidebar">
      <div class="brand-block">
        <BrandLogo class="brand-logo--sidebar" />
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
        <RouterLink class="nav-item" to="/documents">
          <span class="nav-dot" aria-hidden="true"></span>
          文档列表
        </RouterLink>
        <RouterLink class="nav-item" to="/documents/upload">
          <span class="nav-dot" aria-hidden="true"></span>
          文档上传
        </RouterLink>
        <RouterLink class="nav-item" to="/chat">
          <span class="nav-dot" aria-hidden="true"></span>
          知识问答
        </RouterLink>
      </nav>

      <div class="sidebar-note">
        <span>阶段 4</span>
        <strong>工程化增强</strong>
      </div>
    </aside>

    <main class="app-main">
      <header class="app-header">
        <div class="header-brand">
          <BrandLogo class="brand-logo--header" />
          <div class="header-brand__copy">
            <p class="header-eyebrow">ENTERPRISE KNOWLEDGE SYSTEM</p>
            <h1>林希电子商务公司知识库系统</h1>
          </div>
        </div>
        <figure class="product-showcase">
          <img
            :src="naturalStoneProductsUrl"
            alt="林希电子商务公司的天然石雕件产品陈列"
          />
          <figcaption>
            <span>CORE COLLECTION</span>
            <strong>天然石饰品</strong>
          </figcaption>
        </figure>
      </header>

      <RouterView />
    </main>
  </div>
</template>
