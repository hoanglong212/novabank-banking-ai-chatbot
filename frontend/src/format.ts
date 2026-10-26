export const vnd = (amount: number) => `${amount.toLocaleString('en-US')} VND`;

export function initials(name: string) {
  return name.trim().split(/\s+/).slice(-2).map(x => x[0]).join('').toUpperCase();
}

export function greeting(date = new Date()) {
  const hour = date.getHours();
  return hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening';
}
