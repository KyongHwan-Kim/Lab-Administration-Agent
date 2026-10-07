import { useEffect, useState } from "react";
import { api } from "./api";
import { LoginScreen } from "./components/LoginScreen";
import { Shell } from "./components/Shell";

export default function App() {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    api("/api/auth/me")
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setReady(true));
  }, []);

  if (!ready) {
    return <div className="grid min-h-screen place-items-center text-muted">불러오는 중</div>;
  }
  if (!user) return <LoginScreen onSuccess={setUser} />;
  return <Shell user={user} onLogout={() => setUser(null)} onUserChange={setUser} />;
}
