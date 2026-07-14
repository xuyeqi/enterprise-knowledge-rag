/**
 * 前端路由配置。
 *
 * 当前只有系统概览页。使用路由而不是直接把页面写进 App.vue，是为了后续增加
 * 文档上传和聊天问答页面时保持清晰的页面边界。
 */
import { createRouter, createWebHistory } from 'vue-router'

import HomeView from '../views/HomeView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
    },
  ],
})

export default router
