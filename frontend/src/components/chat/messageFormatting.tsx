import { Fragment } from 'react';

// Only VietQR's own image service or an inline PNG from its API may render as an image.
const VIETQR = /^!\[VietQR\]\((https:\/\/img\.vietqr\.io\/image\/[^\s)"'<>]+|data:image\/png;base64,[A-Za-z0-9+/=]+)\)$/;

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
      <img src={qr[1]} alt="VietQR payment code" loading="lazy" />
      <figcaption>
        <span>Scan with any banking app</span>
        <a href={qr[1]} target="_blank" rel="noopener noreferrer">Open image</a>
      </figcaption>
    </figure> : <Fragment key={idx}>
      {emphasis(part.trimEnd())}
    </Fragment>;
  });
}
