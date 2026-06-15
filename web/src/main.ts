import App from './App.vue'
import './assets/main.css'
import router from './router'
import { pinia } from '@/stores'
import { createApp } from 'vue'

const app = createApp(App)
app.use(pinia)
app.use(router)
app.mount('#app')
