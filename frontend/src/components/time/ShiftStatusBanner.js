import React from 'react';

function formatShiftTime(value) {
  if (!value) return '';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return '';
  return d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
}

export default function ShiftStatusBanner({
  currentShift,
  nextShift,
  isLate,
  isOnShift,
  missedShift,
  clockedIn,
  clockedInOutsideShift,
}) {
  let tone = 'bg-slate-100 border-slate-300 text-slate-800';
  let title = 'No shift scheduled';
  let subtitle = 'You have no shift scheduled today.';

  if (missedShift) {
    tone = 'bg-red-100 border-red-300 text-red-900';
    title = '❌ Missed shift — submit explanation';
    subtitle = `Scheduled shift was ${formatShiftTime(missedShift.start_time)}–${formatShiftTime(missedShift.end_time)}.`;
  } else if (clockedIn && isOnShift) {
    tone = 'bg-blue-100 border-blue-300 text-blue-900';
    title = '🔵 On Shift';
    subtitle = `Current shift ends at ${formatShiftTime(currentShift?.end_time)}.`;
  } else if (currentShift && !clockedIn && isLate) {
    tone = 'bg-red-100 border-red-300 text-red-900';
    title = '🔴 You are late';
    subtitle = `Your shift started at ${formatShiftTime(currentShift?.start_time)}.`;
  } else if (currentShift && !clockedIn) {
    tone = 'bg-green-100 border-green-300 text-green-900';
    title = '🟢 Start Shift';
    subtitle = `Scheduled now until ${formatShiftTime(currentShift?.end_time)}.`;
  } else if (nextShift) {
    tone = 'bg-amber-100 border-amber-300 text-amber-900';
    title = '⏳ Shift starts soon';
    subtitle = `Next shift starts at ${formatShiftTime(nextShift.start_time)}.`;
  }

  return (
    <div className={`mb-4 rounded-lg border px-4 py-3 ${tone}`}>
      <div className="text-sm font-semibold">{title}</div>
      <div className="mt-1 text-sm">{subtitle}</div>
      {clockedInOutsideShift ? (
        <div className="mt-2 text-sm font-medium">
          Warning: You are clocked in outside a scheduled shift.
        </div>
      ) : null}
    </div>
  );
}
