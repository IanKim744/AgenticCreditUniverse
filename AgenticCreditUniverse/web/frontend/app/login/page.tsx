"use client";

import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { Loader2 } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import {
  BackgroundStars,
  type BackgroundStarsHandle,
} from "@/components/cosmic/BackgroundStars";
import { IntroOverlay } from "@/components/cosmic/IntroOverlay";
import { runLoginHandoff } from "@/components/cosmic/cosmicTransition";

// useSyncExternalStore + a no-op subscribe — pure client-side check that
// satisfies the React Compiler `set-state-in-effect` rule.
//
// Server snapshot returns `true` (worst case = intro WILL play) so SSR
// renders all reveal targets with opacity:0 — prevents the flash of the
// form briefly appearing before the intro hides it on hydration.
//
// Demo context: every visit replays the intro for ALL users — even those
// with `prefers-reduced-motion`. The 7.6s swirl is the signature motion
// judges will see, and we cannot afford OS accessibility settings to silently
// strip it. Trade-off accepted: a11y < demo first-impression here.
const NO_OP_SUBSCRIBE = () => () => {};
function shouldPlayIntroSnapshot(): boolean {
  return true;
}

const HERO_FONT_FAMILY =
  "var(--font-eb-garamond), Garamond, Georgia, 'Times New Roman', serif";

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const shouldPlayIntro = useSyncExternalStore(
    NO_OP_SUBSCRIBE,
    shouldPlayIntroSnapshot,
    () => true,
  );
  const [introCompleted, setIntroCompleted] = useState(false);
  const introDone = !shouldPlayIntro || introCompleted;

  const bgRef = useRef<BackgroundStarsHandle>(null);
  const cardRef = useRef<HTMLDivElement | null>(null);
  const usernameInputRef = useRef<HTMLInputElement | null>(null);

  // body cosmic-mode toggle, scoped to /login mount.
  useEffect(() => {
    document.body.classList.add("cosmic-mode");
    return () => {
      document.body.classList.remove("cosmic-mode");
      document.body.classList.remove("cosmic-handoff");
    };
  }, []);

  // Defer autofocus until the form is actually visible.
  useEffect(() => {
    if (introDone) usernameInputRef.current?.focus();
  }, [introDone]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const fd = new FormData();
      fd.set("username", username);
      fd.set("password", password);
      const res = await fetch("/api/auth/login", { method: "POST", body: fd });
      if (!res.ok) {
        setError("Invalid username or password.");
        setLoading(false);
        return;
      }
      await runLoginHandoff({
        bgRef,
        cardEl: cardRef.current,
        onMidFade: () => {
          window.location.href = "/";
        },
      });
    } catch {
      setError("Cannot reach the server.");
      setLoading(false);
    }
  }

  // Shared cinematic reveal — used by hero, corner labels, and card.
  // 3s ease-out-expo so each element drifts in unhurriedly. The reveal begins
  // at IntroOverlay's T_REVEAL_TRIGGER (~1.3s into the 3s star fade) for a
  // long, soft crossfade — eliminates the "딱딱한 (rigid)" pop the user reported.
  const revealStyle: React.CSSProperties = {
    opacity: introDone ? 1 : 0,
    transform: introDone ? "translateY(0)" : "translateY(10px)",
    transition:
      "opacity 3000ms cubic-bezier(0.16, 1, 0.3, 1), transform 3000ms cubic-bezier(0.16, 1, 0.3, 1)",
  };
  // Stagger order: corner labels frame the page first, then the hero anchors
  // the brand, finally the card invites action. Wider gaps scale with the
  // longer 3s reveal so the sequence stays perceptible.
  const cornerStyle: React.CSSProperties = {
    ...revealStyle,
    transitionDelay: "0ms",
  };
  const heroStyle: React.CSSProperties = {
    ...revealStyle,
    transitionDelay: "300ms",
  };
  const cardStyle: React.CSSProperties = {
    ...revealStyle,
    transitionDelay: "600ms",
  };

  return (
    <main className="relative min-h-screen overflow-hidden">
      <BackgroundStars ref={bgRef} />
      {!introDone && <IntroOverlay onComplete={() => setIntroCompleted(true)} />}

      {/* Top-left wordmark */}
      <p
        className="absolute top-7 left-8 sm:top-9 sm:left-12 text-sm sm:text-base font-medium tracking-tight"
        style={{
          color: "rgba(240, 235, 224, 0.85)",
          ...cornerStyle,
        }}
      >
        Global No.1 RWA Hub
      </p>

      {/* Top-right wordmark */}
      <p
        className="absolute top-7 right-8 sm:top-9 sm:right-12 text-sm sm:text-base font-medium tracking-tight"
        style={{
          color: "rgba(240, 235, 224, 0.85)",
          ...cornerStyle,
        }}
      >
        Credit Intelligence Platform
      </p>

      {/* Center column — hero + form, both center-aligned */}
      <div className="min-h-screen flex flex-col items-center justify-center px-6 pt-24 pb-16">
        <h1
          className="text-center italic font-normal whitespace-nowrap"
          style={{
            fontFamily: HERO_FONT_FAMILY,
            color: "#f5efe2",
            fontSize: "clamp(48px, 9vw, 128px)",
            lineHeight: 1.05,
            letterSpacing: "-0.015em",
            textShadow: "0 1px 40px rgba(245, 239, 226, 0.18)",
            ...heroStyle,
          }}
        >
          Hanwha Credit Universe
        </h1>

        <div
          className="mt-14 sm:mt-16 w-full max-w-[400px] relative"
          style={cardStyle}
        >
          {/* Soft radial glow anchoring the card */}
          <div
            aria-hidden
            className="absolute inset-0 -z-10"
            style={{
              background:
                "radial-gradient(ellipse at center, rgba(240, 235, 224, 0.07) 0%, rgba(240, 235, 224, 0) 70%)",
              filter: "blur(40px)",
              transform: "scale(1.4)",
            }}
          />
          <Card
            ref={cardRef}
            className="rounded-2xl p-9"
            style={{
              background: "rgba(255, 255, 255, 0.035)",
              borderColor: "rgba(255, 255, 255, 0.08)",
              backdropFilter: "blur(18px) saturate(140%)",
              WebkitBackdropFilter: "blur(18px) saturate(140%)",
              boxShadow:
                "0 30px 80px -30px rgba(0, 0, 0, 0.7), inset 0 1px 0 rgba(255, 255, 255, 0.06)",
            }}
          >
            <form onSubmit={onSubmit} className="space-y-5">
              <div className="space-y-2">
                <Label
                  htmlFor="username"
                  className="text-[10px] font-medium uppercase"
                  style={{
                    color: "rgba(255, 255, 255, 0.5)",
                    letterSpacing: "0.18em",
                  }}
                >
                  Username
                </Label>
                <Input
                  id="username"
                  ref={usernameInputRef}
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  autoComplete="username"
                  className="h-11 text-white placeholder:text-white/25"
                  style={{
                    background: "rgba(255, 255, 255, 0.04)",
                    borderColor: "rgba(255, 255, 255, 0.10)",
                    borderRadius: "8px",
                  }}
                />
              </div>
              <div className="space-y-2">
                <Label
                  htmlFor="password"
                  className="text-[10px] font-medium uppercase"
                  style={{
                    color: "rgba(255, 255, 255, 0.5)",
                    letterSpacing: "0.18em",
                  }}
                >
                  Password
                </Label>
                <Input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                  className="h-11 text-white placeholder:text-white/25"
                  style={{
                    background: "rgba(255, 255, 255, 0.04)",
                    borderColor: "rgba(255, 255, 255, 0.10)",
                    borderRadius: "8px",
                  }}
                />
              </div>
              {error && (
                <div
                  className="rounded-lg p-3 text-sm"
                  style={{
                    color: "#fca5a5",
                    background: "rgba(248, 113, 113, 0.06)",
                    border: "1px solid rgba(248, 113, 113, 0.30)",
                  }}
                >
                  {error}
                </div>
              )}
              <Button
                type="submit"
                className="w-full h-11 text-white font-medium tracking-wide"
                style={{
                  background: "rgba(255, 255, 255, 0.10)",
                  border: "1px solid rgba(255, 255, 255, 0.16)",
                  borderRadius: "8px",
                }}
                disabled={loading}
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Signing in…
                  </>
                ) : (
                  "Sign in"
                )}
              </Button>
            </form>
          </Card>
        </div>
      </div>
    </main>
  );
}
