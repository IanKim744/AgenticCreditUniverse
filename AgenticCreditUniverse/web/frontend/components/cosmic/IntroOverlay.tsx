"use client";

/**
 * IntroOverlay — one-shot login intro.
 *  Phase 1 (0–T_SWIRL_END): swirl 250 stars + 120 dust on a fixed overlay canvas.
 *    Slow polar rotation (~9–23°/sec for stars, ~6°/sec for dust) — meditative.
 *  Phase 2 (T_SWIRL_END–T_FADE_END): swirl continues, particles fade out over
 *    4s with a LINEAR curve. Linear (vs cubic ease-in) means the visible
 *    decrease is uniform across the whole 4s — no concentrated drop at the
 *    end that would feel sudden.
 *  Reveal trigger fires at T_REVEAL_TRIGGER (~45% into the fade) so the UI
 *    begins emerging while stars are still visibly receding. The 3s reveal
 *    duration on the LoginPage side completes after the stars are gone,
 *    creating a long, soft crossfade with no abrupt cut.
 *  At T_FADE_END the canvas removes itself from the DOM. Each visit replays
 *  the intro — the swirl is signature motion + the demo's first impression,
 *  so showing it every time is intentional (not a bug).
 *
 * Caller is responsible for *not* mounting this when prefers-reduced-motion
 * is set — see LoginPage.
 */

import { useEffect, useRef } from "react";

export const STAR_COUNT = 250;
export const DUST_COUNT = 120;

const T_SWIRL_END = 2200;       // swirl duration — contemplative opening
const T_REVEAL_TRIGGER = 4000;  // 1800ms into fade (~45%) — UI begins emerging
const T_FADE_END = 6200;        // 4000ms LINEAR fade end, canvas removed

type Particle = {
  cx: number; cy: number;       // center of orbit (viewport center)
  r: number;                    // orbit radius
  theta: number;                // current angle
  omega: number;                // angular speed (rad / frame, integrated against dt)
  jitter: number;               // organic noise amplitude
  jitterPhase: number;
  size: number;
  alpha: number;                // base alpha
};

type IntroOverlayProps = {
  /** Fired at T_REVEAL_TRIGGER (~45% into fade) so the form + title begin
   * fading in while stars are still visibly receding (long crossfade). */
  onComplete: () => void;
};

export function IntroOverlay({ onComplete }: IntroOverlayProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvasEl = canvasRef.current;
    if (!canvasEl) return;
    const ctxMaybe = canvasEl.getContext("2d");
    if (!ctxMaybe) return;
    // TS strict: narrowed bindings don't propagate into nested function
    // declarations, so capture as explicitly non-null `const`.
    const canvas: HTMLCanvasElement = canvasEl;
    const ctx: CanvasRenderingContext2D = ctxMaybe;

    let dpr = Math.max(1, window.devicePixelRatio || 1);
    let w = window.innerWidth;
    let h = window.innerHeight;
    let completed = false;

    function applySize() {
      dpr = Math.max(1, window.devicePixelRatio || 1);
      w = window.innerWidth;
      h = window.innerHeight;
      canvas.width = Math.floor(w * dpr);
      canvas.height = Math.floor(h * dpr);
      canvas.style.width = `${w}px`;
      canvas.style.height = `${h}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    applySize();

    function makeStar(isDust: boolean): Particle {
      const r = isDust
        ? 80 + Math.random() * Math.min(w, h) * 0.45
        : 60 + Math.random() * Math.min(w, h) * 0.38;
      const theta = Math.random() * Math.PI * 2;
      const dirSign = Math.random() < 0.5 ? -1 : 1;
      // Slow polar rotation — meditative drift, not mechanical spin.
      // Stars: 0.15–0.40 rad/sec (~9–23°/sec). Dust: 0.10 rad/sec (~6°/sec).
      const omega = (isDust ? 0.10 : 0.15 + Math.random() * 0.25) * dirSign;
      return {
        cx: w / 2,
        cy: h / 2,
        r,
        theta,
        omega,
        jitter: 8 + Math.random() * 22,
        jitterPhase: Math.random() * Math.PI * 2,
        size: isDust ? 0.5 + Math.random() * 0.6 : 0.8 + Math.random() * 1.4,
        alpha: isDust ? 0.25 + Math.random() * 0.25 : 0.7 + Math.random() * 0.3,
      };
    }

    const stars: Particle[] = [];
    for (let i = 0; i < STAR_COUNT; i++) stars.push(makeStar(false));
    const dust: Particle[] = [];
    for (let i = 0; i < DUST_COUNT; i++) dust.push(makeStar(true));

    let resizeTimer: number | null = null;
    function onResize() {
      if (resizeTimer != null) window.clearTimeout(resizeTimer);
      resizeTimer = window.setTimeout(() => {
        const oldCx = w / 2;
        const oldCy = h / 2;
        applySize();
        const dxc = w / 2 - oldCx;
        const dyc = h / 2 - oldCy;
        for (const s of [...stars, ...dust]) {
          s.cx += dxc;
          s.cy += dyc;
        }
      }, 150);
    }
    window.addEventListener("resize", onResize);

    let raf = 0;
    let startTime = performance.now();
    let lastVisCheck = startTime;

    function loop(now: number) {
      raf = requestAnimationFrame(loop);

      // Visibility pause: shift startTime forward so the timeline doesn't jump.
      if (document.visibilityState === "hidden") {
        lastVisCheck = now;
        return;
      }
      if (now - lastVisCheck > 100 && lastVisCheck !== startTime) {
        startTime += (now - lastVisCheck);
      }
      lastVisCheck = now;

      const elapsed = now - startTime;
      ctx.clearRect(0, 0, w, h);

      // Global fade multiplier — 1 during swirl, then LINEAR toward 0.
      // Linear distributes the visible decrease evenly across the whole 4s
      // window so no part of the fade feels concentrated or sudden. Cubic
      // ease-in (previous) lingered at full alpha and dropped fast at the
      // end, which the user perceived as rushed.
      let fadeAlpha = 1;
      if (elapsed >= T_SWIRL_END) {
        const t = Math.min(1, (elapsed - T_SWIRL_END) / (T_FADE_END - T_SWIRL_END));
        fadeAlpha = 1 - t;
      }

      // Fire reveal once — partway into Phase 2 so the form crossfades with
      // the receding stars instead of waiting for the void.
      if (!completed && elapsed >= T_REVEAL_TRIGGER) {
        completed = true;
        onComplete();
      }

      // Dust (slower, dimmer)
      for (const d of dust) {
        d.theta += d.omega * (1 / 60);
        d.jitterPhase += 0.04;
        const x = d.cx + Math.cos(d.theta) * d.r + Math.sin(d.jitterPhase) * d.jitter;
        const y = d.cy + Math.sin(d.theta) * d.r + Math.cos(d.jitterPhase) * d.jitter;
        const a = d.alpha * fadeAlpha;
        if (a < 0.01) continue;
        ctx.globalAlpha = a;
        ctx.fillStyle = "#f0ebe0";
        ctx.beginPath();
        ctx.arc(x, y, d.size, 0, Math.PI * 2);
        ctx.fill();
      }

      // Stars
      for (const s of stars) {
        s.theta += s.omega * (1 / 60);
        s.jitterPhase += 0.05;
        const x = s.cx + Math.cos(s.theta) * s.r + Math.sin(s.jitterPhase) * s.jitter;
        const y = s.cy + Math.sin(s.theta) * s.r + Math.cos(s.jitterPhase) * s.jitter;
        const a = s.alpha * fadeAlpha;
        if (a < 0.01) continue;
        ctx.globalAlpha = a;
        ctx.fillStyle = "#f0ebe0";
        ctx.beginPath();
        ctx.arc(x, y, s.size, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.globalAlpha = 1;

      // Done — remove canvas from DOM and stop the loop.
      if (elapsed >= T_FADE_END) {
        cancelAnimationFrame(raf);
        window.removeEventListener("resize", onResize);
        if (resizeTimer != null) window.clearTimeout(resizeTimer);
        if (canvas.parentNode) canvas.parentNode.removeChild(canvas);
      }
    }

    raf = requestAnimationFrame(loop);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", onResize);
      if (resizeTimer != null) window.clearTimeout(resizeTimer);
    };
    // `onComplete` is captured once at mount — re-creating the RAF mid-animation
    // would lose state. The intro is a one-shot effect by design.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden="true"
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 50,
        pointerEvents: "none",
      }}
    />
  );
}
