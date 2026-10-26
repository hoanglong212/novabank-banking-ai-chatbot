import { useState } from 'react';
import { Check, ChevronDown, Search } from 'lucide-react';

import type { Bank } from '../../types';
import { Sheet } from '../ui/Sheet';

interface BankPickerProps {
  banks: Bank[];
  value: string;
  onChange: (bin: string) => void;
}

// Searchable bank list with logos, as banking apps do for 70+ NAPAS members.
export function BankPicker({ banks, value, onChange }: BankPickerProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const selected = banks.find(b => b.bin === value);
  const q = query.trim().toLowerCase();
  const matches = banks.filter(b => !q || [b.shortName, b.code, b.name].some(x => x?.toLowerCase().includes(q)));

  return (
    <>
      <button type="button" className="bank-trigger" onClick={() => setOpen(true)} disabled={!banks.length} aria-haspopup="dialog">
        {selected ? <img src={selected.logo} alt="" /> : <span className="bank-logo-empty" />}
        <span className="bank-names">
          <strong>{selected?.shortName ?? 'Loading banks…'}</strong>
          {selected && <small>{selected.name}</small>}
        </span>
        <ChevronDown size={18} aria-hidden="true" />
      </button>
      <Sheet open={open} onClose={() => setOpen(false)} title="Choose a bank">
        <label className="search-box">
          <Search size={18} aria-hidden="true" />
          <input autoFocus placeholder="Search by name or code" value={query} onChange={e => setQuery(e.target.value)} aria-label="Search banks" />
        </label>
        <ul className="bank-list">
          {matches.map(b => (
            <li key={b.bin}>
              <button type="button" className={b.bin === value ? 'is-selected' : ''} onClick={() => { onChange(b.bin); setOpen(false); setQuery(''); }}>
                <img src={b.logo} alt="" loading="lazy" />
                <span className="bank-names"><strong>{b.shortName}</strong><small>{b.name}</small></span>
                {b.bin === value && <Check size={18} aria-hidden="true" />}
              </button>
            </li>
          ))}
          {matches.length === 0 && <li className="muted">No bank matches “{query}”.</li>}
        </ul>
      </Sheet>
    </>
  );
}
