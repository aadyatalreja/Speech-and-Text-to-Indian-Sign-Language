export default function HistoryPanel({ items, onPick }: { items: string[]; onPick: (t: string) => void }) {
  return (
    <section aria-labelledby="hist-h" className="rounded-xl border-2 border-line p-5">
      <h2 id="hist-h" className="mb-2 font-bold">Recent translations</h2>
      {items.length === 0 ? <p>Nothing yet. Sentences you translate appear here.</p> :
        <ul className="space-y-1">{items.map((t) => <li key={t}><button className="text-left underline hover:bg-saffron" onClick={() => onPick(t)}>{t}</button></li>)}</ul>}
    </section>
  );
}
