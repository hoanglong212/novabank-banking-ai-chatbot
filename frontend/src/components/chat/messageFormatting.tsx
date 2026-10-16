export function formatTime(value: string) {
  const parsed = new Date(value);

  if (Number.isNaN(parsed.valueOf())) return '';

  return parsed.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
}

export function safeMessageParts(text: string) {
  // Minimal formatting; messages are rendered as text, NOT unsanitized model HTML.

  return text.split(/(\*\*[^*]+\*\*)/g).map((part, idx) =>
    part.startsWith('**') && part.endsWith('**') ? <strong key={idx}>
      {part.slice(2, -2)}
    </strong> : <span key={idx}>
      {part}
    </span>,
  );
}
