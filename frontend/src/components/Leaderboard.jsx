import React from 'react'

const cellStyle = { padding: '8px 16px', textAlign: 'center', borderBottom: '1px solid #333' }
const headerStyle = { ...cellStyle, fontWeight: 'bold', borderBottom: '2px solid #555', color: '#ffd700' }

export default function Leaderboard({ standings }) {
  if (!standings || standings.length === 0) {
    return <div style={{ opacity: 0.5 }}>No standings yet</div>
  }

  return (
    <div>
      <h2 style={{ marginBottom: '12px', fontSize: '18px' }}>🏆 Standings</h2>
      <table style={{ borderCollapse: 'collapse', width: '100%' }}>
        <thead>
          <tr>
            <th style={headerStyle}>#</th>
            <th style={{ ...headerStyle, textAlign: 'left' }}>Player</th>
            <th style={headerStyle}>W</th>
            <th style={headerStyle}>D</th>
            <th style={headerStyle}>L</th>
            <th style={headerStyle}>Pts</th>
            <th style={headerStyle}>💀</th>
          </tr>
        </thead>
        <tbody>
          {standings.map((s) => (
            <tr key={s.name}>
              <td style={cellStyle}>{s.rank}</td>
              <td style={{ ...cellStyle, textAlign: 'left' }}>{s.name}</td>
              <td style={cellStyle}>{s.wins}</td>
              <td style={cellStyle}>{s.draws}</td>
              <td style={cellStyle}>{s.losses}</td>
              <td style={{ ...cellStyle, fontWeight: 'bold', color: '#ffd700' }}>{s.points}</td>
              <td style={cellStyle}>{s.fallbacks}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div style={{ fontSize: '11px', opacity: 0.4, marginTop: '4px' }}>💀 = random fallback moves</div>
    </div>
  )
}
