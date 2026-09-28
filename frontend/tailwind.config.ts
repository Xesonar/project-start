import type { Config } from "tailwindcss";

/**
 * Project Start — design system.
 *
 * Tokens are named, not numbered-by-mood: `surface`/`surface-2` for cards,
 * `semantic-*` for feedback, `brand` for the product gradient. Dark mode is
 * class-based (`<html class="dark">`) so MAX/device theme can be overridden by the user.
 */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eef4ff",
          100: "#d9e6ff",
          200: "#bcd3ff",
          300: "#8eb4ff",
          400: "#5b8def",
          500: "#3563e9",
          600: "#274bc4",
          700: "#1e3a99",
          800: "#1a2e74",
          900: "#17265c",
          950: "#101a3d",
        },
        accent: {
          400: "#a78bfa",
          500: "#8b5cf6",
          600: "#7c3aed",
        },
        surface: {
          DEFAULT: "#ffffff",
          2: "#f8fafc",
          3: "#f1f5f9",
        },
        ok: { 50: "#ecfdf5", 600: "#059669", 700: "#047857" },
        warn: { 50: "#fffbeb", 600: "#d97706", 700: "#b45309" },
        danger: { 50: "#fef2f2", 600: "#dc2626", 700: "#b91c1c" },
      },
      fontFamily: {
        sans: [
          "Inter",
          "system-ui",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "Roboto",
          "Helvetica Neue",
          "Arial",
          "sans-serif",
        ],
      },
      borderRadius: {
        xs: "0.5rem",
        sm: "0.625rem",
        DEFAULT: "0.75rem",
        lg: "1rem",
        xl: "1.25rem",
        "2xl": "1.5rem",
      },
      boxShadow: {
        // Layered, soft — avoids the hard "student project" 1px border look
        soft: "0 1px 2px rgba(15, 23, 42, 0.04), 0 4px 16px rgba(15, 23, 42, 0.06)",
        lift: "0 2px 4px rgba(15, 23, 42, 0.05), 0 12px 32px rgba(15, 23, 42, 0.12)",
        glow: "0 8px 32px rgba(53, 99, 233, 0.35)",
      },
      backgroundImage: {
        "brand-gradient":
          "linear-gradient(135deg, #3563e9 0%, #7c3aed 100%)",
        "brand-gradient-soft":
          "linear-gradient(135deg, rgba(53, 99, 233, 0.12) 0%, rgba(139, 92, 246, 0.12) 100%)",
        "grid-pattern":
          "linear-gradient(to right, rgba(148, 163, 184, 0.12) 1px, transparent 1px), linear-gradient(to bottom, rgba(148, 163, 184, 0.12) 1px, transparent 1px)",
      },
      backgroundSize: {
        grid: "32px 32px",
      },
      transitionTimingFunction: {
        "out-expo": "cubic-bezier(0.16, 1, 0.3, 1)",
        spring: "cubic-bezier(0.34, 1.56, 0.64, 1)",
      },
      keyframes: {
        shimmer: {
          "100%": { transform: "translateX(100%)" },
        },
        "fade-in-up": {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "scale-in": {
          "0%": { opacity: "0", transform: "scale(0.96)" },
          "100%": { opacity: "1", transform: "scale(1)" },
        },
        "pulse-ring": {
          "0%": { transform: "scale(0.8)", opacity: "0.6" },
          "100%": { transform: "scale(2.2)", opacity: "0" },
        },
        "gradient-pan": {
          "0%, 100%": { backgroundPosition: "0% 50%" },
          "50%": { backgroundPosition: "100% 50%" },
        },
      },
      animation: {
        shimmer: "shimmer 1.4s infinite",
        "fade-in-up": "fade-in-up 0.45s cubic-bezier(0.16, 1, 0.3, 1) both",
        "scale-in": "scale-in 0.3s cubic-bezier(0.34, 1.56, 0.64, 1) both",
        "pulse-ring": "pulse-ring 1.6s cubic-bezier(0.16, 1, 0.3, 1) infinite",
        "gradient-pan": "gradient-pan 6s ease infinite",
      },
    },
  },
  plugins: [],
} satisfies Config;
