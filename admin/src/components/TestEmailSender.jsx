import { useState } from "react";
import { adminApi } from "../api/client.js";
import "./TestEmailSender.css";

// Shown under Settings → Notifications. Sends one message with the
// SAVED SMTP settings and shows the server's real error if it fails —
// the quickest way to confirm mail works before switching it on.
export default function TestEmailSender() {
  const [to, setTo] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null); // { ok, message }

  async function handleSend() {
    setBusy(true);
    setResult(null);
    try {
      const data = await adminApi.sendTestEmail(to.trim());
      setResult({ ok: true, message: `Test email sent to ${data.to}. Check the inbox (and spam folder).` });
    } catch (e) {
      setResult({ ok: false, message: e.message });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="test-email">
      <h3 className="test-email-title">Send test email</h3>
      <p className="test-email-help">
        Uses the saved settings above, so save any changes first. Works even while email
        notifications are switched off. Leave the address blank to send to the internal alert email.
      </p>
      <div className="test-email-row">
        <input
          type="email"
          placeholder="you@example.com"
          value={to}
          onChange={(e) => setTo(e.target.value)}
          aria-label="Test email recipient"
        />
        <button type="button" className="btn-primary" onClick={handleSend} disabled={busy}>
          {busy ? "Sending…" : "Send test"}
        </button>
      </div>
      {result && (
        <p className={result.ok ? "test-email-ok" : "test-email-error"} role="status">{result.message}</p>
      )}
    </div>
  );
}
