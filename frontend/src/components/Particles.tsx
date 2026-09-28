import { useEffect, useRef } from "react";

interface Orb { x: number; y: number; r: number; vx: number; vy: number; ph: number; sw: number; tw: number; hue: number; depth: number; alpha: number }
const TAU = Math.PI * 2;
const HUES = [238, 252, 266, 282, 205, 190]; // indigo → violet → sky, matches the accent palette

/** Fixed full-screen canvas of fine, softly glowing particles. Pointer-transparent, pauses when the tab is hidden,
 *  drifts with a soft mouse parallax, and renders a single static frame under prefers-reduced-motion. */
export default function Particles({ dark }: { dark: boolean }) {
  const ref = useRef<HTMLCanvasElement>(null);
  const darkRef = useRef(dark);
  const redraw = useRef<() => void>(() => {});
  darkRef.current = dark;

  useEffect(() => {
    const cv = ref.current!;
    const ctx = cv.getContext("2d");
    if (!ctx) return;
    const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
    let w = 0, h = 0, raf = 0, last = 0;
    let orbs: Orb[] = [];
    const mouse = { x: 0, y: 0, tx: 0, ty: 0 };

    const make = (): Orb => {
      const far = Math.random() < .12; // a few large, very faint out-of-focus specks for depth
      const r = far ? 6 + Math.random() * 8 : .7 + Math.random() * 1.5;
      const depth = far ? .2 : .4 + Math.random() * .6;
      return {
        x: Math.random() * w, y: Math.random() * h, r, depth,
        vx: (Math.random() - .5) * .05, vy: -(.04 + Math.random() * .12) * (far ? .5 : 1),
        ph: Math.random() * TAU, sw: .5 + Math.random(), tw: .5 + Math.random() * .7,
        hue: HUES[Math.floor(Math.random() * HUES.length)],
        alpha: far ? .5 : .55 + Math.random() * .45,
      };
    };
    const target = () => Math.min(80, Math.max(24, Math.floor((w * h) / 16000)));

    const resize = () => {
      const dpr = Math.min(2, window.devicePixelRatio || 1);
      const ow = w || innerWidth, oh = h || innerHeight;
      w = innerWidth; h = innerHeight;
      cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      orbs.forEach((o) => { o.x *= w / ow; o.y *= h / oh; });
      const n = target();
      while (orbs.length < n) orbs.push(make());
      if (orbs.length > n) orbs = orbs.slice(0, n);
      if (reduce) draw(0);
    };

    const draw = (t: number) => {
      const d = darkRef.current;
      ctx.clearRect(0, 0, w, h);
      ctx.globalCompositeOperation = d ? "lighter" : "source-over";
      for (const o of orbs) {
        const px = o.x + mouse.x * o.depth * 14, py = o.y + mouse.y * o.depth * 14;
        const a = o.alpha * (.7 + .3 * Math.sin(t * .0008 * o.tw + o.ph));
        const far = o.r > 4;
        const L = d ? 72 : 52;
        if (far) { // soft bokeh: no edge, just a faint radial fade
          const g = ctx.createRadialGradient(px, py, 0, px, py, o.r * 2);
          g.addColorStop(0, `hsla(${o.hue},85%,${L}%,${(d ? .10 : .07) * a})`);
          g.addColorStop(1, `hsla(${o.hue},85%,${L}%,0)`);
          ctx.fillStyle = g; ctx.beginPath(); ctx.arc(px, py, o.r * 2, 0, TAU); ctx.fill();
          continue;
        }
        // fine point with a soft halo
        const g = ctx.createRadialGradient(px, py, 0, px, py, o.r * 7);
        g.addColorStop(0, `hsla(${o.hue},90%,${L}%,${(d ? .32 : .22) * a})`);
        g.addColorStop(1, `hsla(${o.hue},90%,${L}%,0)`);
        ctx.fillStyle = g; ctx.beginPath(); ctx.arc(px, py, o.r * 7, 0, TAU); ctx.fill();
        ctx.fillStyle = d ? `rgba(255,255,255,${.75 * a})` : `hsla(${o.hue},80%,45%,${.55 * a})`;
        ctx.beginPath(); ctx.arc(px, py, o.r, 0, TAU); ctx.fill();
      }
      ctx.globalCompositeOperation = "source-over";
    };

    const step = (now: number) => {
      const dt = last ? Math.min(50, now - last) / 16.67 : 1; last = now;
      mouse.x += (mouse.tx - mouse.x) * .05; mouse.y += (mouse.ty - mouse.y) * .05;
      for (const o of orbs) {
        o.x += (o.vx + Math.sin(now * .0004 * o.sw + o.ph) * .12) * dt;
        o.y += o.vy * dt;
        const m = o.r * 7;
        if (o.y < -m) { o.y = h + m; o.x = Math.random() * w; }
        if (o.x < -m) o.x = w + m; else if (o.x > w + m) o.x = -m;
      }
      draw(now);
      raf = requestAnimationFrame(step);
    };
    const start = () => { if (!reduce && !raf) { last = 0; raf = requestAnimationFrame(step); } };
    const stop = () => { cancelAnimationFrame(raf); raf = 0; };
    const onMove = (e: PointerEvent) => { mouse.tx = e.clientX / w - .5; mouse.ty = e.clientY / h - .5; };
    const onVis = () => (document.hidden ? stop() : start());

    redraw.current = () => { if (reduce) draw(0); };
    resize(); start();
    window.addEventListener("resize", resize);
    window.addEventListener("pointermove", onMove, { passive: true });
    document.addEventListener("visibilitychange", onVis);
    return () => { stop(); window.removeEventListener("resize", resize); window.removeEventListener("pointermove", onMove); document.removeEventListener("visibilitychange", onVis); };
  }, []);

  useEffect(() => { redraw.current(); }, [dark]);

  return <canvas ref={ref} aria-hidden className="pointer-events-none fixed inset-0 -z-10 h-full w-full" />;
}