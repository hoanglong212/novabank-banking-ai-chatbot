import { useId, useRef, useState, type ClipboardEvent, type PointerEvent } from 'react';

/** One native, accessible input preserves paste/autofill/caret behavior; cells are visual only. */
export function VerificationCode({ value, onChange, disabled, invalid, shake }: {
  value: string; onChange: (value: string) => void; disabled: boolean; invalid: boolean; shake: boolean;
}) {
  const input = useRef<HTMLInputElement>(null);
  const labelId = useId();
  const [focused, setFocused] = useState(false);
  const [cursor, setCursor] = useState(0);

  function selectCell(event: PointerEvent<HTMLInputElement>) {
    if (disabled || !input.current) return;
    event.preventDefault();
    const bounds = event.currentTarget.getBoundingClientRect();
    const position = Math.min(value.length, Math.max(0, Math.min(5, Math.floor((event.clientX - bounds.left) / bounds.width * 6))));
    input.current.focus();
    input.current.setSelectionRange(position, Math.min(value.length, position + 1));
    setCursor(position);
  }

  function paste(event: ClipboardEvent<HTMLInputElement>) {
    const digits = event.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6);
    if (!digits) return;
    event.preventDefault();
    onChange(digits);
    setCursor(Math.min(digits.length, 5));
    // React commits the controlled value before restoring the native insertion point.
    requestAnimationFrame(() => input.current?.setSelectionRange(digits.length, digits.length));
  }

  return <label className="auth-field auth-code-field">
    <span id={labelId}>Verification code</span>
    <span className={`auth-otp-control${focused ? ' is-focused' : ''}${value.length === 6 ? ' is-complete' : ''}${shake ? ' has-error' : ''}`}
      data-invalid={invalid} data-disabled={disabled}>
      <input ref={input} className="auth-otp-input" autoComplete="one-time-code" inputMode="numeric"
        pattern="[0-9]{6}" minLength={6} maxLength={6} required value={value} disabled={disabled}
        aria-labelledby={labelId} aria-invalid={invalid} aria-describedby="auth-code-help" spellCheck={false}
        onChange={event => {
          const digits = event.target.value.replace(/\D/g, '').slice(0, 6);
          onChange(digits);
          setCursor(Math.min(event.target.selectionStart ?? digits.length, 5));
        }}
        onFocus={() => { setFocused(true); setCursor(Math.min(input.current?.selectionStart ?? value.length, 5)); }}
        onBlur={() => setFocused(false)}
        onSelect={event => setCursor(Math.min(event.currentTarget.selectionStart ?? value.length, 5))}
        onPointerDown={selectCell} onPaste={paste} />
      <span className="auth-otp-slots" aria-hidden="true">
        {Array.from({ length: 6 }, (_, index) => <span key={index}
          className={`auth-otp-slot${value[index] ? ' is-filled' : ''}${focused && cursor === index ? ' is-active' : ''}`}>
          {value[index] ? <span key={`${index}-${value[index]}`} className="auth-otp-digit">{value[index]}</span>
            : <span className="auth-otp-placeholder">·</span>}
        </span>)}
      </span>
    </span>
  </label>;
}
