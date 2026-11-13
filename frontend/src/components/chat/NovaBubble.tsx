import { useState, type DragEvent } from 'react';
import { ScanLine, Sparkles } from 'lucide-react';

import type { useBankingChat } from '../../hooks/useBankingChat';
import type { TransferStart } from '../../types';
import { Sheet } from '../ui/Sheet';
import { decodeQrImage, toTransfer } from '../qr/QrStudio';
import { Assistant } from './Assistant';

interface NovaBubbleProps {
  chat: ReturnType<typeof useBankingChat>;
  pay: (start: TransferStart) => void;
}

// Floating Nova: opens the same conversation in a drawer. A dropped QR image goes to the
// bank's decoder and straight to transfer review; the assistant never sees the file.
export function NovaBubble({ chat, pay }: NovaBubbleProps) {
  const [open, setOpen] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState('');

  async function drop(event: DragEvent) {
    event.preventDefault();
    setDragging(false);
    const file = event.dataTransfer.files[0];
    if (!file) return;
    setError('');
    try {
      const decoded = await decodeQrImage(chat.user, file);
      setOpen(false);
      pay(toTransfer(decoded));
    } catch (err) {
      setError((err as Error).message);
      setOpen(true);
    }
  }
  const dropTarget = {
    onDragOver: (event: DragEvent) => {
      if (!event.dataTransfer.types.includes('Files')) return;
      event.preventDefault();
      setDragging(true);
    },
    onDragLeave: () => setDragging(false),
    onDrop: (event: DragEvent) => void drop(event),
  };

  return <>
    <button className={`nova-bubble ${dragging ? 'is-dragging' : ''}`} aria-label="Open Nova assistant" onClick={() => setOpen(true)} {...dropTarget}>
      {dragging ? <ScanLine size={26} aria-hidden="true" /> : <Sparkles size={26} aria-hidden="true" />}
      {dragging && <span>Drop QR to pay</span>}
    </button>
    <Sheet open={open} onClose={() => { setOpen(false); setError(''); }} title="Nova assistant" side="right">
      <div className={`nova-drawer ${dragging ? 'is-dragging' : ''}`} {...dropTarget}>
        <p className="nova-drop-hint"><ScanLine size={16} aria-hidden="true" />Drop a NovaBank QR image here to pay. Nova never reads your files.</p>
        {error && <p role="alert" className="form-error">{error}</p>}
        <Assistant chat={chat} openTransfer={draftId => { setOpen(false); pay({ draftId }); }} />
      </div>
    </Sheet>
  </>;
}
