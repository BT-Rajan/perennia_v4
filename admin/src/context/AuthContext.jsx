import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { adminApi, setCsrfToken } from "../api/client.js";

const AuthContext = createContext(null);

// Shown when the password was right but the browser dropped the session
// cookie — almost always a Secure cookie on a plain-http:// address.
const COOKIE_BLOCKED =
  window.location.protocol === "http:"
    ? "Signed in, but the browser refused the session cookie because this site is on plain http:// " +
      "while the server requires HTTPS cookies. Open the site over https://, or on a test server " +
      "re-run ./install.sh --public-ip=<server-ip>."
    : "Signed in, but the browser did not keep the session cookie. Check that cookies are allowed for this site.";

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
    // Confirm the session cookie actually stuck before entering the
    // dashboard; otherwise every page would bounce straight back to login.
    try {
      await adminApi.me();
    } catch (err) {
      setCsrfToken(null);
      throw err.status === 401 ? new Error(COOKIE_BLOCKED) : err;
    }
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
