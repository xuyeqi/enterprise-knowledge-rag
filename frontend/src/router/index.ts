/**
 * 前端路由配置。
 *
 * 系统概览、文档列表和文档上传各自使用独立页面组件。后续增加聊天问答时，
 * 继续通过这里登记路由，保持 App.vue 只负责全局布局。
 */
import { createRouter, createWebHistory } from 'vue-router'

import DocumentListView from '../views/DocumentListView.vue'
import DocumentUploadView from '../views/DocumentUploadView.vue'
import HomeView from '../views/HomeView.vue'

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
  ],
})

export default router
