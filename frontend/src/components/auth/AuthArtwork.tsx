// Decorative, non-scannable sample code. Never used to initiate a payment.
const qrCells = Array.from({ length: 29 * 29 }, (_, index) => {
  const x = index % 29, y = Math.floor(index / 29);
  const finder = (ox: number, oy: number) => {
    const dx = x - ox, dy = y - oy;
    if (dx < -1 || dy < -1 || dx > 7 || dy > 7) return null;
    return dx >= 0 && dy >= 0 && dx <= 6 && dy <= 6 && (dx === 0 || dy === 0 || dx === 6 || dy === 6 || (dx >= 2 && dx <= 4 && dy >= 2 && dy <= 4));
  };
  const fixed = finder(0, 0) ?? finder(22, 0) ?? finder(0, 22);
  return (fixed ?? (((x * 17 + y * 31 + x * y * 7) ^ (x + y * 3)) % 11 < 5))
    ? <rect key={index} x={x} y={y} width="1" height="1" /> : null;
});

export function AuthArtwork() {
  return <div className="auth-vector-panel">
    <div className="auth-art-brand" aria-label="NovaBank">
      <span className="auth-art-logo" aria-hidden="true">N</span><span>nova<span>bank</span></span><small>CHATBOT</small>
    </div>
    <div className="auth-art-copy">
      <h2>Sign in to pick up<br />the <span>conversation.</span></h2>
      <p>QR payments, FAQs, transactions, balances and bill reminders.</p>
    </div>
    <div className="auth-art-account" aria-hidden="true">
      <span>PAYMENT ACCOUNT</span><strong>12,450,000 VND</strong>
      <svg viewBox="0 0 220 48" fill="none"><path d="M1 39 20 34 39 35 59 28 79 30 99 23 119 26 139 20 159 22 179 16 199 19 219 12" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" /></svg>
    </div>
    <div className="auth-art-qr" aria-hidden="true">
      <svg viewBox="-1 -1 31 31" fill="currentColor" shapeRendering="crispEdges">{qrCells}</svg>
      <span>Receive 500,000 VND</span>
    </div>
    <div className="auth-art-reminder" aria-hidden="true"><i />Electricity bill due Nov 3</div>
  </div>;
}
