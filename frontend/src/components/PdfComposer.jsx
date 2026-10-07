import { useEffect, useMemo, useState } from "react";
import { api, downloadBlob } from "../api";

const ROW_COLUMNS = [
  "영수증 제출",
  "사용일자",
  "사용금액",
  "연구비항목",
  "사용목적",
  "사용시각",
  "사용처",
  "회의시간",
  "회의지역",
  "회의장소",
  "총인원",
  "회의참석자",
  "회의내용",
  "추천인원",
];
const EXPENSE_CATEGORIES = ["초과근무", "회의비"];

export function PdfComposer() {
  const [delivery, setDelivery] = useState([]);
  const [receipt, setReceipt] = useState([]);
  const [projects, setProjects] = useState([]);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [extracted, setExtracted] = useState([]);

  const deliveryPreviews = useMemo(
    () => delivery.map((file) => ({ file, url: URL.createObjectURL(file) })),
    [delivery],
  );
  const receiptPreviews = useMemo(
    () => receipt.map((file) => ({ file, url: URL.createObjectURL(file) })),
    [receipt],
  );
  const previewCount = deliveryPreviews.length + receiptPreviews.length;

  useEffect(() => {
    return () => {
      deliveryPreviews.forEach((item) => URL.revokeObjectURL(item.url));
      receiptPreviews.forEach((item) => URL.revokeObjectURL(item.url));
    };
  }, [deliveryPreviews, receiptPreviews]);

  useEffect(() => {
    api("/api/overtime/projects")
      .then(setProjects)
      .catch(() => setProjects([]));
  }, []);

  function replaceFiles(kind, files) {
    if (kind === "delivery") setDelivery(files);
    else setReceipt(files);
    setExtracted([]);
  }

  function updateRow(key, patch) {
    setExtracted((current) => current.map((row) => (row.key === key ? { ...row, ...patch } : row)));
  }

  function updateValue(key, column, value) {
    setExtracted((current) =>
      current.map((row) => {
        if (row.key !== key) return row;
        const values = { ...row.values, [column]: value };
        if (column === "사용시각") values["회의시간"] = meetingWindow(value);
        if (column === "사용금액") values["추천인원"] = suggestedHeadcount(value);
        return { ...row, values };
      }),
    );
  }

  async function extract() {
    setError("");
    setExtracting(true);
    try {
      const body = new FormData();
      delivery.forEach((file) => body.append("delivery", file));
      receipt.forEach((file) => body.append("receipt", file));
      const result = await api("/api/overtime/receipts/preview", { method: "POST", body });
      setExtracted(
        (result.items || []).map((item, index) => ({
          key: `${Date.now()}-${index}`,
          projectGid: item.project_gid || "",
          values: item.values || {},
          editing: false,
          saved: false,
          saving: false,
        })),
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setExtracting(false);
    }
  }

  async function saveRow(row) {
    setError("");
    updateRow(row.key, { saving: true });
    try {
      const body = new FormData();
      body.append("payload", JSON.stringify(row.values));
      body.append("gid", row.projectGid || "");
      delivery.forEach((file) => body.append("delivery", file));
      receipt.forEach((file) => body.append("receipt", file));
      await api("/api/overtime/receipts/save", { method: "POST", body });
      updateRow(row.key, { saving: false, saved: true, editing: false });
    } catch (err) {
      setError(err.message);
      updateRow(row.key, { saving: false });
    }
  }

  async function download() {
    setError("");
    setPending(true);
    try {
      const body = new FormData();
      delivery.forEach((file) => body.append("delivery", file));
      receipt.forEach((file) => body.append("receipt", file));
      const blob = await api("/api/overtime/pdf", { method: "POST", body });
      downloadBlob(blob, "증빙.pdf");
    } catch (err) {
      setError(err.message);
    } finally {
      setPending(false);
    }
  }

  return (
    <section className="rounded-3xl border border-line bg-card p-4 sm:p-6">
      <div className="flex flex-wrap justify-end gap-2">
        <button
          type="button"
          disabled={pending || extracting || previewCount === 0}
          onClick={extract}
          className="rounded-xl bg-pine px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {extracting ? "추출 중" : "AI 내역 추출"}
        </button>
        <button
          type="button"
          disabled={pending || extracting || previewCount === 0}
          onClick={download}
          className="rounded-xl bg-copper px-4 py-2 text-sm font-medium text-white hover:bg-copper-dark disabled:opacity-50"
        >
          {pending ? "만드는 중" : "PDF 다운로드"}
        </button>
      </div>
      {extracted.length > 0 && (
        <div className="mt-3 overflow-x-auto">
          <table className="w-full min-w-[1100px] border-collapse text-left text-sm">
            <thead>
              <tr className="border-b border-line text-xs text-muted">
                <th className="px-2 py-2 font-medium">프로젝트</th>
                {ROW_COLUMNS.map((column) => (
                  <th key={column} className="px-2 py-2 font-medium whitespace-nowrap">
                    {column === "추천인원" ? "추천 인원 수" : column}
                  </th>
                ))}
                <th className="px-2 py-2 font-medium"> </th>
              </tr>
            </thead>
            <tbody>
              {extracted.map((row) => (
                <tr key={row.key} className="border-b border-line align-top">
                  <td className="px-2 py-2">
                    {row.editing ? (
                      <select
                        value={row.projectGid}
                        onChange={(event) => updateRow(row.key, { projectGid: event.target.value })}
                        className="w-36 rounded-lg border border-line bg-white px-2 py-1"
                      >
                        <option value="">프로젝트 할당 전</option>
                        {projects.map((project) => (
                          <option key={project.gid} value={project.gid}>
                            {project.name}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <span className="whitespace-nowrap">{projectName(projects, row.projectGid)}</span>
                    )}
                  </td>
                  {ROW_COLUMNS.map((column) => (
                    <td key={column} className="px-2 py-2">
                      {row.editing && column !== "추천인원" ? (
                        column === "연구비항목" ? (
                          <select
                            value={row.values[column] || ""}
                            onChange={(event) => updateValue(row.key, column, event.target.value)}
                            className="w-28 rounded-lg border border-line bg-white px-2 py-1"
                          >
                            <option value="">선택</option>
                            {EXPENSE_CATEGORIES.map((category) => (
                              <option key={category} value={category}>
                                {category}
                              </option>
                            ))}
                          </select>
                        ) : (
                          <input
                            value={row.values[column] || ""}
                            onChange={(event) => updateValue(row.key, column, event.target.value)}
                            className={`rounded-lg border border-line bg-white px-2 py-1 ${column === "회의내용" || column === "회의장소" ? "w-48" : "w-28"}`}
                          />
                        )
                      ) : (
                        <span className="block max-w-48 whitespace-pre-wrap">
                          {column === "추천인원" && row.values[column] ? `${row.values[column]}` : row.values[column] || ""}
                        </span>
                      )}
                    </td>
                  ))}
                  <td className="px-2 py-2">
                    {row.saved ? (
                      <span className="whitespace-nowrap text-xs text-muted">저장됨</span>
                    ) : (
                      <div className="flex gap-1">
                        <button
                          type="button"
                          disabled={row.saving}
                          onClick={() => updateRow(row.key, { editing: !row.editing })}
                          className="whitespace-nowrap rounded-lg border border-line px-2 py-1 text-xs"
                        >
                          {row.editing ? "보기" : "수정"}
                        </button>
                        <button
                          type="button"
                          disabled={row.saving}
                          onClick={() => saveRow(row)}
                          className="whitespace-nowrap rounded-lg bg-pine px-2 py-1 text-xs font-medium text-white disabled:opacity-50"
                        >
                          {row.saving ? "저장 중" : "저장"}
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <div className="mt-5 grid gap-5 lg:grid-cols-[280px_minmax(0,1fr)]">
        <div className="space-y-4">
          <FileField label="배달 내역" files={delivery} onChange={(files) => replaceFiles("delivery", files)} />
          <FileField label="영수증" files={receipt} onChange={(files) => replaceFiles("receipt", files)} />
          {error && <p className="text-sm text-copper">{error}</p>}
        </div>
        <div className="min-h-40 space-y-4 rounded-2xl bg-paper p-3">
          {previewCount === 0 ? (
            <p className="grid h-full min-h-32 place-items-center text-sm text-muted">
              사진을 올리면 배달 내역과 영수증이 한 줄에 가로로 배치됩니다.
            </p>
          ) : (
            <div
              className="grid gap-2"
              style={{ gridTemplateColumns: `repeat(${previewCount}, minmax(0, 1fr))` }}
            >
              {deliveryPreviews.map((item) => (
                <PreviewFigure key={item.url} item={item} label="배달 내역" />
              ))}
              {receiptPreviews.map((item) => (
                <PreviewFigure key={item.url} item={item} label="영수증" />
              ))}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

function projectName(projects, gid) {
  if (!gid) return "프로젝트 할당 전";
  return projects.find((project) => project.gid === gid)?.name || "프로젝트 할당 전";
}

function meetingWindow(usageTime) {
  const match = /^(\d{2}):(\d{2})$/.exec(usageTime.trim());
  if (!match) return "";
  const base = Number(match[1]) * 60 + Number(match[2]);
  const start = (base - 120 + 24 * 60) % (24 * 60);
  const end = (base + 120) % (24 * 60);
  const clock = (minutes) => `${String(Math.floor(minutes / 60)).padStart(2, "0")}:${String(minutes % 60).padStart(2, "0")}`;
  return `${clock(start)}~${clock(end)}`;
}

function suggestedHeadcount(amountText) {
  const amount = Number(String(amountText).replace(/[^\d]/g, ""));
  if (!amount) return "";
  return `${Math.ceil(amount / 12000)}명`;
}

function PreviewFigure({ item, label }) {
  return (
    <figure className="overflow-hidden rounded-xl bg-white">
      <img src={item.url} alt={label} className="h-36 w-full object-contain" />
      <figcaption className="px-2 py-1 text-center text-xs text-muted">{label}</figcaption>
    </figure>
  );
}

function FileField({ label, files, onChange }) {
  return (
    <label className="block rounded-2xl border border-dashed border-line px-3 py-3 text-sm">
      <span className="font-medium">{label}</span>
      <span className="mt-1 block text-muted">{files.length ? `${files.length}장 선택` : "사진 선택"}</span>
      <input
        type="file"
        accept="image/jpeg,image/png,image/webp"
        multiple
        className="mt-2 block w-full text-xs"
        onChange={(event) => onChange(Array.from(event.target.files || []))}
      />
    </label>
  );
}
