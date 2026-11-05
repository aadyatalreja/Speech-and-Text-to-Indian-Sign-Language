import { expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { createSpeechSession, ERRORS, type Recognition } from "../hooks/useSpeech";
import TextInput, { LANGS } from "../components/TextInput";

class FakeRecognition implements Recognition {
  lang = ""; interimResults = false; continuous = false; maxAlternatives = 0;
  start = vi.fn(); stop = vi.fn(); abort = vi.fn();
  onresult: Recognition["onresult"] = null;
  onerror: Recognition["onerror"] = null;
  onend: Recognition["onend"] = null;
}

it.each([["hi-IN", "मुझे मदद चाहिए"], ["kn-IN", "ನನಗೆ ಸಹಾಯ ಬೇಕು"]])("passes %s from the selector to speech and typing without changing script", (locale, text) => {
  const selected = LANGS.find(([code]) => code === locale)![0];
  const callbacks = { interim: vi.fn(), final: vi.fn(), error: vi.fn(), end: vi.fn() };
  const { recognition: r } = createSpeechSession(FakeRecognition, selected, callbacks);
  expect(r.lang).toBe(locale);
  r.start();
  r.onresult!({ resultIndex: 0, results: [{ isFinal: false, 0: { transcript: text } }] });
  expect(callbacks.interim).toHaveBeenLastCalledWith(text);
  r.onresult!({ resultIndex: 0, results: [{ isFinal: true, 0: { transcript: text } }] });
  r.onend!();
  expect(callbacks.final).toHaveBeenCalledWith(text);
  const html = renderToStaticMarkup(<TextInput value={text} onChange={vi.fn()} onTranslate={vi.fn()} busy={false} realtime={false} onRealtime={vi.fn()} mode="type" onMode={vi.fn()} speech={{ supported: true, listening: false, error: null, start: vi.fn(), stop: vi.fn() }} lang={selected} onLang={vi.fn()} hint={null} />);
  expect(html).toContain(`lang="${locale}"`);
});

it("reports unsupported locales and suppresses final submission without English retry", () => {
  const callbacks = { interim: vi.fn(), final: vi.fn(), error: vi.fn(), end: vi.fn() };
  const { recognition: r } = createSpeechSession(FakeRecognition, "kn-IN", callbacks);
  r.onresult!({ resultIndex: 0, results: [{ isFinal: true, 0: { transcript: "unexpected" } }] });
  r.onerror!({ error: "language-not-supported" }); r.onend!();
  expect(callbacks.error).toHaveBeenCalledWith(ERRORS["language-not-supported"]);
  expect(callbacks.final).not.toHaveBeenCalled();
  expect(r.lang).toBe("kn-IN");
});

it("renders an accessible type-instead message when speech is unavailable", () => {
  const html = renderToStaticMarkup(<TextInput value="" onChange={vi.fn()} onTranslate={vi.fn()} busy={false} realtime={false} onRealtime={vi.fn()} mode="type" onMode={vi.fn()} speech={{ supported: false, listening: false, error: ERRORS.unavailable, start: vi.fn(), stop: vi.fn() }} lang="hi-IN" onLang={vi.fn()} hint={null} />);
  expect(html).toContain('role="alert"');
  expect(html).toContain("Speech recognition is unavailable in this browser. Please type instead.");
});

it("ignores delayed results and errors from a cancelled recognizer", () => {
  const callbacks = { interim: vi.fn(), final: vi.fn(), error: vi.fn(), end: vi.fn() };
  const { recognition, cancel } = createSpeechSession(FakeRecognition, "en-IN", callbacks);
  cancel();
  recognition.onresult!({ resultIndex: 0, results: [{ isFinal: true, 0: { transcript: "stale" } }] });
  recognition.onerror!({ error: "network" });
  recognition.onend!();
  for (const callback of Object.values(callbacks)) expect(callback).not.toHaveBeenCalled();
});
