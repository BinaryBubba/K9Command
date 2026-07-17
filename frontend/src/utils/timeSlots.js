// Shared time-slot options for booking check-in/check-out pickers.
// Matches the pattern used for Meet & Greet scheduling: fixed windows
// in 15-minute increments, rather than a free-form time-of-day picker.
export const BOOKING_TIME_WINDOWS = [
  { start: 8, end: 10 },
  { start: 12, end: 14 },
  { start: 16, end: 18 },
];

export const BOOKING_TIME_SLOTS = (() => {
  const slots = [];
  for (const { start, end } of BOOKING_TIME_WINDOWS) {
    for (let mins = start * 60; mins <= end * 60; mins += 15) {
      const h = Math.floor(mins / 60);
      const m = mins % 60;
      const value = `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
      const period = h >= 12 ? 'PM' : 'AM';
      const h12 = h % 12 === 0 ? 12 : h % 12;
      const label = `${h12}:${String(m).padStart(2, '0')} ${period}`;
      slots.push({ value, label });
    }
  }
  return slots;
})();
