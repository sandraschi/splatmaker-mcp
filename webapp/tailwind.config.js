/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        amber: { 500: "#f59e0b" },
      },
    },
  },
  plugins: [],
};
