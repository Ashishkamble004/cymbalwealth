/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./index.tsx", "./**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        idfc: {
          maroon: "#791652",
          "maroon-dark": "#5a1040",
          "maroon-light": "#9a2a6e",
          blue: "#0066B3",
          "blue-dark": "#004d87",
          gold: "#C5A55A",
          cream: "#FFF8F0",
          gray: {
            50: "#F9FAFB",
            100: "#F3F4F6",
            200: "#E5E7EB",
            300: "#D1D5DB",
            400: "#9CA3AF",
            500: "#6B7280",
            600: "#4B5563",
            700: "#374151",
            800: "#1F2937",
            900: "#111827",
          },
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
