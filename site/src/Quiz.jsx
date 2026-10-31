import { useState } from 'react';

/** items: [{ q, options: [...], answer: index, why }] */
export default function Quiz({ items, onDone }) {
  const [picked, setPicked] = useState({});
  const done = Object.keys(picked).length === items.length;
  const score = items.filter((it, i) => picked[i] === it.answer).length;
  return (
    <div className="quiz">
      {items.map((it, i) => (
        <fieldset key={i} className="q">
          <legend>{i + 1}. {it.q}</legend>
          {it.options.map((o, j) => {
            const chosen = picked[i] === j;
            const state = picked[i] === undefined ? '' : j === it.answer ? 'right' : chosen ? 'wrong' : 'dim';
            return (
              <button key={j} type="button" className={`opt ${state}`} disabled={picked[i] !== undefined}
                onClick={() => { const p = { ...picked, [i]: j }; setPicked(p); if (Object.keys(p).length === items.length && onDone) onDone(); }}>
                {o}
              </button>
            );
          })}
          {picked[i] !== undefined && it.why && <p className="why">{picked[i] === it.answer ? '✅ ' : '❌ '}{it.why}</p>}
        </fieldset>
      ))}
      {done && <p className="score">You got <b>{score} / {items.length}</b>{score === items.length ? ' — perfect! 🎉' : '.'}</p>}
    </div>
  );
}
