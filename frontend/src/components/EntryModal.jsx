import { useEffect, useState } from "react";
import { api } from "../api";
import { userLabel } from "../userLabel";

const SKIP = new Set(["순번", "글자수"]);
const LONG = new Set(["회의내용", "회의목적"]);
const EXPENSE_CATEGORIES = ["초과근무", "회의비"];
const SUGGESTIONS = {
  "영수증 제출": ["O", "분실"],
  사용목적: ["초과근무", "회의비"],
};

export function EntryModal({ project, onClose, onSaved }) {
  const columns = project.columns.filter((column) => !SKIP.has(column));
  const [values, setValues] = useState({});
  const [delivery, setDelivery] = useState([]);
  const [receipt, setReceipt] = useState([]);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  function setField(column, value) {
    setValues((current) => ({ ...current, [column]: value }));
  }

  async function submit(event) {
    event.preventDefault();
    setError("");
    setPending(true);
    try {
      const body = new FormData();
      body.append("payload", JSON.stringify(values));
      delivery.forEach((file) => body.append("delivery", file));
      receipt.forEach((file) => body.append("receipt", file));
      await api(`/api/overtime/projects/${project.gid}/entries`, { method: "POST", body });
      onSaved();
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
        className="max-h-[94vh] w-full overflow-y-auto rounded-t-3xl bg-card p-5 sm:max-w-3xl sm:rounded-3xl sm:p-6"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-xl font-semibold">항목 추가</h2>
            <p className="mt-1 text-sm text-muted">{project.name}에 저장됩니다.</p>
          </div>
          <button type="button" className="text-sm text-muted" onClick={onClose}>
            닫기
          </button>
        </div>
        <div className="mt-5 grid gap-3 sm:grid-cols-2">
          {columns.map((column) =>
            column === "회의참석자" ? (
              <AttendeePicker key={column} projectGid={project.gid} onChange={(value) => setField(column, value)} />
            ) : (
              <Field key={column} column={column} value={values[column] || ""} onChange={(value) => setField(column, value)} />
            ),
          )}
          <label className="block text-sm sm:col-span-2">
            메모
            <textarea
              rows={3}
              value={values["메모"] || ""}
              onChange={(event) => setField("메모", event.target.value)}
              className="mt-1 w-full rounded-xl border border-line bg-white px-3 py-2"
            />
          </label>
        </div>
        <div className="mt-5 grid gap-3 sm:grid-cols-2">
          <label className="text-sm">
            배달 내역 사진
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              multiple
              className="mt-1 block w-full text-xs"
              onChange={(event) => setDelivery(Array.from(event.target.files || []))}
            />
          </label>
          <label className="text-sm">
            영수증 사진
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              multiple
              className="mt-1 block w-full text-xs"
              onChange={(event) => setReceipt(Array.from(event.target.files || []))}
            />
          </label>
        </div>
        <p className="mt-2 text-xs text-muted">사진을 첨부하면 항목과 함께 한 열 PDF로 저장됩니다.</p>
        {error && <p className="mt-3 text-sm text-copper">{error}</p>}
        <button
          type="submit"
          disabled={pending}
          className="mt-5 w-full rounded-xl bg-copper py-3 font-medium text-white disabled:opacity-60 sm:w-auto sm:px-6"
        >
          {pending ? "저장 중" : "저장"}
        </button>
      </form>
    </div>
  );
}

export function AttendeePicker({ projectGid, value = "", onChange }) {
  const [members, setMembers] = useState([]);
  const [externals, setExternals] = useState([]);
  const [memberIds, setMemberIds] = useState([]);
  const [externalIds, setExternalIds] = useState([]);
  const [affiliation, setAffiliation] = useState("");
  const [position, setPosition] = useState("");
  const [personName, setPersonName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);
  const [ready, setReady] = useState(false);
  const [initialValue] = useState(value);
  const summary = composeAttendees(members, externals, memberIds, externalIds);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api(`/api/overtime/projects/${projectGid}/attendees`)
      .then((data) => {
        if (cancelled) return;
        const nextMembers = [...data.members].sort((a, b) => userLabel(a).localeCompare(userLabel(b), "ko"));
        const nextExternals = [...data.externals].sort((a, b) => externalLabel(a).localeCompare(externalLabel(b), "ko"));
        const labels = new Set(
          String(initialValue)
            .split(",")
            .map((item) => item.trim())
            .filter(Boolean),
        );
        setMembers(nextMembers);
        setExternals(nextExternals);
        setMemberIds(
          nextMembers.filter((member) => labels.has(userLabel(member)) || labels.has(member.username)).map((member) => member.id),
        );
        setExternalIds(nextExternals.filter((person) => labels.has(externalLabel(person))).map((person) => person.id));
        setReady(true);
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
  }, [projectGid, initialValue]);

  useEffect(() => {
    if (ready) onChange(summary);
  }, [summary, ready]);

  function toggle(id, selected, setSelected) {
    setSelected((current) => (current.includes(id) ? current.filter((item) => item !== id) : [...current, id]));
  }

  async function addExternal() {
    setError("");
    setAdding(true);
    try {
      const created = await api("/api/overtime/externals", {
        method: "POST",
        body: JSON.stringify({ affiliation, position, name: personName }),
      });
      setExternals((current) => {
        if (current.some((item) => item.id === created.id)) return current;
        return [...current, created].sort((a, b) => externalLabel(a).localeCompare(externalLabel(b), "ko"));
      });
      setExternalIds((current) => (current.includes(created.id) ? current : [...current, created.id]));
      setAffiliation("");
      setPosition("");
      setPersonName("");
    } catch (err) {
      setError(err.message);
    } finally {
      setAdding(false);
    }
  }

  return (
    <div className="text-sm sm:col-span-2">
      회의참석자
      <div className="mt-1 rounded-2xl border border-line bg-white p-3">
        {loading && <p className="text-muted">참석자 목록을 불러오는 중</p>}
        {!loading && (
          <>
            <p className="text-xs font-medium text-muted">참여 연구원</p>
            {members.length === 0 ? (
              <p className="mt-2 text-muted">이 프로젝트에 등록된 연구원이 없습니다.</p>
            ) : (
              <div className="mt-2 flex flex-wrap gap-2">
                {members.map((member) => (
                  <Chip
                    key={member.id}
                    selected={memberIds.includes(member.id)}
                    onClick={() => toggle(member.id, memberIds, setMemberIds)}
                    label={member.role ? `${userLabel(member)} · ${member.role}` : userLabel(member)}
                  />
                ))}
              </div>
            )}

            <p className="mt-4 text-xs font-medium text-muted">외부 인원</p>
            {externals.length === 0 ? (
              <p className="mt-2 text-muted">저장된 외부 인원이 없습니다.</p>
            ) : (
              <div className="mt-2 flex flex-wrap gap-2">
                {externals.map((person) => (
                  <Chip
                    key={person.id}
                    selected={externalIds.includes(person.id)}
                    onClick={() => toggle(person.id, externalIds, setExternalIds)}
                    label={externalLabel(person)}
                  />
                ))}
              </div>
            )}

            <div className="mt-4 grid gap-2 sm:grid-cols-3">
              <label>
                소속
                <input
                  value={affiliation}
                  onChange={(event) => setAffiliation(event.target.value)}
                  className="mt-1 w-full rounded-xl border border-line px-3 py-2"
                />
              </label>
              <label>
                직급
                <input
                  value={position}
                  onChange={(event) => setPosition(event.target.value)}
                  className="mt-1 w-full rounded-xl border border-line px-3 py-2"
                />
              </label>
              <label>
                성함
                <input
                  value={personName}
                  onChange={(event) => setPersonName(event.target.value)}
                  className="mt-1 w-full rounded-xl border border-line px-3 py-2"
                />
              </label>
            </div>
            <button
              type="button"
              disabled={adding}
              onClick={addExternal}
              className="mt-2 rounded-xl border border-line px-3 py-2 text-sm disabled:opacity-60"
            >
              {adding ? "추가 중" : "외부 인원 추가"}
            </button>
            <p className="mt-3 text-xs text-muted">
              {summary ? `저장되는 참석자: ${summary}` : "선택한 참석자가 없습니다."}
            </p>
          </>
        )}
        {error && <p className="mt-2 text-copper">{error}</p>}
      </div>
    </div>
  );
}

function Chip({ selected, onClick, label }) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      onClick={onClick}
      className={`rounded-full px-3 py-1.5 text-sm ${selected ? "bg-pine text-white" : "border border-line bg-paper text-ink"}`}
    >
      {label}
    </button>
  );
}

function externalLabel(person) {
  return `${person.affiliation} ${person.position} ${person.name}`;
}

function composeAttendees(members, externals, memberIds, externalIds) {
  const labels = [
    ...members.filter((member) => memberIds.includes(member.id)).map((member) => userLabel(member)),
    ...externals.filter((person) => externalIds.includes(person.id)).map(externalLabel),
  ];
  labels.sort((a, b) => a.localeCompare(b, "ko"));
  return labels.join(", ");
}

function Field({ column, value, onChange }) {
  const wide = LONG.has(column);
  const listId = `suggest-${column.replace(/\s+/g, "-")}`;
  const className = "mt-1 w-full rounded-xl border border-line bg-white px-3 py-2";
  let control;
  if (column === "사용일자") {
    control = <input required type="date" value={value} onChange={(event) => onChange(event.target.value)} className={className} />;
  } else if (column === "사용시각") {
    control = <input type="time" value={value} onChange={(event) => onChange(event.target.value)} className={className} />;
  } else if (LONG.has(column)) {
    control = <textarea rows={3} value={value} onChange={(event) => onChange(event.target.value)} className={className} />;
  } else if (column === "연구비항목") {
    control = (
      <select required value={value} onChange={(event) => onChange(event.target.value)} className={className}>
        <option value="">선택</option>
        {EXPENSE_CATEGORIES.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    );
  } else if (SUGGESTIONS[column]) {
    control = (
      <>
        <input list={listId} value={value} onChange={(event) => onChange(event.target.value)} className={className} />
        <datalist id={listId}>
          {SUGGESTIONS[column].map((option) => (
            <option key={option} value={option} />
          ))}
        </datalist>
      </>
    );
  } else {
    control = <input value={value} onChange={(event) => onChange(event.target.value)} className={className} />;
  }

  return (
    <label className={`block text-sm ${wide ? "sm:col-span-2" : ""}`}>
      {column}
      {control}
    </label>
  );
}
