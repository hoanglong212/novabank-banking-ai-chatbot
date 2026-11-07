import type { Bank } from '../../types';

const fold = (value: string) => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/đ/gi, 'd').toLowerCase();
const compact = (value: string) => fold(value).replace(/[^a-z0-9]/g, '');

/** OCR produces suggestions only. Never substitute ambiguous letters with digits or infer a bank from an account. */
export function paymentImageText(text: string, banks: Bank[]) {
  const lines = text.split(/\r?\n/).map(line => line.trim()).filter(Boolean);
  const internal = text.toUpperCase().match(/\bACC-[A-Z0-9]+(?:-[A-Z0-9]+)+\b/g) ?? [];
  const labelled: string[] = [];
  const labels = /(?:so\s*tai\s*khoan|\bstk\b|account\s*(?:number|no\.?))\s*[:#.-]?\s*(.*)$/;
  for (const [index, line] of lines.entries()) {
    const match = fold(line).match(labels);
    if (!match) continue;
    const value = match[1].trim() || lines[index + 1] || '';
    // Validate the whole value: never truncate an OCR result like 1234567O89.
    if (!/^\d[\d .\t-]*\d$/.test(value)) continue;
    const digits = value.replace(/\D/g, '');
    if (digits.length >= 6 && digits.length <= 19) labelled.push(digits);
  }
  const standalone = lines.filter(line => /^\d[\d \t-]{4,28}\d$/.test(line)).map(line => line.replace(/\D/g, '')).filter(value => value.length >= 6 && value.length <= 19);
  const accounts = [...new Set([...internal, ...labelled])];
  const candidates = accounts.length ? accounts : [...new Set(standalone)];
  const matchedBanks = banks.filter(bank => lines.some(line => {
    const value = compact(line);
    return [bank.shortName, bank.name, bank.code].some(name => {
      const key = compact(name);
      return key.length >= 2 && (value === key || value === 'nganhang' + key || value === 'bank' + key);
    });
  }));
  const bankHint = lines.find(line => /^(ngan\s*hang|bank)\s*[:\-]/.test(fold(line)))?.replace(/^[^:\-]+[:\-]\s*/, '') ?? '';
  return { account: candidates.length === 1 ? candidates[0] : '', candidates,
    bank: matchedBanks.length === 1 ? (matchedBanks[0].shortName === 'NovaBank' ? 'NovaBank' : matchedBanks[0].bin) : '', bankHint };
}
