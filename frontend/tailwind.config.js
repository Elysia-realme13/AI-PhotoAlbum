/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        dark: {
          bg: '#1a1a2e',
          card: '#16213e',
          border: '#2a2a4a',
          text: '#e2e8f0',
          'text-secondary': '#94a3b8',
          hover: '#233044',
        },
      },
    },
  },
  plugins: [],
}
