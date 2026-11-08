'use client';
import { useEffect, useRef } from 'react';

/** A pop-up window that dims the page behind it. */
export default function Sheet({ open, onClose, title, children }: { open: boolean; onClose: () => void; title: string; children: React.ReactNode }) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const d = ref.current; if (!d) return;
    if (open && !d.open) { try { d.showModal(); } catch { d.setAttribute('open', ''); } }
    if (!open && d.open) d.close();
  }, [open]);
  return (
    <dialog ref={ref} className="sheet" aria-label={title} onClose={onClose} onCancel={onClose}>
      {open ? <div className="sheet-in"><h2>{title}</h2>{children}</div> : null}
    </dialog>
  );
}
