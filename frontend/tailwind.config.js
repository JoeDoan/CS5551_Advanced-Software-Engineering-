/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#eef6ff',
          100: '#d9eaff',
          500: '#1a73e8',
          600: '#1557b0',
          700: '#0d47a1',
          900: '#002171',
        },
      },
    },
  },
  plugins: [],
}
