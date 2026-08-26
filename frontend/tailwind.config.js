/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: {
          50: "#EEF3F9",
          100: "#D7E3F0",
          200: "#A8C0DA",
          300: "#6C93BC",
          400: "#3A6B9E",
          500: "#27507E",
          600: "#1D3D63",
          700: "#16304F",
          800: "#10233F",
          900: "#0A1930",
          950: "#060F1F",
        },
        surface: {
          DEFAULT: "#F5F7FB",
          raised: "#FFFFFF",
        },
      },
      fontFamily: {
        sans: [
          "InterVariable",
          "Inter",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "sans-serif",
        ],
      },
      boxShadow: {
        card: "0 1px 2px rgba(16, 35, 63, 0.06), 0 1px 3px rgba(16, 35, 63, 0.08)",
        "card-hover":
          "0 4px 12px rgba(16, 35, 63, 0.10), 0 2px 4px rgba(16, 35, 63, 0.08)",
      },
      keyframes: {
        "fade-in": {
          from: { opacity: "0" },
          to: { opacity: "1" },
        },
        "rise-in": {
          from: { opacity: "0", transform: "translateY(10px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "fade-in": "fade-in 0.5s ease-out both",
        "rise-in": "rise-in 0.55s cubic-bezier(0.22, 1, 0.36, 1) both",
      },
    },
  },
  plugins: [],
};
