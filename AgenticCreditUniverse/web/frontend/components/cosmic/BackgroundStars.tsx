"use client";

/**
 * BackgroundStars — Phase 4 ambient starfield + Phase 5 dark→light handoff.
 * Pure Canvas 2D, no external libs. 30fps throttle, visibility pause, DPR-aware.
 * Always mounts on /login (regardless of intro state).
 */

import {
  forwardRef,
  useEffect,
  useImperativeHandle,
  useRef,
} from "react";

export type BackgroundStarsHandle = {
  /** Phase 5: scatter stars + fade canvas tone, resolves when 700ms elapsed. */
  triggerHandoff: () => Promise<void>;
};

type Star = {
  x: number;          // CSS px (canvas internally scales by dpr)
  y: number;
  r: number;          // radius in CSS px
  baseAlpha: number;  // 0.3..0.7
  twinklePhase: number;
  twinkleSpeed: number;
  vx: number;
  vy: number;
  /** Phase 5 scatter velocity, set when handoff begins. */
  sx?: number;
  sy?: number;
};

type Shooting = {
  x: number;
  y: number;
  vx: number;
  vy: number;
  life: number;       // ms remaining
  maxLife: number;
};

const STAR_COUNT = 175;
const TARGET_FPS = 30;
const FRAME_MS = 1000 / TARGET_FPS;
const SHOOTING_PER_MIN = 2.5;          // average
const SHOOTING_SPAWN_PROB = SHOOTING_PER_MIN / (60 * TARGET_FPS); // per frame

export const BackgroundStars = forwardRef<BackgroundStarsHandle>(
  function BackgroundStars(_props, ref) {
    const canvasRef = useRef<HTMLCanvasElement | null>(null);
    const handoffStateRef = useRef<{ start: number; resolve: () => void } | null>(null);

    useImperativeHandle(ref, () => ({
      triggerHandoff() {
        return new Promise<void>((resolve) => {
          handoffStateRef.current = { start: performance.now(), resolve };
          // body class for the CSS bg fade — matched 700ms in globals.css.
          if (typeof document !== "undefined") {
            document.body.classList.add("cosmic-handoff");
          }
        });
      },
    }), []);

    useEffect(() => {
      const canvasEl = canvasRef.current;
      if (!canvasEl) return;
      const ctxMaybe = canvasEl.getContext("2d");
      if (!ctxMaybe) return;
      // TS strict: narrowed bindings don't propagate into nested function
      // declarations, so capture as explicitly non-null `const`.
      const canvas: HTMLCanvasElement = canvasEl;
      const ctx: CanvasRenderingContext2D = ctxMaybe;

      const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      let dpr = Math.max(1, window.devicePixelRatio || 1);
      let w = window.innerWidth;
      let h = window.innerHeight;

      const stars: Star[] = [];
      const shooting: Shooting[] = [];

      function spawnStars(count: number) {
        stars.length = 0;
        for (let i = 0; i < count; i++) {
          stars.push(makeStar());
        }
      }
      function makeStar(): Star {
        // depth 0..1 — far stars dimmer/smaller/slower.
        const depth = Math.random();
        const baseAlpha = 0.3 + depth * 0.4;
        const r = 0.4 + depth * 1.4;
        const speedScale = reduced ? 0 : (0.05 + depth * 0.15);
        const angle = Math.random() * Math.PI * 2;
        return {
          x: Math.random() * w,
          y: Math.random() * h,
          r,
          baseAlpha,
          twinklePhase: Math.random() * Math.PI * 2,
          twinkleSpeed: reduced ? 0.0005 : (0.0015 + Math.random() * 0.0035),
          vx: Math.cos(angle) * speedScale,
          vy: Math.sin(angle) * speedScale,
        };
      }

      function applySize() {
        dpr = Math.max(1, window.devicePixelRatio || 1);
        const newW = window.innerWidth;
        const newH = window.innerHeight;
        // Re-distribute existing stars to new ratio (no snap)
        if (stars.length > 0 && (newW !== w || newH !== h)) {
          const sx = newW / w;
          const sy = newH / h;
          for (const s of stars) {
            s.x *= sx;
            s.y *= sy;
          }
        }
        w = newW;
        h = newH;
        canvas.width = Math.floor(w * dpr);
        canvas.height = Math.floor(h * dpr);
        canvas.style.width = `${w}px`;
        canvas.style.height = `${h}px`;
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      }

      applySize();
      spawnStars(STAR_COUNT);

      let resizeTimer: number | null = null;
      function onResize() {
        if (resizeTimer != null) window.clearTimeout(resizeTimer);
        resizeTimer = window.setTimeout(applySize, 150);
      }
      window.addEventListener("resize", onResize);

      let raf = 0;
      let last = performance.now();
      let running = document.visibilityState !== "hidden";

      function spawnShooting() {
        // Random edge entry; diagonal across viewport in ~600ms.
        const fromTop = Math.random() < 0.5;
        const startX = fromTop ? Math.random() * w * 0.5 : -20;
        const startY = fromTop ? -20 : Math.random() * h * 0.5;
        const endX = startX + w * (0.6 + Math.random() * 0.4);
        const endY = startY + h * (0.5 + Math.random() * 0.5);
        const life = 600;
        shooting.push({
          x: startX,
          y: startY,
          vx: (endX - startX) / life,
          vy: (endY - startY) / life,
          life,
          maxLife: life,
        });
      }

      function loop(now: number) {
        raf = requestAnimationFrame(loop);
        if (!running) return;
        const dt = now - last;
        if (dt < FRAME_MS) return;
        last = now - (dt % FRAME_MS);

        // Phase 5 handoff progress (0..1)
        let handoffT = 0;
        let handoffActive = false;
        if (handoffStateRef.current) {
          handoffActive = true;
          handoffT = Math.min(1, (now - handoffStateRef.current.start) / 700);
          if (handoffT >= 1) {
            const resolve = handoffStateRef.current.resolve;
            handoffStateRef.current = null;
            resolve();
          }
        }

        // Background fill — base #08080d, fading to dashboard-light during handoff.
        // Drawn to keep stars over a solid backdrop (canvas itself is z=-1).
        ctx.clearRect(0, 0, w, h);
        if (handoffActive) {
          // Interpolate #08080d → #f8f8fc
          const r = Math.round(0x08 + (0xf8 - 0x08) * handoffT);
          const g = Math.round(0x08 + (0xf8 - 0x08) * handoffT);
          const b = Math.round(0x0d + (0xfc - 0x0d) * handoffT);
          ctx.fillStyle = `rgb(${r},${g},${b})`;
          ctx.fillRect(0, 0, w, h);
        }
        // (Otherwise the body's #08080d shows through — no need to fill.)

        // Drift + twinkle
        for (const s of stars) {
          if (handoffActive) {
            // Initialize scatter velocity from center on first handoff frame.
            if (s.sx === undefined || s.sy === undefined) {
              const dx = s.x - w / 2;
              const dy = s.y - h / 2;
              const len = Math.max(1, Math.hypot(dx, dy));
              const speed = 2 + Math.random() * 3; // px / frame
              s.sx = (dx / len) * speed;
              s.sy = (dy / len) * speed;
            }
            s.x += s.sx;
            s.y += s.sy;
          } else {
            s.x += s.vx;
            s.y += s.vy;
            // Wrap softly on edges.
            if (s.x < -2) s.x = w + 2;
            else if (s.x > w + 2) s.x = -2;
            if (s.y < -2) s.y = h + 2;
            else if (s.y > h + 2) s.y = -2;
          }
          s.twinklePhase += s.twinkleSpeed * dt;
          const twinkle = reduced ? 1 : (0.85 + Math.sin(s.twinklePhase) * 0.15);
          const fadeOut = handoffActive ? (1 - handoffT) : 1;
          const alpha = s.baseAlpha * twinkle * fadeOut;
          if (alpha <= 0.01) continue;
          ctx.globalAlpha = alpha;
          ctx.fillStyle = "#f0ebe0";
          ctx.beginPath();
          ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
          ctx.fill();
        }
        ctx.globalAlpha = 1;

        // Shooting stars (skip in reduced motion or during handoff)
        if (!reduced && !handoffActive) {
          if (Math.random() < SHOOTING_SPAWN_PROB) spawnShooting();
          for (let i = shooting.length - 1; i >= 0; i--) {
            const sh = shooting[i];
            sh.life -= dt;
            sh.x += sh.vx * dt;
            sh.y += sh.vy * dt;
            if (sh.life <= 0 || sh.x > w + 100 || sh.y > h + 100) {
              shooting.splice(i, 1);
              continue;
            }
            const lifeT = sh.life / sh.maxLife; // 1..0
            const tailLen = 60;
            const grad = ctx.createLinearGradient(
              sh.x, sh.y,
              sh.x - sh.vx * tailLen, sh.y - sh.vy * tailLen,
            );
            grad.addColorStop(0, `rgba(240,235,224,${0.9 * lifeT})`);
            grad.addColorStop(1, "rgba(240,235,224,0)");
            ctx.strokeStyle = grad;
            ctx.lineWidth = 1.2;
            ctx.beginPath();
            ctx.moveTo(sh.x, sh.y);
            ctx.lineTo(sh.x - sh.vx * tailLen, sh.y - sh.vy * tailLen);
            ctx.stroke();
          }
        }
      }

      function onVisibility() {
        running = document.visibilityState !== "hidden";
        if (running) last = performance.now();
      }
      document.addEventListener("visibilitychange", onVisibility);

      raf = requestAnimationFrame(loop);

      return () => {
        cancelAnimationFrame(raf);
        window.removeEventListener("resize", onResize);
        document.removeEventListener("visibilitychange", onVisibility);
        if (resizeTimer != null) window.clearTimeout(resizeTimer);
        // Defensive: clear handoff body class on unmount.
        if (typeof document !== "undefined") {
          document.body.classList.remove("cosmic-handoff");
        }
      };
    }, []);

    return (
      <canvas
        ref={canvasRef}
        aria-hidden="true"
        style={{
          position: "fixed",
          inset: 0,
          zIndex: -1,
          pointerEvents: "none",
        }}
      />
    );
  },
);
