import type { Config } from "tailwindcss";

export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      boxShadow: {
        glass: "0 10px 40px rgba(15,23,42,0.35)"
      }
    }
  },
  plugins: []
} satisfies Config;