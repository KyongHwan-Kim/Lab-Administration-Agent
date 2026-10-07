import { useEffect, useState } from "react";
import { api } from "../api";

export function SignatureDialog({ userId, username, onClose, onSaved, page = false, embedded = false }) {
  const base = userId ? `/api/users/${userId}/signature` : "/api/users/me/signature";
  const [preview, setPreview] = useState("");
  const [file, setFile] = useState(null);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const [hasSignature, setHasSignature] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    let active = true;
    let objectUrl = "";
    api(base)
      .then((blob) => {
        if (!active || !blob) return;
        objectUrl = URL.createObjectURL(blob);
        setPreview(objectUrl);
        setHasSignature(true);
      })
      .catch((err) => {
        if (active && err.status !== 404) setError(err.message);
      });
    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [base]);

  function chooseFile(event) {
    const next = event.target.files?.[0];
    setFile(next || null);
    if (!next) return;
    const objectUrl = URL.createObjectURL(next);
    setPreview((current) => {
      if (current) URL.revokeObjectURL(current);
      return objectUrl;
    });
  }

  async function save(event) {
    event.preventDefault();
    if (!file) {
      setError("서명 이미지를 선택해 주세요.");
      return;
    }
    setError("");
    setMessage("");
    setPending(true);
    try {
      const body = new FormData();
      body.append("file", file);
      const updated = await api(base, { method: "POST", body });
      setHasSignature(true);
      setFile(null);
      if (page) setMessage("서명을 저장했습니다.");
      onSaved(updated);
    } catch (err) {
      setError(err.message);
    } finally {
      setPending(false);
    }
  }

  async function remove() {
    setError("");
    setMessage("");
    setPending(true);
    try {
      const updated = await api(base, { method: "DELETE" });
      setPreview("");
      setFile(null);
      setHasSignature(false);
      if (page) setMessage("서명을 삭제했습니다.");
      onSaved(updated);
    } catch (err) {
      setError(err.message);
    } finally {
      setPending(false);
    }
  }

  const form = (
      <form onSubmit={save} className={page && !embedded ? "max-w-md" : undefined} onClick={(event) => event.stopPropagation()}>
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className={embedded ? "text-lg font-semibold" : page ? "text-2xl font-semibold tracking-tight sm:text-3xl" : "text-xl font-semibold"}>
              서명 등록
            </h2>
            <p className="mt-1 text-sm text-muted">{username} 계정의 서명 이미지입니다.</p>
          </div>
          {!page && (
            <button type="button" className="text-sm text-muted" onClick={onClose}>
              닫기
            </button>
          )}
        </div>
        <div className="mt-5 grid min-h-36 place-items-center rounded-2xl border border-dashed border-line bg-paper p-4">
          {preview ? (
            <img src={preview} alt="서명 미리보기" className="max-h-40 max-w-full" />
          ) : (
            <p className="text-sm text-muted">등록된 서명이 없습니다.</p>
          )}
        </div>
        <label className="mt-4 block text-sm">
          이미지 선택
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp"
            className="mt-1 block w-full text-xs"
            onChange={chooseFile}
          />
        </label>
        {error && <p className="mt-3 text-sm text-copper">{error}</p>}
        {message && <p className="mt-3 text-sm text-pine">{message}</p>}
        <div className="mt-5 flex flex-col gap-2 sm:flex-row">
          <button
            type="submit"
            disabled={pending}
            className="rounded-xl bg-copper px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
          >
            {pending ? "저장 중" : "저장"}
          </button>
          {hasSignature && (
            <button type="button" disabled={pending} className="rounded-xl border border-line px-4 py-2 text-sm" onClick={remove}>
              삭제
            </button>
          )}
        </div>
      </form>
  );

  if (page) return form;
  return (
    <div className="fixed inset-0 z-[60] grid place-items-end bg-ink/40 sm:place-items-center" onClick={onClose}>
      <div className="w-full rounded-t-3xl bg-card p-5 shadow-xl sm:max-w-md sm:rounded-3xl sm:p-6">{form}</div>
    </div>
  );
}
