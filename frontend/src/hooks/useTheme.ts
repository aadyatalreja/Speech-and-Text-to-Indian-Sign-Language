import { useCallback, useEffect, useState } from "react";

export type Theme = "light" | "dark";
const KEY = "signai.theme";
const stored = (): Theme | null => { try { const s = localStorage.getItem(KEY); return s === "light" || s === "dark" ? s : null; } catch { return null; } };
const system = (): Theme => (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");

/** Light/dark theme: saved choice wins, otherwise follows the OS setting live. */
export function useTheme() {
  const [theme, setTheme] = useState<Theme>(() => stored() ?? system());

  useEffect(() => {
    const r = document.documentElement;
    r.classList.toggle("dark", theme === "dark");
    r.style.colorScheme = theme;
    document.querySelector('meta[name="theme-color"]')?.setAttribute("content", theme === "dark" ? "#141211" : "#FAF8F5");
  }, [theme]);

  useEffect(() => {
    const mq = matchMedia("(prefers-color-scheme: dark)");
    const on = () => { if (!stored()) setTheme(system()); };
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, []);

  const toggle = useCallback(() => {
    const r = document.documentElement;
    r.classList.add("theme-anim");
    window.setTimeout(() => r.classList.remove("theme-anim"), 400);
    setTheme((t) => {
      const next: Theme = t === "dark" ? "light" : "dark";
      try { localStorage.setItem(KEY, next); } catch { /* storage unavailable */ }
      return next;
    });
  }, []);

  return { theme, dark: theme === "dark", toggle };
}