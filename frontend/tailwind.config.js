/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#0d1117',
        surface: '#161b22',
        surfaceHover: '#21262d',
        border: '#30363d',
        accent: '#58a6ff',
        accentSuccess: '#3fb950',
        accentWarning: '#d29922',
        accentDanger: '#f85149',
      },
    },
  },
  plugins: [],
}
