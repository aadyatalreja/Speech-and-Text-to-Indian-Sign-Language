import { useId, useRef, useState } from "react";
import type { SignItem } from "../types/translation";
import { reportSign } from "../services/api";

/** Explicit opt-in only: no account or IP fields, never changes review metadata. */
export default function ReportSign({ item, sentence }: { item: SignItem; sentence: string }) {
  const heading = useId();
  const dialog = useRef<HTMLDialogElement>(null);
  const [note, setNote] = useState("");
  const [status, setStatus] = useState("");
  const [sending, setSending] = useState(false);
  return <>
    <button className="btn-quiet !p-1 text-xs" aria-label={`Report ${item.gloss}`} onClick={() => { setStatus(""); dialog.current?.showModal(); }}>Report</button>
    <dialog ref={dialog} className="m-auto max-w-md rounded-card bg-surface p-6 text-ink backdrop:bg-black/50" aria-labelledby={heading}>
      <form onSubmit={async e => {
        e.preventDefault(); setSending(true); setStatus("");
        try { await reportSign({ gloss: item.gloss, sign_id: item.sign_id, sentence, note, timestamp: new Date().toISOString() }); setNote(""); setStatus("Report saved for human review. No asset status was changed."); }
        catch { setStatus("Could not save report. Please retry later; reporting is rate limited."); }
        finally { setSending(false); }
      }}>
        <h2 id={heading} className="font-semibold">Report a wrong sign · experimental</h2>
        <p className="mt-2">Gloss: {item.gloss}</p>
        <label className="mt-3 block">Optional note (300 characters maximum)
          <textarea maxLength={300} value={note} onChange={e => setNote(e.target.value)} className="mt-1 w-full rounded border border-line/20 bg-transparent p-2" />
        </label>
        <p className="text-xs text-muted">Sends this gloss, sign ID, sentence, note and timestamp to the app server. No account or IP is saved in the report. Avoid personal information.</p>
        <p role="status" className="my-2 text-sm">{status}</p>
        <button type="submit" className="btn-primary" disabled={sending}>{sending ? "Sending…" : "Send report"}</button>
        <button type="button" className="btn-quiet" onClick={() => dialog.current?.close()}>Close</button>
      </form>
    </dialog>
  </>;
}
