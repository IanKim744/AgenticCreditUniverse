"use client";

/**
 * runLoginHandoff — Phase 5 dark→light transition.
 *
 * Choreography (700ms total):
 *   t=0      card starts dissolving (CSS transition: opacity 1→0, scale 1→1.04)
 *   t=0      bgRef.triggerHandoff() begins — stars scatter + canvas tone
 *            interpolates #08080d → #f8f8fc; body.cosmic-handoff fades the
 *            CSS body bg toward var(--background) (matched 700ms in globals.css).
 *   t=550    onMidFade() — caller usually calls window.location.href = "/"
 *            so the new page loads while the screen is mostly white.
 *   t=700    triggerHandoff promise resolves; helper itself returns.
 */

import type { RefObject } from "react";
import type { BackgroundStarsHandle } from "./BackgroundStars";

type HandoffOpts = {
  bgRef: RefObject<BackgroundStarsHandle | null>;
  cardEl: HTMLElement | null;
  onMidFade: () => void;
};

export async function runLoginHandoff(opts: HandoffOpts): Promise<void> {
  const { bgRef, cardEl, onMidFade } = opts;

  // Reduced motion: skip the choreography, just call onMidFade immediately.
  if (typeof window !== "undefined") {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      onMidFade();
      return;
    }
  }

  // Card dissolve — set inline transition + transform/opacity targets.
  if (cardEl) {
    cardEl.style.transition = "opacity 600ms ease-out, transform 600ms ease-out";
    cardEl.style.opacity = "0";
    cardEl.style.transform = "scale(1.04)";
  }

  const handoffPromise = bgRef.current
    ? bgRef.current.triggerHandoff()
    : Promise.resolve();

  // Fire navigation when the screen is ~80% faded so the new page loads under
  // the white veil.
  const midFadeTimer = window.setTimeout(() => {
    try { onMidFade(); } catch { /* navigation can throw mid-unload, ignore */ }
  }, 550);

  try {
    await handoffPromise;
  } finally {
    window.clearTimeout(midFadeTimer);
  }
}
