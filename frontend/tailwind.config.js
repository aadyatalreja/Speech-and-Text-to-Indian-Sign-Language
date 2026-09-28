export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: { extend: {
    colors: { ink: "#111827", muted: "#5B6472", accent: { DEFAULT: "#4F46E5", soft: "#EEF0FF", deep: "#3730A3" }, warn: { DEFAULT: "#B45309", soft: "#FFF4E5" } },
    fontFamily: { sans: ["Manrope", "system-ui", "sans-serif"] },
    borderRadius: { ctl: "12px", card: "20px", panel: "24px" } } },
};
