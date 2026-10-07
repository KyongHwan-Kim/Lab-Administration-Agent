import { useEffect, useState } from "react";
import { api } from "../api";
import { BrandLogo } from "./BrandLogo";

export function LogoAdmin({ revision, onChanged }) {
  const [custom, setCustom] = useState(false);
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  useEffect(() => {
    let active = true;
    api(`/api/branding/logo?v=${revision}`)
      .then(() => {
        if (active) setCustom(true);
      })
      .catch((err) => {
        if (active && err.status !== 404) setError(err.message);
        if (active) setCustom(false);
      });
    return () => {
      active = false;
    };
  }, [revision]);

  function chooseFile(event) {
    const next = event.target.files?.[0];
    setFile(next || null);
    setPreview((current) => {
      if (current) URL.revokeObjectURL(current);
      return next ? URL.createObjectURL(next) : "";
    });
  }

  async function save(event) {
    event.preventDefault();
    if (!file) {
      setError("로고 이미지를 선택해 주세요.");
      return;
    }
    setError("");
    setPending(true);
    try {
      const body = new FormData();
      body.append("file", file);
      await api("/api/branding/logo", { method: "POST", body });
      setFile(null);
      setPreview("");
      setCustom(true);
      onChanged();
    } catch (err) {
      setError(err.message);
    } finally {
      setPending(false);
    }
  }

  async function reset() {
    setError("");
    setPending(true);
    try {
      await api("/api/branding/logo", { method: "DELETE" });
      setCustom(false);
      setFile(null);
      setPreview("");
      onChanged();
    } catch (err) {
      setError(err.message);
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">로고 변경</h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-muted">
          등록한 로고는 로그인 화면 왼쪽 위와 메뉴 아래에 나타납니다. 등록하지 않으면 그 자리는 비워 둡니다.
        </p>
      </div>
      <form onSubmit={save} className="max-w-xl rounded-3xl border border-line bg-card p-4 sm:p-6">
        <div className="grid min-h-24 place-items-center rounded-2xl bg-ink p-6">
          {preview ? (
            <img src={preview} alt="선택한 로고" className="h-14 w-auto max-w-full" />
          ) : (
            <BrandLogo revision={revision} className="h-14 w-auto max-w-full" />
          )}
          {!preview && !custom && <p className="text-sm text-white/60">등록된 로고가 없습니다.</p>}
        </div>
        <p className="mt-3 text-sm text-muted">{custom ? "등록한 로고를 사용 중입니다." : "아직 등록한 로고가 없습니다."}</p>
        <label className="mt-4 block text-sm">
          이미지 선택
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp"
            className="mt-2 block w-full text-xs"
            onChange={chooseFile}
          />
        </label>
        {error && <p className="mt-3 text-sm text-copper">{error}</p>}
        <div className="mt-5 flex flex-col gap-2 sm:flex-row">
          <button
            type="submit"
            disabled={pending}
            className="rounded-xl bg-copper px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
          >
            {pending ? "저장 중" : "로고 저장"}
          </button>
          {custom && (
            <button type="button" disabled={pending} onClick={reset} className="rounded-xl border border-line px-4 py-2 text-sm">
              등록한 로고 삭제
            </button>
          )}
        </div>
      </form>
    </div>
  );
}
