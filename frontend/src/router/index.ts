/**
 * 前端路由配置。
 *
 * 系统概览、文档管理和知识问答各自使用独立页面组件，保持 App.vue 只负责
 * 全局布局，不承载具体业务状态。
 */
import { createRouter, createWebHistory } from 'vue-router'

import DocumentListView from '../views/DocumentListView.vue'
import DocumentUploadView from '../views/DocumentUploadView.vue'
import HomeView from '../views/HomeView.vue'
import KnowledgeChatView from '../views/KnowledgeChatView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
    },
    {
      path: '/documents',
      name: 'document-list',
      component: DocumentListView,
    },
    {
      path: '/documents/upload',
      name: 'document-upload',
      component: DocumentUploadView,
    },
    {
      path: '/chat',
      name: 'knowledge-chat',
      component: KnowledgeChatView,
    },
  ],
})

export default router
