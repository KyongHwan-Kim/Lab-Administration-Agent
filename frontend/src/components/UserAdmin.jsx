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
  const [bulkOpen, setBulkOpen] = useState(false);

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
          <div className="flex flex-wrap gap-2 sm:col-span-2">
            <button
              type="submit"
              disabled={pending}
              className="rounded-xl bg-ink px-4 py-2 text-sm text-white disabled:opacity-60"
            >
              {pending ? "등록 중" : "등록"}
            </button>
            <button
              type="button"
              className="rounded-xl border border-line bg-white px-4 py-2 text-sm"
              onClick={() => setBulkOpen(true)}
            >
              여러 명 등록
            </button>
          </div>
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
        {bulkOpen && (
          <BulkRegisterModal
            onClose={() => setBulkOpen(false)}
            onDone={async (summary) => {
              setError("");
              setMessage(summary);
              await load();
            }}
          />
        )}
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

function BulkRegisterModal({ onClose, onDone }) {
  const [text, setText] = useState("");
  const [error, setError] = useState("");
  const [rowErrors, setRowErrors] = useState([]);
  const [pending, setPending] = useState(false);
  const parsed = parseBulkUsers(text);

  function loadFile(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => setText(String(reader.result || ""));
    reader.readAsText(file);
  }

  async function submit(event) {
    event.preventDefault();
    setError("");
    setRowErrors([]);
    if (!parsed.users.length && !parsed.errors.length) {
      setError("등록할 사용자를 입력해 주세요.");
      return;
    }
    if (parsed.errors.length) {
      setError("형식이 맞지 않는 줄이 있습니다.");
      setRowErrors(parsed.errors);
      return;
    }
    setPending(true);
    try {
      const result = await api("/api/users/bulk", {
        method: "POST",
        body: JSON.stringify({ users: parsed.users }),
      });
      const failures = result.errors || [];
      if (failures.length) {
        setRowErrors(failures.map((item) => `${item.row}번째 줄: ${item.detail}`));
        if (result.created) await onDone(`${result.created}명을 등록했습니다. 실패한 줄은 모달에서 확인해 주세요.`);
        return;
      }
      await onDone(`${result.created}명을 등록했습니다.`);
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 grid place-items-end bg-ink/40 sm:place-items-center" onClick={onClose}>
      <form
        onSubmit={submit}
        className="max-h-[92vh] w-full overflow-y-auto rounded-t-3xl bg-card p-5 shadow-xl sm:max-w-lg sm:rounded-3xl sm:p-6"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-xl font-semibold">여러 명 등록</h2>
            <p className="mt-1 text-sm text-muted">한 줄에 이름, 이메일, 아이디, 비밀번호를 쉼표나 탭으로 구분합니다.</p>
          </div>
          <button type="button" className="rounded-lg px-2 py-1 text-sm text-muted" onClick={onClose}>
            닫기
          </button>
        </div>
        <textarea
          value={text}
          onChange={(event) => setText(event.target.value)}
          placeholder={"홍길동,hong@example.com,hong,pass1234\n김연구,kim@example.com,kim,pass1234"}
          className="mt-4 h-48 w-full rounded-xl border border-line px-3 py-2 text-sm"
        />
        <label className="mt-3 block text-sm">
          CSV 파일
          <input type="file" accept=".csv,.txt,text/csv,text/plain" className="mt-1 block w-full text-xs" onChange={loadFile} />
        </label>
        <p className="mt-3 text-sm text-muted">
          {parsed.users.length}명 인식
          {parsed.errors.length ? ` · 형식 오류 ${parsed.errors.length}줄` : ""}
        </p>
        {error && <p className="mt-3 text-sm text-copper">{error}</p>}
        {rowErrors.length > 0 && (
          <ul className="mt-2 space-y-1 text-sm text-copper">
            {rowErrors.map((item, index) => (
              <li key={`${index}-${item}`}>{item}</li>
            ))}
          </ul>
        )}
        <button
          type="submit"
          disabled={pending}
          className="mt-4 rounded-xl bg-ink px-4 py-2 text-sm text-white disabled:opacity-60"
        >
          {pending ? "등록 중" : "등록"}
        </button>
      </form>
    </div>
  );
}

function parseBulkUsers(text) {
  const lines = String(text || "")
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
  const users = [];
  const errors = [];
  lines.forEach((line, index) => {
    const row = index + 1;
    const cells = line.includes("\t") ? line.split("\t").map((cell) => cell.trim()) : splitCsv(line);
    if (row === 1 && /^(이름|name)$/i.test(cells[0] || "")) return;
    if (cells.length !== 4) {
      errors.push(`${row}번째 줄: 이름, 이메일, 아이디, 비밀번호 네 칸이 필요합니다.`);
      return;
    }
    const [name, email, username, password] = cells;
    users.push({ name, email, username, password });
  });
  return { users, errors };
}

function splitCsv(line) {
  const cells = [];
  let current = "";
  let quoted = false;
  for (let index = 0; index < line.length; index += 1) {
    const char = line[index];
    if (char === '"') {
      if (quoted && line[index + 1] === '"') {
        current += '"';
        index += 1;
      } else {
        quoted = !quoted;
      }
    } else if (char === "," && !quoted) {
      cells.push(current.trim());
      current = "";
    } else {
      current += char;
    }
  }
  cells.push(current.trim());
  return cells;
}
