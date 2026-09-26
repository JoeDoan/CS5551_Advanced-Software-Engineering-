/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
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
        'umkc-blue': {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#005696',
          700: '#004b87', // Official UMKC Primary Blue
          800: '#003866',
          900: '#002647',
        },
        'umkc-gold': {
          50: '#fffbeb',
          100: '#fef3c7',
          200: '#fde68a',
          300: '#fcd34d',
          400: '#fbbf24',
          500: '#ffc72c', // Official Kangaroo Gold
          600: '#d99b00',
          700: '#b47b00',
          800: '#925f05',
          900: '#784d08',
        },
        dept: {
          cs: {
            bg: '#eff6ff',
            text: '#1d4ed8',
            border: '#bfdbfe',
            solid: '#2563eb',
          },
          math: {
            bg: '#f5f3ff',
            text: '#6d28d9',
            border: '#ddd6fe',
            solid: '#7c3aed',
          },
          ece: {
            bg: '#ecfdf5',
            text: '#047857',
            border: '#a7f3d0',
            solid: '#059669',
          },
          chem: {
            bg: '#fffbeb',
            text: '#b45309',
            border: '#fde68a',
            solid: '#d97706',
          },
          bio: {
            bg: '#f0fdfa',
            text: '#0f766e',
            border: '#99f6e4',
            solid: '#0d9488',
          },
        },
        status: {
          confirmed: '#059669',
          tentative: '#d97706',
          conflict: '#dc2626',
          pending: '#0284c7',
        },
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(8px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        pulseSubtle: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.85' },
        },
      },
      animation: {
        'fade-in': 'fadeIn 0.25s ease-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'pulse-subtle': 'pulseSubtle 2s infinite ease-in-out',
      },
      borderRadius: {
        'xl': '0.75rem',
        '2xl': '1rem',
        '3xl': '1.5rem',
      },
      boxShadow: {
        'card': '0 1px 3px 0 rgba(0, 0, 0, 0.05), 0 1px 2px -1px rgba(0, 0, 0, 0.05)',
        'card-hover': '0 4px 6px -1px rgba(0, 0, 0, 0.08), 0 2px 4px -2px rgba(0, 0, 0, 0.05)',
      },
    },
  },
  plugins: [],
}
