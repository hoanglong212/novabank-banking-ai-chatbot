import type { DemoUser } from '../../types';
import { Cards } from './Cards';
import { Bills } from './Bills';
import { Savings } from './Savings';
export function Products({ user, section }: { user: DemoUser; section: 'cards' | 'bills' | 'savings' }) {
  if (section === 'cards') return <Cards user={user} />;
  if (section === 'bills') return <Bills user={user} />;
  return <Savings user={user} />;
}