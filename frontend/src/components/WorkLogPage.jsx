import { useEffect, useState } from "react";
import { api, downloadBlob } from "../api";
import letterhead from "../assets/letterhead.jpg";

const PAGE_SLOTS = 6;

const EMPTY_ROW = { year: "", month: "", day: "", worker: "", time: "", signature: "" };

export function WorkLogPage() {
  const [items, setItems] = useState([]);
  const [projects, setProjects] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [form, setForm] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [creating, setCreating] = useState(false);
  const [projectGid, setProjectGid] = useState("");

  useEffect(() => {
    let cancelled = false;
    Promise.all([api("/api/overtime/work-logs"), api("/api/overtime/projects")])
      .then(([logs, projectList]) => {
        if (cancelled) return;
        const nextItems = logs.items || [];
        const nextProjects = projectList || [];
        const nextGid = nextProjects[0]?.gid || "";
        setItems(nextItems);
        setProjects(nextProjects);
        setProjectGid(nextGid);
        const first = nextItems.find((item) => item.project_gid === nextGid);
        setSelectedId(first?.id ?? null);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!selectedId) {
      setForm(null);
      return undefined;
    }
    let cancelled = false;
    api(`/api/overtime/work-logs/${selectedId}/form`)
      .then((data) => {
        if (!cancelled) setForm(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedId]);

  function updateDocument(patch) {
    setForm((current) => (current ? { ...current, document: { ...current.document, ...patch } } : current));
  }

  function updateRow(index, patch) {
    setForm((current) => {
      if (!current) return current;
      const rows = current.document.rows.map((row, rowIndex) => (rowIndex === index ? { ...row, ...patch } : row));
      return { ...current, document: { ...current.document, rows } };
    });
  }

  function addRow() {
    setForm((current) => {
      if (!current) return current;
      const previous = current.document.rows.at(-1) || EMPTY_ROW;
      const rows = [
        ...current.document.rows,
        { year: previous.year, month: previous.month, day: previous.day, worker: "", time: previous.time, signature: "" },
      ];
      return { ...current, document: { ...current.document, rows } };
    });
  }

  function removeRow(index) {
    setForm((current) => {
      if (!current || current.document.rows.length < 2) return current;
      const rows = current.document.rows.filter((_, rowIndex) => rowIndex !== index);
      return { ...current, document: { ...current.document, rows } };
    });
  }

  async function save() {
    if (!form) return;
    setError("");
    setSaving(true);
    try {
      const saved = await api(`/api/overtime/work-logs/${form.id}`, {
        method: "PATCH",
        body: JSON.stringify(plainDocument(form.document)),
      });
      setForm(saved);
      setItems((current) =>
        current.map((item) =>
          item.id === saved.id
            ? {
                ...item,
                filename: saved.filename,
                usage_date: saved.document.rows?.[0] ? joinDate(saved.document.rows[0]) : item.usage_date,
                store_name: saved.document.place,
              }
            : item,
        ),
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function createLog() {
    if (!projectGid) {
      setError("프로젝트를 선택해 주세요.");
      return;
    }
    setError("");
    setCreating(true);
    try {
      const created = await api("/api/overtime/work-logs", {
        method: "POST",
        body: JSON.stringify({ gid: projectGid }),
      });
      setItems((current) => [
        {
          id: created.id,
          project_gid: created.project_gid || projectGid,
          project_name: created.project_name,
          filename: created.filename,
          usage_date: "",
          store_name: "",
          created_at: new Date().toISOString(),
        },
        ...current,
      ]);
      setForm(created);
      setSelectedId(created.id);
    } catch (err) {
      setError(err.message);
    } finally {
      setCreating(false);
    }
  }

  async function download() {
    if (!form) return;
    setError("");
    try {
      const blob = await api(`/api/overtime/work-logs/${form.id}`);
      downloadBlob(blob, form.filename || "초과근무일지.pdf");
    } catch (err) {
      setError(err.message);
    }
  }

  const visible = items.filter((item) => item.project_gid === projectGid);

  function changeProject(gid) {
    setProjectGid(gid);
    const next = items.find((item) => item.project_gid === gid);
    setSelectedId(next?.id ?? null);
  }

  return (
    <section>
      <div>
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">초과근무일지</h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-muted">
          양식과 같은 표로 보고, 근무 행을 추가한 뒤 저장합니다. 저장하면 PDF도 같은 내용으로 다시 만들어집니다.
        </p>
      </div>
      {error && <p className="mt-4 text-sm text-copper">{error}</p>}
      {loading && <p className="mt-4 text-sm text-muted">목록을 불러오는 중</p>}
      {!loading && (
        <div className="mt-5 grid gap-5 xl:grid-cols-[240px_minmax(0,1fr)]">
          <div>
            <label className="block text-sm">
              프로젝트
              <select
                value={projectGid}
                onChange={(event) => changeProject(event.target.value)}
                className="mt-1 block w-full rounded-xl border border-line bg-white px-3 py-2"
              >
                {projects.map((project) => (
                  <option key={project.gid} value={project.gid}>
                    {project.name}
                  </option>
                ))}
              </select>
            </label>
            <button
              type="button"
              disabled={creating || !projectGid}
              className="mt-2 w-full rounded-xl bg-pine px-4 py-2 text-sm text-white disabled:opacity-40"
              onClick={createLog}
            >
              {creating ? "만드는 중" : "일지 추가"}
            </button>
            <div className="mt-4 space-y-1">
              <p className="px-2 text-sm text-muted">{visible.length}건</p>
              {visible.length === 0 && <p className="px-2 text-sm text-muted">이 프로젝트의 일지가 없습니다.</p>}
              {visible.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  className={`w-full rounded-xl px-3 py-2 text-left text-sm ${
                    item.id === selectedId ? "bg-white font-medium" : "hover:bg-white/70"
                  }`}
                  onClick={() => setSelectedId(item.id)}
                >
                  <span className="block">{item.usage_date || "날짜 없음"}</span>
                  <span className="block text-xs text-muted">
                    {item.project_name}
                    {item.store_name ? ` · ${item.store_name}` : ""}
                  </span>
                </button>
              ))}
            </div>
          </div>
          {form ? (
            <WorkLogSheet
              form={form}
              saving={saving}
              onDocument={updateDocument}
              onRow={updateRow}
              onAddRow={addRow}
              onRemoveRow={removeRow}
              onSave={save}
              onDownload={download}
            />
          ) : (
            <p className="text-sm text-muted">일지를 선택하거나 새로 추가해 주세요.</p>
          )}
        </div>
      )}
    </section>
  );
}

function WorkLogSheet({ form, saving, onDocument, onRow, onAddRow, onRemoveRow, onSave, onDownload }) {
  const document = form.document;
  const rows = document.rows || [];
  return (
    <div>
      <div className="mb-3 flex flex-wrap justify-end gap-2">
        <button type="button" className="rounded-xl border border-line bg-white px-4 py-2 text-sm" onClick={onAddRow}>
          행 추가
        </button>
        <button type="button" className="rounded-xl border border-line bg-white px-4 py-2 text-sm" onClick={onDownload}>
          PDF 다운로드
        </button>
        <button
          type="button"
          disabled={saving}
          className="rounded-xl bg-ink px-4 py-2 text-sm text-white disabled:opacity-40"
          onClick={onSave}
        >
          {saving ? "저장 중" : "저장"}
        </button>
      </div>
      <div className="space-y-4">
        {formPages(rows).map((slots, pageIndex, pages) => (
          <LetterheadPage key={pageIndex} pageIndex={pageIndex} pageCount={pages.length}>
            <SheetBody
              document={document}
              rows={rows}
              slots={slots}
              onDocument={onDocument}
              onRow={onRow}
              onRemoveRow={onRemoveRow}
            />
          </LetterheadPage>
        ))}
      </div>
    </div>
  );
}

function formPages(rows) {
  const total = Math.max(rows.length, 1);
  const pages = [];
  for (let start = 0; start < total; start += PAGE_SLOTS) {
    const slots = [];
    for (let index = start; index < start + PAGE_SLOTS; index += 1) {
      slots.push(index < rows.length ? index : null);
    }
    pages.push(slots);
  }
  return pages;
}

function LetterheadPage({ pageIndex, pageCount, children }) {
  return (
    <article
      className="relative mx-auto w-full max-w-[680px] overflow-hidden text-black shadow-sm"
      style={{
        aspectRatio: "724 / 1024",
        backgroundImage: `url(${letterhead})`,
        backgroundSize: "100% 100%",
        backgroundRepeat: "no-repeat",
      }}
    >
      {pageCount > 1 && (
        <p className="absolute right-[6%] top-[1.5%] text-[10px] text-neutral-500">
          {pageIndex + 1} / {pageCount}
        </p>
      )}
      <div className="absolute inset-x-[5.5%] top-[3.2%] bottom-[15%] overflow-hidden">{children}</div>
    </article>
  );
}

function SheetBody({ document, rows, slots, onDocument, onRow, onRemoveRow }) {
  return (
    <div className="flex h-full flex-col">
      <p className="text-[10px] tracking-wide">| 필수 첨부 양식 |</p>
      <h2 className="mt-1 text-center text-lg font-semibold tracking-[0.4em]">초과근무일지</h2>
      <table className="mt-2 w-full border-collapse border border-black text-[11px]">
        <tbody>
          <tr>
            <FormLabel>과제번호</FormLabel>
            <td className="border border-black px-1 py-0.5">
              <CellInput value={document.project_number} onChange={(value) => onDocument({ project_number: value })} />
            </td>
            <FormLabel>연구책임자</FormLabel>
            <td className="border border-black px-1 py-0.5">
              <CellInput
                value={document.principal_investigator}
                onChange={(value) => onDocument({ principal_investigator: value })}
              />
            </td>
          </tr>
          <tr>
            <th className="w-20 border border-black bg-neutral-50 px-1 py-1 text-center font-medium">연구지원기관</th>
            <td className="border border-black px-1 py-0.5">
              <CellInput value={document.funding_agency} onChange={(value) => onDocument({ funding_agency: value })} />
            </td>
            <th className="w-16 border border-black bg-neutral-50 px-1 py-1 text-center font-medium">사업명</th>
            <td className="border border-black px-1 py-0.5">
              <CellInput value={document.program_name} onChange={(value) => onDocument({ program_name: value })} />
            </td>
          </tr>
          <tr>
            <th className="border border-black bg-neutral-50 px-1 py-1 text-center font-medium">연구과제명</th>
            <td className="border border-black px-1 py-0.5" colSpan={3}>
              <CellInput value={document.research_title} onChange={(value) => onDocument({ research_title: value })} />
            </td>
          </tr>
        </tbody>
      </table>
      <table className="mt-2 w-full flex-1 border-collapse border border-black text-[11px]">
        <thead>
          <tr className="bg-neutral-50">
            <th className="border border-black px-1 py-1 font-medium">
              <Required />
              근무일자
              <span className="block text-[9px] font-normal">(년-월-일)</span>
            </th>
            <th className="border border-black px-1 py-1 font-medium">
              <Required />
              근무자
            </th>
            <th className="border border-black px-1 py-1 font-medium">
              <Required />
              근무내용
            </th>
            <th className="border border-black px-1 py-1 font-medium">
              <Required />
              근무장소
            </th>
            <th className="w-16 border border-black px-1 py-1 font-medium">
              <Required />
              시간
            </th>
            <th className="w-16 border border-black px-1 py-1 font-medium">
              <Required />
              근무자
              <span className="block text-[9px] font-normal">본인사인</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {slots.map((index, slot) => {
            const row = index === null ? null : rows[index];
            return (
              <tr key={slot} className="h-8">
                <td className="border border-black px-0.5 py-0.5 align-middle">
                  {row && (
                    <div className="flex items-center justify-center">
                      <CellInput value={row.year} onChange={(value) => onRow(index, { year: value })} className="w-10" />
                      <CellInput value={row.month} onChange={(value) => onRow(index, { month: value })} className="w-6" />
                      <CellInput value={row.day} onChange={(value) => onRow(index, { day: value })} className="w-6" />
                    </div>
                  )}
                </td>
                <td className="border border-black px-0.5 py-0.5 align-middle">
                  {row && <CellInput value={row.worker} onChange={(value) => onRow(index, { worker: value })} />}
                  {row && rows.length > 1 && (
                    <button type="button" className="block w-full text-[9px] text-neutral-500" onClick={() => onRemoveRow(index)}>
                      행 삭제
                    </button>
                  )}
                </td>
                {slot === 0 && (
                  <td className="border border-black px-1 py-0.5 align-middle" rowSpan={slots.length}>
                    <textarea
                      value={document.content}
                      onChange={(event) => onDocument({ content: event.target.value })}
                      className="h-full min-h-16 w-full resize-none bg-transparent text-center outline-none"
                    />
                  </td>
                )}
                {slot === 0 && (
                  <td className="border border-black px-1 py-0.5 align-middle" rowSpan={slots.length}>
                    <textarea
                      value={document.place}
                      onChange={(event) => onDocument({ place: event.target.value })}
                      className="h-full min-h-16 w-full resize-none bg-transparent text-center outline-none"
                    />
                  </td>
                )}
                <td className="border border-black px-0.5 py-0.5 align-middle">
                  {row && <CellInput value={row.time} onChange={(value) => onRow(index, { time: value })} />}
                </td>
                <td className="border border-black px-0.5 py-0.5 text-center align-middle">
                  {row?.signature ? <img src={row.signature} alt="" className="mx-auto h-7 max-w-full object-contain" /> : null}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <div className="mt-2 space-y-0.5 text-[9px] leading-4">
        <p>※ [영수증첨부] : 상한 1인 30,000원, 법인신용카드 영수증만 인정</p>
        <p>※ [필수항목] *본인사인에는 근무자의 자필사인 기재</p>
        <p className="pl-12">*연구책임자의 확인(날인 또는 사인) 기재하여 청구 시 파일 업로드함</p>
      </div>
      <div className="mt-2 flex items-center justify-end gap-3 text-[11px]">
        <span>
          <Required />
          연구책임자
        </span>
        <span className="min-w-12 text-center">{document.principal_investigator}</span>
        {document.pi_signature ? (
          <img src={document.pi_signature} alt="" className="h-10 w-10 object-contain" />
        ) : (
          <span className="inline-block h-10 w-10" />
        )}
      </div>
    </div>
  );
}

function FormLabel({ children }) {
  return (
    <th className="w-20 border border-black bg-neutral-50 px-1 py-1 text-center font-medium">
      <Required />
      {children}
    </th>
  );
}

function Required() {
  return <span className="mr-0.5 text-red-600">*</span>;
}

function CellInput({ value, onChange, className = "" }) {
  return (
    <input
      value={value || ""}
      onChange={(event) => onChange(event.target.value)}
      className={`w-full bg-transparent text-center outline-none ${className}`}
    />
  );
}

function plainDocument(document) {
  return {
    project_number: document.project_number || "",
    principal_investigator: document.principal_investigator || "",
    funding_agency: document.funding_agency || "",
    program_name: document.program_name || "",
    research_title: document.research_title || "",
    content: document.content || "",
    place: document.place || "",
    rows: (document.rows || []).map((row) => ({
      year: row.year || "",
      month: row.month || "",
      day: row.day || "",
      worker: row.worker || "",
      time: row.time || "",
    })),
  };
}

function joinDate(row) {
  if (!row.year || !row.month || !row.day) return "";
  return `${row.year}-${String(row.month).padStart(2, "0")}-${String(row.day).padStart(2, "0")}`;
}
