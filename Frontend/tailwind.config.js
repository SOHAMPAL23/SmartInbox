/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'system-ui', 'sans-serif'],
      },
      colors: {
        accent: {
          DEFAULT: '#4A90E2',
          light: '#EBF4FF',
          dark: '#2563EB',
        },
      },
      borderRadius: {
        DEFAULT: '12px',
        lg: '16px',
        xl: '20px',
        '2xl': '24px',
      },
      transitionDuration: {
        DEFAULT: '150ms',
      },
      animation: {
        'fade-in': 'fade-in 0.2s ease-out both',
        'spin-slow': 'spin 2s linear infinite',
      },
      boxShadow: {
        soft: '0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)',
        card: '0 4px 12px rgba(0,0,0,0.06)',
      },
    },
  },
  plugins: [],
};
