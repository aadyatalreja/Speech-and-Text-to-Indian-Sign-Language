import { StatusIndicator } from "./ui";
import ThemeToggle from "./ThemeToggle";
export const Logo = () => (
  <svg width="28" height="28" viewBox="0 0 28 28" aria-hidden>
    <defs><linearGradient id="logo-g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#6366F1" /><stop offset="1" stopColor="#8B5CF6" /></linearGradient></defs>
    <rect width="28" height="28" rx="8" fill="url(#logo-g)" />
    <path d="M7 17c3-7 7-7 9-3s4 3 5-2" fill="none" stroke="#fff" strokeWidth="2.2" strokeLinecap="round" />
    <circle cx="21" cy="9" r="1.8" fill="#fff" opacity=".85" />
  </svg>
);
export default function Header({ onHistory, online, dark, onToggleTheme }: { onHistory: () => void; online: boolean | null; dark: boolean; onToggleTheme: () => void }) {
  return (
    <header className="sticky top-3 z-30 mx-auto mt-3 flex max-w-5xl items-center justify-between gap-3 px-3">
      <div className="glass glass-strong flex w-full items-center justify-between rounded-card px-4 py-2.5">
        <a href="#top" className="flex items-center gap-2.5 rounded-ctl text-lg font-bold tracking-tight"><Logo />SignAI</a>
        <nav aria-label="Main" className="flex items-center gap-1">
          <a href="#top" className="btn-quiet">Translate</a>
          <button className="btn-quiet" onClick={onHistory}>History</button>
          <span className="ml-2 hidden sm:inline"><StatusIndicator ok={online} label={online === null ? "ISL · Connecting" : online ? "ISL · Ready" : "ISL · Offline"} /></span>
          <ThemeToggle dark={dark} onToggle={onToggleTheme} />
        </nav>
      </div>
    </header>
  );
}