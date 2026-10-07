import { useEffect, useState } from "react";
import { api, downloadBlob } from "../api";
import { AttendeePicker, EntryModal } from "./EntryModal";
import { PdfComposer } from "./PdfComposer";

const UNASSIGNED = "unassigned";
const EXPENSE_CATEGORIES = ["초과근무", "회의비"];

export function OvertimePage({ section }) {
  const [projects, setProjects] = useState([]);
  const [gid, setGid] = useState("");
  const [table, setTable] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);
  const [editing, setEditing] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    api("/api/overtime/projects")
      .then((items) => {
        setProjects(items);
        setGid((current) => current || items[0]?.gid || "");
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    if (!gid) return undefined;
    let cancelled = false;
    setLoading(true);
    setError("");
    const path = gid === UNASSIGNED ? "/api/overtime/unassigned" : `/api/overtime/projects/${gid}`;
    api(path)
      .then((data) => {
        if (!cancelled) setTable(data);
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
  }, [gid, refreshKey]);

  async function removeEntry(id) {
    if (!window.confirm("이 항목을 삭제할까요?")) return false;
    try {
      await api(`/api/overtime/entries/${id}`, { method: "DELETE" });
      setRefreshKey((value) => value + 1);
      return true;
    } catch (err) {
      setError(err.message);
      return false;
    }
  }

  async function assignEntry(id, projectGid) {
    if (!projectGid) {
      setError("할당할 프로젝트를 선택해 주세요.");
      return false;
    }
    setError("");
    try {
      await api(`/api/overtime/entries/${id}/assign`, {
        method: "POST",
        body: JSON.stringify({ gid: projectGid }),
      });
      setRefreshKey((value) => value + 1);
      return true;
    } catch (err) {
      setError(err.message);
      return false;
    }
  }

  async function downloadWorkLog(row, values) {
    const sourceKey = row.source === "sheet" ? `sheet:${row.row_key}` : `entry:${row.id}`;
    const blob = await api(`/api/overtime/projects/${gid}/work-log`, {
      method: "POST",
      body: JSON.stringify({ values, source_key: sourceKey }),
    });
    downloadBlob(blob, pdfFilename(values, "log"));
  }

  async function downloadReceipt(row) {
    const path =
      row.source === "sheet"
        ? `/api/overtime/projects/${gid}/receipts/${row.row_key}`
        : `/api/overtime/entries/${row.id}/pdf`;
    try {
      const blob = await api(path);
      downloadBlob(blob, pdfFilename(row.values, "receipt"));
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div>
      <div className={section === "pdf" ? "space-y-5" : "hidden"}>
        <div>
          <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">영수증 등록</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-muted">
            배달 내역과 영수증 사진을 올리면 사용일자, 금액, 시각, 가게 이름을 읽고 사용 내역을 만듭니다. 회의시간은 사용시각 앞뒤 2시간, 회의장소는 배달지, 추천 인원 수는 1인 12,000원 한도로 계산합니다.
          </p>
        </div>
        <PdfComposer />
      </div>

      <div className={section === "sheet" ? "space-y-5" : "hidden"}>
      <div>
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">사용 내역</h1>
        {table?.common_notes?.length > 0 && (
          <details className="mt-2 max-w-3xl text-sm leading-6">
            <summary className="cursor-pointer font-medium text-muted">공통 안내</summary>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-muted">
              {table.common_notes.map((note) => (
                <li key={note}>{note}</li>
              ))}
            </ul>
          </details>
        )}
      </div>

      <section className="rounded-3xl border border-line bg-card p-4 sm:p-6">
        {error && <p className="text-sm text-copper">{error}</p>}
        {loading && <p className="mb-4 text-sm text-muted">표를 불러오는 중</p>}
        {!table && (
          <label className="block text-sm">
            프로젝트
            <select
              value={gid}
              onChange={(event) => setGid(event.target.value)}
              className="mt-1 block rounded-xl border border-line bg-white px-3 py-2 sm:min-w-56"
            >
              <option value={UNASSIGNED}>프로젝트 할당 전</option>
              {projects.map((project) => (
                <option key={project.gid} value={project.gid}>
                  {project.name}
                </option>
              ))}
            </select>
          </label>
        )}
        {table && (
          <SheetTable
            table={table}
            gid={gid}
            projects={projects}
            onProject={setGid}
            onAdd={gid !== UNASSIGNED ? () => setAdding(true) : null}
            onEdit={setEditing}
          />
        )}
      </section>

      {editing && (
        <DetailModal
          row={editing}
          projects={gid === UNASSIGNED ? projects : null}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            setRefreshKey((value) => value + 1);
          }}
          projectGid={gid}
          onDownload={downloadReceipt}
          onWorkLog={downloadWorkLog}
          onRemove={async (id) => {
            const removed = await removeEntry(id);
            if (removed) setEditing(null);
          }}
          onAssign={async (id, projectGid) => {
            const assigned = await assignEntry(id, projectGid);
            if (assigned) setEditing(null);
          }}
        />
      )}

      {adding && table && gid !== UNASSIGNED && (
        <EntryModal
          project={table}
          onClose={() => setAdding(false)}
          onSaved={() => {
            setAdding(false);
            setRefreshKey((value) => value + 1);
          }}
        />
      )}
      </div>
    </div>
  );
}

const SUMMARY_COLUMNS = [
  ["사용일자", "날짜"],
  ["사용금액", "금액"],
  ["연구비항목", "연구비 항목"],
  ["사용시각", "사용 시각"],
  ["사용처", "사용처"],
  ["총인원", "총인원"],
  ["메모", "메모"],
];

function summaryValue(values, key) {
  if (key === "총인원") return values["총인원"] || values["참석인원"] || "";
  return values[key] || "";
}

function HeadcountCell({ values }) {
  const actual = values["총인원"] || values["참석인원"] || "";
  const recommended = String(values["추천인원"] || "").trim();
  if (!actual && !recommended) return null;
  return (
    <div>
      {actual ? <div>{actual}</div> : null}
      {recommended ? <div className="text-xs text-muted">추천 인원 수 {recommended}</div> : null}
    </div>
  );
}

function currentPeriod() {
  const now = new Date();
  return { year: String(now.getFullYear()), month: String(now.getMonth() + 1) };
}

function SheetTable({ table, gid, projects, onProject, onAdd, onEdit }) {
  const today = currentPeriod();
  const [year, setYear] = useState(today.year);
  const [month, setMonth] = useState(today.month);
  const [scope, setScope] = useState(table.name);
  if (table.name !== scope) {
    setScope(table.name);
    setYear(today.year);
    setMonth(today.month);
  }
  const periods = table.rows.map((row) => parseUsageDate(row.values["사용일자"])).filter(Boolean);
  const years = [...new Set([...periods.map((period) => period.year), Number(today.year)])].sort((a, b) => b - a);
  const months = [
    ...new Set([
      ...periods.filter((period) => !year || period.year === Number(year)).map((period) => period.month),
      ...(year === today.year ? [Number(today.month)] : []),
    ]),
  ].sort((a, b) => a - b);
  const filtered = table.rows
    .filter((row) => matchesPeriod(row.values["사용일자"], year, month))
    .slice()
    .sort((left, right) => usageOrder(right) - usageOrder(left));

  function changeYear(value) {
    setYear(value);
    if (value && month && !periods.some((period) => period.year === Number(value) && period.month === Number(month))) {
      setMonth("");
    }
  }

  return (
    <div>
      <div className="flex flex-wrap items-end gap-3">
        <label className="text-sm">
          프로젝트
          <select
            value={gid}
            onChange={(event) => onProject(event.target.value)}
            className="mt-1 block rounded-xl border border-line bg-white px-3 py-2 sm:min-w-56"
          >
            <option value={UNASSIGNED}>프로젝트 할당 전</option>
            {projects.map((project) => (
              <option key={project.gid} value={project.gid}>
                {project.name}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          연도
          <select
            value={year}
            onChange={(event) => changeYear(event.target.value)}
            className="mt-1 block rounded-xl border border-line bg-white px-3 py-2"
          >
            <option value="">전체</option>
            {years.map((item) => (
              <option key={item} value={item}>
                {item}년
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          월
          <select
            value={month}
            onChange={(event) => setMonth(event.target.value)}
            className="mt-1 block rounded-xl border border-line bg-white px-3 py-2"
          >
            <option value="">전체</option>
            {months.map((item) => (
              <option key={item} value={item}>
                {item}월
              </option>
            ))}
          </select>
        </label>
        <span className="pb-2 text-sm text-muted">{filtered.length}건</span>
        {onAdd && (
          <button
            type="button"
            onClick={onAdd}
            className="ml-auto shrink-0 rounded-xl bg-pine px-4 py-2 text-sm font-medium text-white"
          >
            항목 추가
          </button>
        )}
      </div>
      {gid === UNASSIGNED && (
        <p className="mt-4 text-sm text-muted">영수증 등록에서 읽어 온 항목입니다. 내용을 고친 뒤 프로젝트를 정하면 해당 사용 내역으로 옮깁니다.</p>
      )}
    <div className="mt-4 overflow-x-auto">
      <table className="w-full min-w-[860px] border-collapse text-left text-sm">
        <thead>
          <tr className="border-b border-line text-muted">
            {SUMMARY_COLUMNS.map(([, label]) => (
              <th key={label} className="whitespace-nowrap px-2 py-2 font-medium">
                {label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {filtered.length === 0 && (
            <tr>
              <td colSpan={SUMMARY_COLUMNS.length} className="px-2 py-8 text-center text-muted">
                {table.rows.length === 0 ? "표시할 항목이 없습니다." : "선택한 기간에 해당하는 항목이 없습니다."}
              </td>
            </tr>
          )}
          {filtered.map((row, index) => (
            <tr
              key={row.id || `sheet-${index}`}
              className={`cursor-pointer border-b border-line/80 align-top hover:bg-paper ${row.source === "app" ? "bg-paper/70" : ""}`}
              onClick={() => onEdit(row)}
            >
              {SUMMARY_COLUMNS.map(([key, label]) => (
                <td key={label} className="max-w-xs px-2 py-2 whitespace-pre-wrap">
                  {key === "총인원" ? <HeadcountCell values={row.values} /> : summaryValue(row.values, key)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
    </div>
  );
}

function fileDate(value) {
  const text = String(value || "").trim();
  const full = text.match(/(20\d{2})\s*[.\/년-]\s*(\d{1,2})\s*[.\/월-]?\s*(\d{1,2})/);
  if (full) {
    const month = Number(full[2]);
    const day = Number(full[3]);
    if (month >= 1 && month <= 12 && day >= 1 && day <= 31) {
      return `${full[1].slice(2)}.${String(month).padStart(2, "0")}.${String(day).padStart(2, "0")}`;
    }
  }
  const short = text.match(/(?:^|\D)(\d{2})\s*[.\/-]\s*(\d{1,2})\s*[.\/-]\s*(\d{1,2})/);
  if (short) {
    const month = Number(short[2]);
    const day = Number(short[3]);
    if (month >= 1 && month <= 12 && day >= 1 && day <= 31) {
      return `${short[1]}.${String(month).padStart(2, "0")}.${String(day).padStart(2, "0")}`;
    }
  }
  return "";
}

function pdfFilename(values, kind) {
  const stamp = fileDate(values["사용일자"]);
  const prefix = stamp ? `[${stamp}] ` : "";
  if (kind === "log") return `${prefix}초과근무_간접비.pdf`;
  const category = String(values["연구비항목"] || "").trim();
  const label = category === "회의비" ? "회의비_영수증" : category === "초과근무" ? "초과근무_영수증" : "영수증";
  return `${prefix}${label}.pdf`;
}

function parseUsageDate(value) {
  const text = String(value || "").trim();
  const full = text.match(/(20\d{2})\s*[.\/년-]\s*(\d{1,2})/);
  if (full) {
    const month = Number(full[2]);
    if (month >= 1 && month <= 12) return { year: Number(full[1]), month };
  }
  const short = text.match(/(?:^|\D)(\d{2})\s*[.\/-]\s*(\d{1,2})\s*[.\/-]\s*(\d{1,2})/);
  if (short) {
    const month = Number(short[2]);
    if (month >= 1 && month <= 12) return { year: 2000 + Number(short[1]), month };
  }
  return null;
}

function usageOrder(row) {
  const text = String(row.values["사용일자"] || "").trim();
  const full = text.match(/(20\d{2})\s*[.\/년-]\s*(\d{1,2})\s*[.\/월-]?\s*(\d{1,2})?/);
  const short = text.match(/(?:^|\D)(\d{2})\s*[.\/-]\s*(\d{1,2})\s*[.\/-]\s*(\d{1,2})/);
  let year = 0;
  let month = 0;
  let day = 0;
  if (full && Number(full[2]) >= 1 && Number(full[2]) <= 12) {
    year = Number(full[1]);
    month = Number(full[2]);
    day = Number(full[3] || 0);
  } else if (short && Number(short[2]) >= 1 && Number(short[2]) <= 12) {
    year = 2000 + Number(short[1]);
    month = Number(short[2]);
    day = Number(short[3]);
  }
  const clock = String(row.values["사용시각"] || "").match(/(\d{1,2})\s*[:시]\s*(\d{2})/);
  const minutes = clock ? Number(clock[1]) * 60 + Number(clock[2]) : 0;
  return year * 100000000 + month * 1000000 + day * 10000 + minutes;
}

function matchesPeriod(value, year, month) {
  if (!year && !month) return true;
  const date = parseUsageDate(value);
  if (!date) return false;
  if (year && date.year !== Number(year)) return false;
  if (month && date.month !== Number(month)) return false;
  return true;
}

const LONG_FIELDS = new Set(["회의내용", "회의목적", "회의참석자", "메모"]);
const HIDDEN_FIELDS = new Set(["순번", "추천인원"]);

function DetailModal({ row, projects, projectGid, onClose, onSaved, onDownload, onWorkLog, onRemove, onAssign }) {
  const columns = Object.keys(row.values).filter((column) => !HIDDEN_FIELDS.has(column));
  const sheetMemo = row.source === "sheet";
  const [values, setValues] = useState(row.values);
  const [target, setTarget] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const [hasPdf, setHasPdf] = useState(Boolean(row.has_pdf));
  const [linking, setLinking] = useState(false);
  const [logPending, setLogPending] = useState(false);
  const editable = Boolean(row.can_edit);
  const overtime = (values["연구비항목"] || "").trim() === "초과근무";
  const canLink = row.source === "sheet" || editable;

  async function submit(event) {
    event.preventDefault();
    if (!editable && !sheetMemo) return;
    setError("");
    setPending(true);
    try {
      if (sheetMemo) {
        await api(`/api/overtime/projects/${projectGid}/memos`, {
          method: "PUT",
          body: JSON.stringify({ row_key: row.row_key, memo: values["메모"] || "" }),
        });
      } else {
        await api(`/api/overtime/entries/${row.id}`, {
          method: "PATCH",
          body: JSON.stringify({ values }),
        });
      }
      onSaved();
    } catch (err) {
      setError(err.message);
    } finally {
      setPending(false);
    }
  }

  async function linkReceipt(event) {
    const files = Array.from(event.target.files || []);
    event.target.value = "";
    if (!files.length) return;
    setError("");
    setLinking(true);
    try {
      const body = new FormData();
      files.forEach((file) => body.append("file", file));
      if (row.source === "sheet") {
        body.append("row_key", row.row_key);
        await api(`/api/overtime/projects/${projectGid}/receipts`, { method: "POST", body });
      } else {
        await api(`/api/overtime/entries/${row.id}/pdf`, { method: "POST", body });
      }
      setHasPdf(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setLinking(false);
    }
  }

  async function downloadLog() {
    setError("");
    setLogPending(true);
    try {
      await onWorkLog(row, values);
    } catch (err) {
      setError(err.message);
    } finally {
      setLogPending(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 grid place-items-end bg-ink/40 sm:place-items-center" onClick={onClose}>
      <form
        onSubmit={submit}
        className="max-h-[94vh] w-full overflow-y-auto rounded-t-3xl bg-card p-5 sm:max-w-3xl sm:rounded-3xl sm:p-6"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-xl font-semibold">사용 내역</h2>
            <p className="mt-1 text-sm text-muted">
              {editable ? "내용을 수정한 뒤 저장할 수 있습니다." : "스프레드시트 항목은 조회만 되고, 메모는 저장할 수 있습니다."}
            </p>
          </div>
          <button type="button" className="text-sm text-muted" onClick={onClose}>
            닫기
          </button>
        </div>
        <div className="mt-5 grid gap-3 sm:grid-cols-2">
          {columns.map((column) =>
            column === "회의참석자" && editable && projectGid !== UNASSIGNED ? (
              <AttendeePicker
                key={column}
                projectGid={projectGid}
                value={values[column] || ""}
                onChange={(value) => setValues((current) => ({ ...current, [column]: value }))}
              />
            ) : (
              <DetailField
                key={column}
                column={column}
                value={editable && column === "글자수" ? String((values["회의내용"] || "").length) : values[column] || ""}
                recommended={column === "총인원" ? values["추천인원"] || "" : ""}
                editable={(editable && column !== "글자수") || (sheetMemo && column === "메모")}
                onChange={(value) => setValues((current) => ({ ...current, [column]: value }))}
              />
            ),
          )}
        </div>
        {row.can_edit && projects && (
          <div className="mt-5 flex flex-col gap-2 sm:flex-row sm:items-end">
            <label className="text-sm">
              프로젝트
              <select
                value={target}
                onChange={(event) => setTarget(event.target.value)}
                className="mt-1 block rounded-xl border border-line bg-white px-3 py-2"
              >
                <option value="">프로젝트 선택</option>
                {projects.map((project) => (
                  <option key={project.gid} value={project.gid}>
                    {project.name}
                  </option>
                ))}
              </select>
            </label>
            <button type="button" className="rounded-xl border border-line px-4 py-2 text-sm" onClick={() => onAssign(row.id, target)}>
              할당
            </button>
          </div>
        )}
        {overtime && projectGid !== UNASSIGNED && (
          <div className="mt-5 rounded-2xl border border-line p-4">
            <p className="text-sm font-medium">초과근무일지</p>
            <p className="mt-1 text-xs text-muted">과제 정보는 프로젝트 관리에 저장한 내용을 사용하고, 근무자는 회의참석자와 등록된 서명을 사용합니다.</p>
            <button
              type="button"
              disabled={logPending}
              className="mt-3 rounded-xl bg-ink px-4 py-2 text-sm text-white disabled:opacity-40"
              onClick={downloadLog}
            >
              {logPending ? "만드는 중" : "초과근무일지 다운로드"}
            </button>
          </div>
        )}
        <div className="mt-5 rounded-2xl border border-line p-4">
          <p className="text-sm font-medium">영수증 PDF</p>
          <p className="mt-1 text-xs text-muted">PDF나 사진을 연결하면 이 항목에서 받을 수 있습니다.</p>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <button
              type="button"
              disabled={!hasPdf}
              className="rounded-xl bg-ink px-4 py-2 text-sm text-white disabled:opacity-40"
              onClick={() => onDownload(row)}
            >
              영수증 PDF 다운로드
            </button>
            {canLink && (
              <label className="cursor-pointer rounded-xl border border-line px-4 py-2 text-sm">
                {linking ? "연결 중" : hasPdf ? "영수증 다시 연결" : "영수증 연결"}
                <input
                  type="file"
                  accept="application/pdf,image/jpeg,image/png,image/webp"
                  multiple
                  className="sr-only"
                  disabled={linking}
                  onChange={linkReceipt}
                />
              </label>
            )}
          </div>
        </div>
        {error && <p className="mt-3 text-sm text-copper">{error}</p>}
        <div className="mt-5 flex flex-wrap gap-2">
          {(editable || sheetMemo) && (
            <button
              type="submit"
              disabled={pending}
              className="rounded-xl bg-copper px-6 py-3 font-medium text-white disabled:opacity-60"
            >
              {pending ? "저장 중" : "저장"}
            </button>
          )}
          {row.can_delete && (
            <button type="button" className="rounded-xl border border-line px-4 py-3 text-sm text-muted" onClick={() => onRemove(row.id)}>
              삭제
            </button>
          )}
        </div>
      </form>
    </div>
  );
}

function DetailField({ column, value, recommended = "", editable, onChange }) {
  const wide = LONG_FIELDS.has(column);
  const className = "mt-1 w-full rounded-xl border border-line bg-white px-3 py-2 disabled:bg-paper";
  const dateValue = /^\d{4}-\d{2}-\d{2}$/.test(value) ? value : "";
  let control;
  if (!editable) {
    control = <p className="mt-1 min-h-10 whitespace-pre-wrap rounded-xl bg-paper px-3 py-2">{value || "-"}</p>;
  } else if (column === "사용일자" && (dateValue || !value)) {
    control = <input required type="date" value={dateValue} onChange={(event) => onChange(event.target.value)} className={className} />;
  } else if (column === "사용시각" && (/^\d{2}:\d{2}$/.test(value) || !value)) {
    control = <input type="time" value={value} onChange={(event) => onChange(event.target.value)} className={className} />;
  } else if (column === "연구비항목") {
    control = (
      <select
        required
        value={EXPENSE_CATEGORIES.includes(value) ? value : ""}
        onChange={(event) => onChange(event.target.value)}
        className={className}
      >
        <option value="">선택</option>
        {EXPENSE_CATEGORIES.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    );
  } else if (wide) {
    control = <textarea rows={3} value={value} onChange={(event) => onChange(event.target.value)} className={className} />;
  } else {
    control = <input value={value} onChange={(event) => onChange(event.target.value)} className={className} />;
  }
  const label = column === "메모" ? "메모" : column;
  return (
    <label className={`block text-sm ${wide ? "sm:col-span-2" : ""}`}>
      {label}
      {control}
      {column === "총인원" && recommended ? <p className="mt-1 text-xs text-muted">추천 인원 수 {recommended}</p> : null}
    </label>
  );
}
