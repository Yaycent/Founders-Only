import { useMemo } from 'react';

function parseMoney(value) {
  const match = String(value || '').replace(/,/g, '').match(/\$?\s*(\d+(?:\.\d+)?)\s*([kmb])?/i);
  if (!match) return 0;
  const multiplier = { k: 1e3, m: 1e6, b: 1e9 }[(match[2] || '').toLowerCase()] || 1;
  return Number(match[1]) * multiplier;
}

export function noteCount(netWorth) {
  const amount = parseMoney(netWorth);
  if (!amount) return 5;
  return Math.min(24, Math.max(4, 4 + Math.round(3 * Math.log10(Math.max(amount, 1) / 1e6))));
}

export default function MoneyRain({ netWorth }) {
  const notes = useMemo(() => {
    const count = noteCount(netWorth);
    return Array.from({ length: count }, (_, index) => {
      const duration = 3.5 + Math.random() * 2.5;
      return {
        id: `${index}-${Math.round(Math.random() * 1e8)}`,
        left: `${Math.random() * 96}%`,
        duration: `${duration.toFixed(1)}s`,
        delay: `${(-Math.random() * duration).toFixed(1)}s`,
        drift: `${Math.round(Math.random() * 100 - 50)}px`,
        tilt: `${Math.round(Math.random() * 36 - 18)}deg`,
        spin: `${Math.round(160 + Math.random() * 250)}deg`,
      };
    });
  }, [netWorth]);

  return (
    <div className="money-rain" aria-hidden="true">
      {notes.map((note, index) => (
        <span
          className="money-note"
          key={note.id}
          style={{
            left: note.left,
            '--duration': note.duration,
            '--delay': note.delay,
            '--drift': note.drift,
            '--tilt': note.tilt,
            '--spin': note.spin,
            zIndex: index % 3,
          }}
        >
          <img src="/assets/canada-100-note.png" alt="" />
        </span>
      ))}
    </div>
  );
}
