import { useEffect, useRef, type ReactNode } from 'react';
import { X } from 'lucide-react';

interface SheetProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  side?: 'bottom' | 'right';
}

// Native <dialog>: focus trap, Escape and inert background come from the platform.
// Bottom sheet on phones; on desktop a centered card ("bottom") or a right-hand drawer ("right").
export function Sheet({ open, onClose, title, children, side = 'bottom' }: SheetProps) {
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  return (
    <dialog
      ref={ref}
      className={`sheet sheet-${side}`}
      aria-label={title}
      onClose={onClose}
      onClick={e => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="sheet-body">
        <header className="sheet-head">
          <h2>{title}</h2>
          <button className="icon-button" aria-label="Close" onClick={onClose}><X size={20} /></button>
        </header>
        <div className="sheet-content">{open && children}</div>
      </div>
    </dialog>
  );
}
