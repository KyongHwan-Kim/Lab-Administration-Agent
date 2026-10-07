import { useState } from "react";
import { api } from "../api";
import { userLabel } from "../userLabel";
import logo from "../assets/logo.png";
import { AccountPage } from "./AccountPage";
import { BrandLogo } from "./BrandLogo";
import { LogoAdmin } from "./LogoAdmin";
import { OvertimePage } from "./OvertimePage";
import { ProjectAdmin } from "./ProjectAdmin";
import { UserAdmin } from "./UserAdmin";
import { WorkLogPage } from "./WorkLogPage";

export function Shell({ user, onLogout, onUserChange }) {
  const [section, setSection] = useState("pdf");
  const [overtimeOpen, setOvertimeOpen] = useState(true);
  const [manageOpen, setManageOpen] = useState(true);
  const [logoRevision, setLogoRevision] = useState(0);
  const [menuOpen, setMenuOpen] = useState(false);
  const visibleSection = !user.is_admin && (section === "projects" || section === "logo" || section === "users") ? "pdf" : section;

  async function logout() {
    await api("/api/auth/logout", { method: "POST" });
    onLogout();
  }

  return (
    <div className="min-h-screen lg:grid lg:h-dvh lg:grid-cols-[240px_minmax(0,1fr)] lg:overflow-hidden">
      <header className="sticky top-0 z-20 flex items-center justify-between border-b border-line bg-card px-4 py-3 lg:hidden">
        <button
          type="button"
          className="rounded-lg border border-line px-3 py-2 text-sm"
          onClick={() => setMenuOpen(true)}
        >
          메뉴
        </button>
        <img src={logo} alt="연구실 행정" className="h-7 w-auto" />
        <button type="button" className="text-sm text-muted" onClick={() => setSection("account")}>
          {userLabel(user)}
        </button>
      </header>

      {menuOpen && (
        <button
          type="button"
          aria-label="메뉴 닫기"
          className="fixed inset-0 z-30 bg-ink/40 lg:hidden"
          onClick={() => setMenuOpen(false)}
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-40 flex h-dvh w-64 flex-col overflow-hidden bg-ink text-white transition-transform lg:static lg:h-full lg:w-auto lg:translate-x-0 ${
          menuOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="px-4 pt-5">
          <img src={logo} alt="yeonpil" className="h-8 w-auto" />
        </div>
        <nav className="min-h-0 flex-1 space-y-1 overflow-y-auto px-3 pt-4">
          {user.is_admin && (
            <div>
              <button
                type="button"
                className="flex w-full items-center gap-2 rounded-xl px-3 py-1.5 text-left text-sm font-medium hover:bg-white/10"
                aria-expanded={manageOpen}
                onClick={() => setManageOpen((open) => !open)}
              >
                <span className="w-3 text-xs text-white/70">{manageOpen ? "▾" : "▸"}</span>
                관리
              </button>
              {manageOpen && (
                <div className="ml-4 border-l border-white/25 pl-2">
                  {[
                    ["projects", "프로젝트 관리"],
                    ["users", "사용자 등록"],
                    ["logo", "로고 변경"],
                  ].map(([id, label]) => (
                    <div key={id} className="relative">
                      <span className="absolute top-1/2 -left-2 h-px w-2 bg-white/25" />
                      <MenuButton active={visibleSection === id} onClick={() => setSection(id)} close={() => setMenuOpen(false)}>
                        {label}
                      </MenuButton>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
          <div>
            <button
              type="button"
              className="flex w-full items-center gap-2 rounded-xl px-3 py-1.5 text-left text-sm font-medium hover:bg-white/10"
              aria-expanded={overtimeOpen}
              onClick={() => setOvertimeOpen((open) => !open)}
            >
              <span className="w-3 text-xs text-white/70">{overtimeOpen ? "▾" : "▸"}</span>
              초과근무
            </button>
            {overtimeOpen && (
              <div className="ml-4 border-l border-white/25 pl-2">
                {[
                  ["pdf", "영수증 등록"],
                  ["sheet", "사용 내역"],
                  ["worklog", "초과근무일지"],
                ].map(([id, label]) => (
                  <div key={id} className="relative">
                    <span className="absolute top-1/2 -left-2 h-px w-2 bg-white/25" />
                    <MenuButton active={section === id} onClick={() => setSection(id)} close={() => setMenuOpen(false)}>
                      {label}
                    </MenuButton>
                  </div>
                ))}
              </div>
            )}
          </div>
        </nav>
        <div className="mt-auto space-y-1 px-4 py-4">
          <BrandLogo revision={logoRevision} className="mb-3 h-10 w-auto max-w-full" />
          <button
            type="button"
            className={`w-full rounded-xl px-3 py-1.5 text-left text-sm ${
              visibleSection === "account" ? "bg-white/10 font-medium text-white" : "text-white/80 hover:bg-white/10"
            }`}
            onClick={() => {
              setSection("account");
              setMenuOpen(false);
            }}
          >
            {userLabel(user)}
            {user.is_admin && <span className="ml-2 text-xs text-white/50">관리자</span>}
          </button>
          <button
            type="button"
            className="w-full rounded-xl px-3 py-1.5 text-left text-sm text-white/70 hover:bg-white/10"
            onClick={logout}
          >
            로그아웃
          </button>
        </div>
      </aside>

      <main className="min-w-0 px-4 py-5 sm:px-6 lg:h-full lg:min-h-0 lg:overflow-y-auto lg:px-8 lg:py-8">
        {visibleSection === "projects" ? (
          <ProjectAdmin />
        ) : visibleSection === "logo" ? (
          <LogoAdmin revision={logoRevision} onChanged={() => setLogoRevision((value) => value + 1)} />
        ) : visibleSection === "users" ? (
          <UserAdmin currentUserId={user.id} onCurrentUser={onUserChange} />
        ) : visibleSection === "account" ? (
          <AccountPage user={user} onUserChange={onUserChange} />
        ) : visibleSection === "worklog" ? (
          <WorkLogPage />
        ) : (
          <OvertimePage section={visibleSection} />
        )}
      </main>
    </div>
  );
}

function MenuButton({ active, onClick, close, children }) {
  return (
    <button
      type="button"
      className={`w-full rounded-xl px-3 py-1.5 text-left text-sm ${
        active ? "bg-white/10 font-medium" : "text-white/75 hover:bg-white/10"
      }`}
      onClick={() => {
        onClick();
        close();
      }}
    >
      {children}
    </button>
  );
}
