function formatDate(value) {
  if (!value) return '-'
  try {
    return new Date(value).toLocaleString('tr-TR')
  } catch {
    return value
  }
}

// columns: [{ key, label, render? }]
export default function HistoryTable({ columns, rows, emptyText = 'Kayıt yok' }) {
  if (!rows || rows.length === 0) {
    return <p className="muted">{emptyText}</p>
  }

  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            {columns.map((col) => (
              <th key={col.key}>{col.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>
              {columns.map((col) => (
                <td key={col.key}>
                  {col.render ? col.render(row) : (row[col.key] ?? '-')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export { formatDate }
