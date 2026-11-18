export interface ReviewEvidence {
  title: string; frozen: boolean; risk_band: string; risk_label: string; new_recipient: boolean;
  warning: string; not_before: number; parameter_sources: Record<string, string>;
  source_labels: Record<string, string>; rule_ids: string[]; rule_explanations: string[];
}

export function ApprovalEvidence({ review }: { review?: ReviewEvidence }) {
  if (!review) return null;
  return <div className="service-stack" aria-label="Bank review checks">
    {review.warning && <p role="note" className="form-error">{review.warning}</p>}
    <p className="service-hint">Risk assessment: <strong>{review.risk_label}</strong>. Check every detail before approval.</p>
    {review.not_before > 0 && <p className="service-hint">Bank verification is available after {new Date(review.not_before * 1000).toLocaleString('en-GB', { timeZone: 'Asia/Ho_Chi_Minh' })} (Vietnam time).</p>}
    {Object.keys(review.source_labels).length > 0 && <dl className="detail-list">{Object.entries(review.source_labels).map(([field, source]) => <div key={field}><dt>{field.replaceAll('_', ' ')}</dt><dd>{source}</dd></div>)}</dl>}
    {review.rule_explanations.map((explanation, index) => <p className="service-hint" key={review.rule_ids[index] ?? index}>{explanation}</p>)}
  </div>;
}
