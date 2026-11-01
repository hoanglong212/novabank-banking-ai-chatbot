import { Fragment } from 'react';

// Saved tool messages retain their legacy marker; only inline demo PNGs render.
const VIETQR = /^!\[VietQR\]\((data:image\/png;base64,[A-Za-z0-9+/=]+)\)$/;

export function formatTime(value: string) {
  const parsed = new Date(value);

  if (Number.isNaN(parsed.valueOf())) return '';

  return parsed.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
}

function emphasis(text: string) {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, idx) =>
    part.startsWith('**') && part.endsWith('**') ? <strong key={idx}>
      {part.slice(2, -2)}
    </strong> : <span key={idx}>
      {part}
    </span>,
  );
}

export function safeMessageParts(text: string) {
  // Minimal formatting; messages are rendered as text, NOT unsanitized model HTML.

  return text.split(/(!\[VietQR\]\([^)\s]+\))/g).map((part, idx) => {
    const qr = part.match(VIETQR);
    return qr ? <figure className="qr-card" key={idx}>
      <img src={qr[1]} alt="NovaBank demo QR code" loading="lazy" />
      <figcaption>
        <span>NovaBank simulator only</span>
        <a href={qr[1]} download="NovaBank-demo-QR.png">Download image</a>
      </figcaption>
    </figure> : <Fragment key={idx}>
      {emphasis(part.trimEnd())}
    </Fragment>;
  });
}
