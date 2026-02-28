import React, { useRef, useEffect } from 'react'

export default function MoveList({ moves }) {
  const endRef = useRef(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [moves])

  if (!moves || moves.length === 0) {
    return <div style={{ opacity: 0.5, fontSize: '14px' }}>Waiting for moves...</div>
  }

  // Pair moves into rows (white, black)
  const rows = []
  for (let i = 0; i < moves.length; i += 2) {
    rows.push({
      num: Math.floor(i / 2) + 1,
      white: moves[i],
      black: moves[i + 1] || null,
    })
  }

  return (
    <div>
      <h2 style={{ marginBottom: '8px', fontSize: '18px' }}>📜 Moves</h2>
      <div style={{
        maxHeight: '360px',
        overflowY: 'auto',
        fontFamily: 'monospace',
        fontSize: '13px',
        lineHeight: '1.8',
      }}>
        {rows.map((r) => (
          <div key={r.num} style={{ display: 'flex', gap: '8px' }}>
            <span style={{ width: '30px', opacity: 0.4, textAlign: 'right' }}>{r.num}.</span>
            <span style={{
              width: '70px',
              color: r.white?.fallback ? '#ff6b6b' : '#e0e0e0',
            }}>
              {r.white?.san}{r.white?.fallback ? ' 💀' : ''}
            </span>
            {r.black && (
              <span style={{
                width: '70px',
                color: r.black?.fallback ? '#ff6b6b' : '#e0e0e0',
              }}>
                {r.black?.san}{r.black?.fallback ? ' 💀' : ''}
              </span>
            )}
          </div>
        ))}
        <div ref={endRef} />
      </div>
    </div>
  )
}
