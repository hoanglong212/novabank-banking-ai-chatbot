export function Pagination({ offset, limit, total, busy, change }: {
  offset: number; limit: number; total: number; busy: boolean; change: (offset: number) => void;
}) {
  return <nav className="pagination" aria-label="Results pages">
    <span className="muted">{total === 0 ? 'No results' : `${offset + 1}–${Math.min(offset + limit, total)} of ${total}`}</span>
    <div>
      <button className="secondary-button" disabled={busy || offset === 0} onClick={() => change(Math.max(0, offset - limit))}>Previous</button>
      <button className="secondary-button" disabled={busy || offset + limit >= total} onClick={() => change(offset + limit)}>Next</button>
    </div>
  </nav>;
}
