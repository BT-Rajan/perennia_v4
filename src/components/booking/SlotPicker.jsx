import { useEffect, useState } from "react";
import { api } from "../../api/client.js";
import { useLang } from "../../context/LangContext.jsx";
import "./SlotPicker.css";

export default function SlotPicker({ date, serviceId, value, onChange, emptyLabel }) {
  const { copy } = useLang();
  const [slots, setSlots] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!date) {
      setSlots([]);
      return;
    }
    let cancelled = false;
    setLoading(true);
    api.getSlots(date, serviceId).then((s) => {
      if (!cancelled) {
        setSlots(s);
        setLoading(false);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [date, serviceId]);

  if (!date) return <div className="bk-slots-empty">{emptyLabel}</div>;
  if (loading) return <div className="bk-slots-empty">…</div>;
  if (slots.length === 0) return <div className="bk-slots-empty">{copy.booking.noAvailability}</div>;

  return (
    <div className="bk-slots">
      {slots.map((s) => (
        <button
          key={s}
          type="button"
          className={`bk-slot${value === s ? " bk-slot-active" : ""}`}
          onClick={() => onChange(s)}
        >
          {s}
        </button>
      ))}
    </div>
  );
}
