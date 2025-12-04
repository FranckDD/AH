// src/main.js
import { createApp } from 'vue'
import { createPinia } from 'pinia' // 👈 Import Pinia
import router from './router'      // 👈 Import Routeur
import i18n from './i18n' // 👈 Importez le fichier créé
import App from './App.vue'
import './style.css'

const app = createApp(App)

app.use(createPinia()) // 👈 Utiliser Pinia
app.use(router)        // 👈 Utiliser le Routeur
app.use(i18n) // 👈 Activez le plugin ici

app.mount('#app')
