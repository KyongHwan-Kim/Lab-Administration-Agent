import { useState } from "react";
import { api } from "../api";
import logo from "../assets/logo.png";
import { BrandLogo } from "./BrandLogo";

export function LoginScreen({ onSuccess }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setError("");
    setPending(true);
    try {
      const user = await api("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      });
      onSuccess(user);
    } catch (err) {
      setError(err.message);
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-2">
      <section className="flex flex-col justify-between bg-ink px-8 py-10 text-white sm:px-12">
        <BrandLogo className="h-12 w-auto max-w-full self-start sm:h-14" />
        <div className="py-10">
          <h1>
            <img src={logo} alt="연구실 행정" className="h-14 w-auto max-w-full sm:h-20" />
          </h1>
          <p className="mt-6 max-w-md text-base leading-7 text-white/75">연구 행정을 쉽고 빠르게 도와드립니다</p>
        </div>
        <p className="text-sm text-white/40">Lab Administration</p>
      </section>
      <section className="grid place-items-center px-6 py-12">
        <form onSubmit={submit} className="w-full max-w-sm">
          <h2 className="text-2xl font-semibold">로그인</h2>
          <p className="mt-2 text-sm text-muted">아이디와 비밀번호를 입력해 주세요.</p>
          <label className="mt-8 block text-sm font-medium" htmlFor="username">
            아이디
          </label>
          <input
            id="username"
            autoComplete="username"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            className="mt-2 w-full rounded-xl border border-line bg-card px-3 py-3 outline-none focus:border-copper"
          />
          <label className="mt-4 block text-sm font-medium" htmlFor="password">
            비밀번호
          </label>
          <input
            id="password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="mt-2 w-full rounded-xl border border-line bg-card px-3 py-3 outline-none focus:border-copper"
          />
          {error && <p className="mt-4 text-sm text-copper">{error}</p>}
          <button
            type="submit"
            disabled={pending}
            className="mt-6 w-full rounded-xl bg-copper px-4 py-3 font-medium text-white hover:bg-copper-dark disabled:opacity-60"
          >
            {pending ? "확인 중" : "로그인"}
          </button>
        </form>
      </section>
    </div>
  );
}
