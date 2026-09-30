import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { adminApi, setCsrfToken } from "../api/client.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    adminApi
      .me()
      .then((data) => {
        setCsrfToken(data.csrf_token);
        setUser(data);
      })
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (username, password) => {
    const data = await adminApi.login(username, password);
    setCsrfToken(data.csrf_token);
    setUser(data);
    return data;
  }, []);

  const logout = useCallback(async () => {
    try {
      await adminApi.logout();
    } finally {
      setCsrfToken(null);
      setUser(null);
    }
  }, []);

  // Called by any page when a request comes back 401 mid-session (e.g.
  // the session expired server-side) — drops back to the login screen
  // without a full reload.
  const handleSessionExpired = useCallback(() => {
    setCsrfToken(null);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, handleSessionExpired }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
