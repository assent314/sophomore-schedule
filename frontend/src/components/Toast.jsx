import React, { useEffect } from "react";

export default function Toast({ toast, onClose }) {
  useEffect(() => {
    if (!toast) return undefined;
    const t = setTimeout(onClose, 3200);
    return () => clearTimeout(t);
  }, [toast, onClose]);

  if (!toast) return null;
  return (
    <div className={`toast ${toast.error ? "error" : ""}`} onClick={onClose} role="status">
      {toast.message}
    </div>
  );
}
