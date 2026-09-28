import { useState } from "react";

import { adminLogin } from "@/api/admin";
import { ApiError } from "@/api/client";
import { setAdminToken } from "@/api/token";

export function AdminLogin({ onLoggedIn }: { onLoggedIn: () => void }) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const { access_token } = await adminLogin(password);
      setAdminToken(access_token);
      onLoggedIn();
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setError("Неверный пароль");
      } else if (err instanceof ApiError && err.status === 429) {
        setError("Слишком много попыток. Подожди минуту.");
      } else {
        setError("Не удалось связаться с сервером");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto flex min-h-screen max-w-sm flex-col justify-center gap-4 px-4">
      <h1 className="text-xl font-semibold">Вход для организации</h1>
      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Пароль"
          className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
          autoFocus
        />
        {error && <p className="text-sm text-red-500">{error}</p>}
        <button
          type="submit"
          disabled={loading}
          className="rounded-lg bg-brand-500 px-4 py-3 text-center text-sm font-medium text-white disabled:opacity-60"
        >
          {loading ? "Входим..." : "Войти"}
        </button>
      </form>
    </div>
  );
}
