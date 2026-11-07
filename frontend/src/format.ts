function formatCents(amount: number): string {
  const sign = amount < 0 ? '-' : '';
  const whole = Math.floor(Math.abs(amount) / 100);
  const cents = String(Math.abs(amount) % 100).padStart(2, '0');
  return `${sign}S$${whole.toLocaleString('en-SG')}.${cents}`;
}

export { formatCents };