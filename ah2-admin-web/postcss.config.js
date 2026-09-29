export default {
  plugins: {
    // Tailwind v4 : le plugin PostCSS a change de nom ('tailwindcss' ->
    // '@tailwindcss/postcss'), autoprefixer n'est plus necessaire (gere
    // en interne par le nouveau moteur Lightning CSS).
    '@tailwindcss/postcss': {},
  },
}