export function loanSchedule(principal: number, months: number, annualRate: number) {
  const rate = annualRate / 1200;
  const payment = Math.ceil(rate ? principal * rate / (1 - Math.pow(1 + rate, -months)) : principal / months);
  let remaining = principal;
  return Array.from({ length: months }, (_, i) => {
    const interest = Math.round(remaining * rate);
    const paid = i === months - 1 ? remaining + interest : Math.min(payment, remaining + interest);
    const principalPaid = paid - interest; remaining = Math.max(0, remaining - principalPaid);
    return { month: i + 1, payment: paid, interest, principal: principalPaid, remaining };
  });
}
