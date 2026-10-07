import { useEffect, useState } from "react";
import { api } from "../api";
import { userLabel } from "../userLabel";

const PROFILE_FIELDS = [
  ["name", "프로젝트 이름"],
  ["project_number", "과제번호"],
  ["principal_investigator", "연구책임자"],
  ["funding_agency", "연구지원기관"],
  ["program_name", "사업명"],
  ["research_title", "연구과제명"],
];

function emptyProfile() {
  return Object.fromEntries(PROFILE_FIELDS.map(([key]) => [key, ""]));
}

function profileFrom(project) {
  return Object.fromEntries(PROFILE_FIELDS.map(([key]) => [key, project[key] || ""]));
}

export function ProjectAdmin() {
  const [projects, setProjects] = useState([]);
  const [users, setUsers] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [name, setName] = useState("");
  const [profile, setProfile] = useState(emptyProfile());
  const [memberUserId, setMemberUserId] = useState("");
  const [memberRole, setMemberRole] = useState("");
  const [drafts, setDrafts] = useState({});
  const [cardLabel, setCardLabel] = useState("");
  const [cardNumber, setCardNumber] = useState("");
  const [cardDrafts, setCardDrafts] = useState({});
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  const selected = projects.find((project) => project.id === selectedId) || null;

  useEffect(() => {
    Promise.all([api("/api/projects"), api("/api/users")])
      .then(([projectItems, userItems]) => {
        setProjects(projectItems);
        setUsers(userItems);
        setSelectedId((current) => current || projectItems[0]?.id || null);
      })
      .catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    if (!selected) return;
    setProfile(profileFrom(selected));
    setDrafts(
      Object.fromEntries(
        selected.members.map((member) => [member.id, { user_id: String(member.user_id), role: member.role }]),
      ),
    );
    setCardDrafts(
      Object.fromEntries((selected.cards || []).map((card) => [card.id, { label: card.label, number: card.number }])),
    );
  }, [selected]);

  function replaceProject(updated) {
    setProjects((current) => current.map((project) => (project.id === updated.id ? updated : project)));
  }

  async function createProject(event) {
    event.preventDefault();
    setError("");
    setPending(true);
    try {
      const created = await api("/api/projects", { method: "POST", body: JSON.stringify({ name }) });
      setProjects((current) => [...current, created]);
      setSelectedId(created.id);
      setName("");
    } catch (err) {
      setError(err.message);
    } finally {
      setPending(false);
    }
  }

  async function saveProfile(event) {
    event.preventDefault();
    setError("");
    setPending(true);
    try {
      const updated = await api(`/api/projects/${selected.id}`, { method: "PATCH", body: JSON.stringify(profile) });
      replaceProject(updated);
      setProfile(profileFrom(updated));
    } catch (err) {
      setError(err.message);
    } finally {
      setPending(false);
    }
  }

  async function removeProject() {
    if (!window.confirm(`「${selected.name}」 프로젝트를 삭제할까요? 이 앱에 저장된 사용 내역도 함께 삭제됩니다.`)) return;
    setError("");
    setPending(true);
    try {
      await api(`/api/projects/${selected.id}`, { method: "DELETE" });
      const next = projects.filter((project) => project.id !== selected.id);
      setProjects(next);
      setSelectedId(next[0]?.id || null);
    } catch (err) {
      setError(err.message);
    } finally {
      setPending(false);
    }
  }

  async function addMember(event) {
    event.preventDefault();
    if (!memberUserId) {
      setError("참여 인원을 선택해 주세요.");
      return;
    }
    setError("");
    setPending(true);
    try {
      replaceProject(
        await api(`/api/projects/${selected.id}/members`, {
          method: "POST",
          body: JSON.stringify({ user_id: Number(memberUserId), role: memberRole }),
        }),
      );
      setMemberUserId("");
      setMemberRole("");
    } catch (err) {
      setError(err.message);
    } finally {
      setPending(false);
    }
  }

  async function saveMember(memberId) {
    const draft = drafts[memberId];
    setError("");
    setPending(true);
    try {
      replaceProject(
        await api(`/api/projects/${selected.id}/members/${memberId}`, {
          method: "PATCH",
          body: JSON.stringify({ user_id: Number(draft.user_id), role: draft.role }),
        }),
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setPending(false);
    }
  }

  async function removeMember(memberId) {
    setError("");
    setPending(true);
    try {
      replaceProject(await api(`/api/projects/${selected.id}/members/${memberId}`, { method: "DELETE" }));
    } catch (err) {
      setError(err.message);
    } finally {
      setPending(false);
    }
  }

  async function addCard(event) {
    event.preventDefault();
    if (!cardNumber.trim()) {
      setError("카드 끝자리를 입력해 주세요.");
      return;
    }
    setError("");
    setPending(true);
    try {
      replaceProject(
        await api(`/api/projects/${selected.id}/cards`, {
          method: "POST",
          body: JSON.stringify({ label: cardLabel, number: cardNumber }),
        }),
      );
      setCardLabel("");
      setCardNumber("");
    } catch (err) {
      setError(err.message);
    } finally {
      setPending(false);
    }
  }

  async function saveCard(cardId) {
    const draft = cardDrafts[cardId];
    setError("");
    setPending(true);
    try {
      replaceProject(
        await api(`/api/projects/${selected.id}/cards/${cardId}`, {
          method: "PATCH",
          body: JSON.stringify({ label: draft.label, number: draft.number }),
        }),
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setPending(false);
    }
  }

  async function removeCard(cardId) {
    setError("");
    setPending(true);
    try {
      replaceProject(await api(`/api/projects/${selected.id}/cards/${cardId}`, { method: "DELETE" }));
    } catch (err) {
      setError(err.message);
    } finally {
      setPending(false);
    }
  }

  const participants = users.filter((user) => !user.is_admin);
  const availableUsers = participants.filter((user) => !selected?.members.some((member) => member.user_id === user.id));

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">프로젝트 관리</h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-muted">
          과제를 추가하고 이름, 참여 인원, 법인카드를 수정합니다. 카드는 끝자리만 등록합니다. 영수증 카드 번호의 끝자리가 같으면 그 프로젝트로 배정됩니다.
        </p>
      </div>

      <form onSubmit={createProject} className="flex flex-col gap-2 rounded-3xl border border-line bg-card p-4 sm:flex-row sm:items-end sm:p-6">
        <label className="block flex-1 text-sm">
          새 프로젝트
          <input
            value={name}
            onChange={(event) => setName(event.target.value)}
            className="mt-2 w-full rounded-xl border border-line bg-white px-3 py-2 outline-none focus:border-copper"
            placeholder="과제 이름"
          />
        </label>
        <button type="submit" disabled={pending} className="rounded-xl bg-ink px-4 py-2 text-sm text-white disabled:opacity-60">
          추가
        </button>
      </form>

      {error && <p className="text-sm text-copper">{error}</p>}

      <label className="block text-sm">
        등록된 프로젝트
        <select
          value={selectedId ?? ""}
          onChange={(event) => setSelectedId(Number(event.target.value))}
          className="mt-1 block w-full max-w-md rounded-xl border border-line bg-white px-3 py-2"
        >
          {projects.length === 0 && <option value="">등록된 프로젝트가 없습니다</option>}
          {projects.map((project) => (
            <option key={project.id} value={project.id}>
              {project.name}
            </option>
          ))}
        </select>
      </label>

      {selected ? (
        <section className="rounded-3xl border border-line bg-card p-4 sm:p-6">
            <form onSubmit={saveProfile} className="space-y-3">
              <div className="grid gap-3 sm:grid-cols-2">
                {PROFILE_FIELDS.map(([key, label]) => (
                  <label key={key} className={`block text-sm ${key === "name" || key === "research_title" ? "sm:col-span-2" : ""}`}>
                    {label}
                    <input
                      value={profile[key]}
                      onChange={(event) => setProfile((current) => ({ ...current, [key]: event.target.value }))}
                      className="mt-2 w-full rounded-xl border border-line bg-white px-3 py-2 outline-none focus:border-copper"
                    />
                  </label>
                ))}
              </div>
              <div className="flex flex-wrap gap-2">
                <button type="submit" disabled={pending} className="rounded-xl bg-pine px-4 py-2 text-sm text-white disabled:opacity-60">
                  저장
                </button>
                <button type="button" disabled={pending} onClick={removeProject} className="rounded-xl border border-line px-4 py-2 text-sm">
                  삭제
                </button>
              </div>
            </form>

            <form onSubmit={addMember} className="mt-6 grid gap-2 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto] sm:items-end">
              <label className="text-sm">
                참여 인원
                <select
                  value={memberUserId}
                  onChange={(event) => setMemberUserId(event.target.value)}
                  className="mt-2 w-full rounded-xl border border-line bg-white px-3 py-2"
                >
                  <option value="">사용자 선택</option>
                  {availableUsers.map((user) => (
                    <option key={user.id} value={user.id}>
                      {userLabel(user)}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-sm">
                역할
                <input
                  value={memberRole}
                  onChange={(event) => setMemberRole(event.target.value)}
                  className="mt-2 w-full rounded-xl border border-line bg-white px-3 py-2 outline-none focus:border-copper"
                  placeholder="예: 참여연구원"
                />
              </label>
              <button type="submit" disabled={pending} className="rounded-xl bg-ink px-4 py-2 text-sm text-white disabled:opacity-60">
                인원 추가
              </button>
            </form>

            <ul className="mt-5 divide-y divide-line">
              {selected.members.length === 0 && <li className="py-4 text-sm text-muted">등록된 참여 인원이 없습니다.</li>}
              {selected.members.map((member) => {
                const draft = drafts[member.id] || { user_id: String(member.user_id), role: member.role };
                return (
                  <li key={member.id} className="grid gap-2 py-3 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto] sm:items-center">
                    <select
                      value={draft.user_id}
                      onChange={(event) =>
                        setDrafts((current) => ({ ...current, [member.id]: { ...draft, user_id: event.target.value } }))
                      }
                      className="rounded-xl border border-line bg-white px-3 py-2 text-sm"
                    >
                      {participants.map((user) => (
                        <option key={user.id} value={user.id}>
                          {userLabel(user)}
                        </option>
                      ))}
                    </select>
                    <input
                      value={draft.role}
                      onChange={(event) =>
                        setDrafts((current) => ({ ...current, [member.id]: { ...draft, role: event.target.value } }))
                      }
                      className="rounded-xl border border-line bg-white px-3 py-2 text-sm outline-none focus:border-copper"
                      placeholder="역할"
                    />
                    <div className="flex gap-2">
                      <button
                        type="button"
                        disabled={pending}
                        onClick={() => saveMember(member.id)}
                        className="rounded-xl border border-line px-3 py-2 text-sm"
                      >
                        수정
                      </button>
                      <button
                        type="button"
                        disabled={pending}
                        onClick={() => removeMember(member.id)}
                        className="rounded-xl border border-line px-3 py-2 text-sm text-copper"
                      >
                        삭제
                      </button>
                    </div>
                  </li>
                );
              })}
            </ul>

            <form onSubmit={addCard} className="mt-6 grid gap-2 sm:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)_auto] sm:items-end">
              <label className="text-sm">
                카드 이름
                <input
                  value={cardLabel}
                  onChange={(event) => setCardLabel(event.target.value)}
                  className="mt-2 w-full rounded-xl border border-line bg-white px-3 py-2 outline-none focus:border-copper"
                  placeholder="예: KB법인"
                />
              </label>
              <label className="text-sm">
                카드 끝자리
                <input
                  value={cardNumber}
                  onChange={(event) => setCardNumber(event.target.value)}
                  inputMode="numeric"
                  maxLength={8}
                  className="mt-2 w-full rounded-xl border border-line bg-white px-3 py-2 outline-none focus:border-copper"
                  placeholder="예: 3818"
                />
              </label>
              <button type="submit" disabled={pending} className="rounded-xl bg-ink px-4 py-2 text-sm text-white disabled:opacity-60">
                카드 추가
              </button>
            </form>
            <ul className="mt-3 divide-y divide-line">
              {(selected.cards || []).length === 0 && <li className="py-4 text-sm text-muted">등록된 카드가 없습니다.</li>}
              {(selected.cards || []).map((card) => {
                const draft = cardDrafts[card.id] || { label: card.label, number: card.number };
                return (
                  <li key={card.id} className="grid gap-2 py-3 sm:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)_auto] sm:items-center">
                    <input
                      value={draft.label}
                      onChange={(event) =>
                        setCardDrafts((current) => ({ ...current, [card.id]: { ...draft, label: event.target.value } }))
                      }
                      className="rounded-xl border border-line bg-white px-3 py-2 text-sm outline-none focus:border-copper"
                      placeholder="카드 이름"
                    />
                    <input
                      value={draft.number}
                      onChange={(event) =>
                        setCardDrafts((current) => ({ ...current, [card.id]: { ...draft, number: event.target.value } }))
                      }
                      inputMode="numeric"
                      maxLength={8}
                      className="rounded-xl border border-line bg-white px-3 py-2 text-sm outline-none focus:border-copper"
                      placeholder="끝자리"
                    />
                    <div className="flex gap-2">
                      <button
                        type="button"
                        disabled={pending}
                        onClick={() => saveCard(card.id)}
                        className="rounded-xl border border-line px-3 py-2 text-sm"
                      >
                        수정
                      </button>
                      <button
                        type="button"
                        disabled={pending}
                        onClick={() => removeCard(card.id)}
                        className="rounded-xl border border-line px-3 py-2 text-sm text-copper"
                      >
                        삭제
                      </button>
                    </div>
                  </li>
                );
              })}
            </ul>
        </section>
      ) : (
        <p className="text-sm text-muted">등록된 프로젝트가 없습니다.</p>
      )}
    </div>
  );
}
