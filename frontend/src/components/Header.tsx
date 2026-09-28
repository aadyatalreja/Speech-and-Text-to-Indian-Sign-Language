export default function Header() {
  return (
    <header className="border-b-2 border-ink bg-panel">
      <div className="mx-auto flex max-w-6xl flex-wrap items-baseline justify-between gap-2 px-6 py-5">
        <h1 className="text-3xl font-bold">SignAI</h1>
        <p className="text-base">AI Text / Speech → Indian Sign Language <span className="ml-2 rounded bg-saffron px-2 py-1 text-sm font-bold">Research prototype</span></p>
      </div>
    </header>
  );
}
