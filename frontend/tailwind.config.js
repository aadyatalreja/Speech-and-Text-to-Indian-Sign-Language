// Colours are CSS variables (see src/styles/index.css) so light/dark swap without touching components.
const c = (v) => `rgb(var(--${v}) / <alpha-value>)`;
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: { extend: {
    colors: {
      ink: c("ink"), muted: c("muted"), line: c("line"), surface: c("surface"), raised: c("raised"),
      accent: { DEFAULT: c("accent"), 2: c("accent2"), soft: c("accent-soft"), deep: c("accent-deep"), fg: c("accent-fg") },
      warn: { DEFAULT: c("warn"), soft: c("warn-soft") },
    },
    fontFamily: { sans: ["Manrope", "system-ui", "sans-serif"], display: ["Fraunces", "Georgia", "serif"] },
    borderRadius: { ctl: "12px", card: "20px", panel: "24px" },
    boxShadow: { glow: "0 1px 6px rgb(var(--accent) / .30)" },
  } },
};