/**
 * 前端应用入口。
 *
 * 这里创建 Vue 根应用，注册路由、Pinia 和 Element Plus，最后挂载到
 * `index.html` 中的 `#app`。后续页面都会通过这三个插件共享路由、状态和组件。
 */
import { createPinia } from 'pinia'
import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'

import App from './App.vue'
import router from './router'
import './styles/main.css'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(ElementPlus)
app.mount('#app')
