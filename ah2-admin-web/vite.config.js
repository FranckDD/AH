import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import wasm from 'vite-plugin-wasm'
import topLevelAwait from 'vite-plugin-top-level-await'
import { VitePWA } from 'vite-plugin-pwa'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    wasm(),
    topLevelAwait(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['pwa-192x192.png', 'pwa-512x512.png', 'pwa-maskable-512x512.png'],
      manifest: {
        name: 'AH2',
        short_name: 'AH2',
        description: 'AH2 - Gestion hospitaliere',
        theme_color: '#0d9488',
        background_color: '#ffffff',
        icons: [
          { src: 'pwa-192x192.png', sizes: '192x192', type: 'image/png' },
          { src: 'pwa-512x512.png', sizes: '512x512', type: 'image/png' },
          { src: 'pwa-maskable-512x512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
      workbox: {
        // Ne met en cache que le shell applicatif (JS/CSS/HTML/icones) -
        // PowerSync gere la synchronisation des donnees separement, le
        // service worker ne doit jamais intercepter les appels /appointments/*
        // ni les requetes vers le service PowerSync (port 18080).
        globPatterns: ['**/*.{js,css,html,png,svg,ico}'],
      },
    }),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  // vite-plugin-top-level-await doit connaitre une cible de build explicite.
  // Sans cela, il retombe sur la cible historique par defaut de Vite
  // (chrome87/edge88/es2020/firefox78/safari14) pour sa propre passe de
  // transformation finale du bundle, ce qui declenche un bug connu d'esbuild
  // ("Transforming destructuring to the configured target environment is not
  // supported yet") avec les versions actuelles de esbuild/rollup utilisees
  // par Vite 7. Cibler esnext evite ce downlevel et laisse le plugin gerer
  // lui-meme le polyfill du top-level await.
  build: {
    target: 'esnext',
  },
  // Production : console.log/console.debug retires du bundle (retour
  // terrain 2026-09-28 - identite de l'utilisateur connecte et donnees
  // patient visibles dans la console du navigateur). console.warn/error
  // conserves, utiles au diagnostic et sans donnees sensibles par convention.
  esbuild: process.env.NODE_ENV === 'production' || process.argv.includes('build')
    ? { pure: ['console.log', 'console.debug'] }
    : {},
  // @powersync/web embarque des web workers + fichiers WASM (wa-sqlite) -
  // doit etre exclu de l'optimisation de dependances Vite, sinon le build
  // echoue ou le worker ne charge pas correctement au runtime.
  optimizeDeps: {
    exclude: ['@journeyapps/wa-sqlite', '@powersync/web'],
  },
  worker: {
    format: 'es',
    plugins: () => [wasm(), topLevelAwait()],
  },
})
