/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js}'],
  theme: {
    extend: {
      colors: {
        admin: { DEFAULT: '#7c3aed', dark: '#6d28d9' },
      },
    },
  },
  plugins: [],
}
