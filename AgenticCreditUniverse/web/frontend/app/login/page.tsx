"use client";

import { useState } from "react";
import { Loader2 } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const fd = new FormData();
      fd.set("username", username);
      fd.set("password", password);
      const res = await fetch("/api/auth/login", {
        method: "POST",
        body: fd,
      });
      if (!res.ok) {
        setError("아이디 또는 비밀번호가 올바르지 않습니다.");
        return;
      }
      window.location.href = "/";
    } catch (_err) {
      setError("서버에 연결할 수 없습니다.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen flex items-center justify-center bg-background px-6">
      <Card
        className="w-full max-w-sm rounded-xl border bg-card p-8"
        style={{ boxShadow: "var(--shadow-elevated)" }}
      >
        <div className="flex flex-col items-center text-center mb-8">
          <h1 className="text-3xl font-semibold tracking-tight">
            Credit Universe
          </h1>
        </div>
        <form onSubmit={onSubmit} className="space-y-3">
          <div className="space-y-1">
            <Label
              htmlFor="username"
              className="text-xs font-medium text-muted-foreground"
            >
              아이디
            </Label>
            <Input
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoFocus
              autoComplete="username"
            />
          </div>
          <div className="space-y-1">
            <Label
              htmlFor="password"
              className="text-xs font-medium text-muted-foreground"
            >
              비밀번호
            </Label>
            <Input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
            />
          </div>
          {error && (
            <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
              {error}
            </div>
          )}
          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                로그인 중…
              </>
            ) : (
              "로그인"
            )}
          </Button>
        </form>
      </Card>
    </main>
  );
}
