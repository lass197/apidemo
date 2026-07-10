/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js}'],
  theme: {
    extend: {
      colors: {
        primary: { DEFAULT: '#0d9488', dark: '#0f766e' },
        hospital: { 50: '#f0fdfa', 900: '#134e4a' },
      },
    },
  },
  plugins: [],
}
