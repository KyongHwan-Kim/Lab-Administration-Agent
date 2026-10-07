import { useState } from "react";
import { api } from "../api";
import { userLabel } from "../userLabel";
import { SignatureDialog } from "./SignatureDialog";

export function AccountPage({ user, onUserChange }) {
  return (
    <section className="max-w-xl space-y-10">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">내 계정</h1>
        <p className="mt-2 text-sm text-muted">이름, 비밀번호, 서명을 이 페이지에서 바꿉니다. 로그인 아이디는 {user.username}입니다.</p>
      </div>
      <NameForm user={user} onUserChange={onUserChange} />
      <PasswordForm />
      <SignatureDialog embedded page username={userLabel(user)} onSaved={onUserChange} />
    </section>
  );
}

function NameForm({ user, onUserChange }) {
  const [name, setName] = useState(userLabel(user));
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [pending, setPending] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setError("");
    setMessage("");
    setPending(true);
    try {
      const updated = await api("/api/users/me", {
        method: "PATCH",
        body: JSON.stringify({ name }),
      });
      onUserChange(updated);
      setName(userLabel(updated));
      setMessage("이름을 변경했습니다.");
    } catch (err) {
      setError(err.message);
    } finally {
      setPending(false);
    }
  }

  return (
    <form onSubmit={submit}>
      <h2 className="text-lg font-semibold">이름 변경</h2>
      <label className="mt-4 block text-sm font-medium" htmlFor="account-name">
        이름
      </label>
      <input
        id="account-name"
        required
        maxLength={80}
        value={name}
        onChange={(event) => setName(event.target.value)}
        className="mt-2 w-full rounded-xl border border-line bg-card px-3 py-3 outline-none focus:border-copper"
      />
      {error && <p className="mt-4 text-sm text-copper">{error}</p>}
      {message && <p className="mt-4 text-sm text-pine">{message}</p>}
      <button
        type="submit"
        disabled={pending}
        className="mt-4 rounded-xl bg-copper px-4 py-3 text-sm font-medium text-white disabled:opacity-60"
      >
        {pending ? "변경 중" : "이름 변경"}
      </button>
    </form>
  );
}

function PasswordForm() {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [pending, setPending] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setError("");
    setMessage("");
    if (newPassword !== confirmPassword) {
      setError("새 비밀번호가 서로 다릅니다.");
      return;
    }
    setPending(true);
    try {
      await api("/api/users/me/password", {
        method: "PATCH",
        body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
      });
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setMessage("비밀번호를 변경했습니다.");
    } catch (err) {
      setError(err.message);
    } finally {
      setPending(false);
    }
  }

  return (
    <form onSubmit={submit}>
      <h2 className="text-lg font-semibold">비밀번호 변경</h2>
      <label className="mt-4 block text-sm font-medium" htmlFor="current-password">
        현재 비밀번호
      </label>
      <input
        id="current-password"
        type="password"
        autoComplete="current-password"
        required
        value={currentPassword}
        onChange={(event) => setCurrentPassword(event.target.value)}
        className="mt-2 w-full rounded-xl border border-line bg-card px-3 py-3 outline-none focus:border-copper"
      />
      <label className="mt-4 block text-sm font-medium" htmlFor="new-password">
        새 비밀번호
      </label>
      <input
        id="new-password"
        type="password"
        autoComplete="new-password"
        required
        minLength={4}
        value={newPassword}
        onChange={(event) => setNewPassword(event.target.value)}
        className="mt-2 w-full rounded-xl border border-line bg-card px-3 py-3 outline-none focus:border-copper"
      />
      <label className="mt-4 block text-sm font-medium" htmlFor="confirm-password">
        새 비밀번호 확인
      </label>
      <input
        id="confirm-password"
        type="password"
        autoComplete="new-password"
        required
        minLength={4}
        value={confirmPassword}
        onChange={(event) => setConfirmPassword(event.target.value)}
        className="mt-2 w-full rounded-xl border border-line bg-card px-3 py-3 outline-none focus:border-copper"
      />
      {error && <p className="mt-4 text-sm text-copper">{error}</p>}
      {message && <p className="mt-4 text-sm text-pine">{message}</p>}
      <button
        type="submit"
        disabled={pending}
        className="mt-4 rounded-xl bg-copper px-4 py-3 text-sm font-medium text-white disabled:opacity-60"
      >
        {pending ? "변경 중" : "비밀번호 변경"}
      </button>
    </form>
  );
}
