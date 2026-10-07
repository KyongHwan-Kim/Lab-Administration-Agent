import { useState, useEffect } from "react";
import { api } from "../api";
import { userLabel } from "../userLabel";
import { SignatureDialog } from "./SignatureDialog";

export function UserAdmin({ currentUserId, onCurrentUser }) {
  const [users, setUsers] = useState([]);
  const [signatureUser, setSignatureUser] = useState(null);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [pending, setPending] = useState(false);

  async function load() {
    setUsers(await api("/api/users"));
  }

  useEffect(() => {
    load().catch((err) => setError(err.message));
  }, []);

  async function submit(event) {
    event.preventDefault();
    setError("");
    setMessage("");
    setPending(true);
    try {
      await api("/api/users", {
        method: "POST",
        body: JSON.stringify({ name, email, username, password }),
      });
      setName("");
      setEmail("");
      setUsername("");
      setPassword("");
      setMessage("사용자를 등록했습니다.");
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setPending(false);
    }
  }

  return (
    <section>
      <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">사용자 등록</h1>
      <p className="mt-2 text-sm text-muted">이름, 이메일, 아이디, 비밀번호로 계정을 만들고 등록된 사용자를 확인합니다.</p>
      <form onSubmit={submit} className="mt-5 grid max-w-3xl gap-3 sm:grid-cols-2">
          <label className="text-sm">
            이름
            <input
              required
              value={name}
              onChange={(event) => setName(event.target.value)}
              className="mt-1 w-full rounded-xl border border-line px-3 py-2"
            />
          </label>
          <label className="text-sm">
            이메일
            <input
              required
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="mt-1 w-full rounded-xl border border-line px-3 py-2"
            />
          </label>
          <label className="text-sm">
            아이디
            <input
              required
              minLength={2}
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              className="mt-1 w-full rounded-xl border border-line px-3 py-2"
            />
          </label>
          <label className="text-sm">
            비밀번호
            <input
              required
              minLength={4}
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="mt-1 w-full rounded-xl border border-line px-3 py-2"
            />
          </label>
          <button
            type="submit"
            disabled={pending}
            className="rounded-xl bg-ink px-4 py-2 text-sm text-white sm:col-span-2"
          >
            {pending ? "등록 중" : "등록"}
          </button>
        </form>
        {error && <p className="mt-3 text-sm text-copper">{error}</p>}
        {message && <p className="mt-3 text-sm text-pine">{message}</p>}
        <h2 className="mt-8 text-lg font-semibold">등록된 사용자</h2>
        <p className="mt-1 text-sm text-muted">{users.length}명</p>
        {users.length === 0 && <p className="mt-3 text-sm text-muted">등록된 사용자가 없습니다.</p>}
        <ul className="mt-3 max-w-3xl divide-y divide-line rounded-2xl border border-line bg-white">
          {users.map((user) => (
            <li key={user.id} className="flex items-center justify-between gap-3 px-3 py-2 text-sm">
              <span>
                {userLabel(user)}
                <span className="mt-0.5 block text-xs text-muted">
                  {[
                    userLabel(user) === user.username ? "" : user.username,
                    user.email,
                    user.is_admin ? "관리자" : "사용자",
                    user.has_signature ? "서명 있음" : "서명 없음",
                  ]
                    .filter(Boolean)
                    .join(" · ")}
                </span>
              </span>
              <button
                type="button"
                className="shrink-0 rounded-lg border border-line px-2 py-1 text-xs"
                onClick={() => setSignatureUser(user)}
              >
                서명
              </button>
            </li>
          ))}
        </ul>
        {signatureUser && (
          <SignatureDialog
            userId={signatureUser.id}
            username={userLabel(signatureUser)}
            onClose={() => setSignatureUser(null)}
            onSaved={(updated) => {
              if (updated.id === currentUserId) onCurrentUser(updated);
              setSignatureUser(null);
              load().catch((err) => setError(err.message));
            }}
          />
        )}
    </section>
  );
}
