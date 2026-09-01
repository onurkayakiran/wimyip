import i18n from '../i18n'

function formatDate(value) {
  if (!value) return '-'
  try {
    // i18n.language kullanicinin secili diline gore tarih formatliyor
    // (orn. en-US vs tr-TR vs de-DE farkli gun/ay sirasi kullanir).
    return new Date(value).toLocaleString(i18n.language)
  } catch {
    return value
  }
}

// columns: [{ key, label, render? }]
export default function HistoryTable({ columns, rows, emptyText }) {
  if (!rows || rows.length === 0) {
    return <p className="muted">{emptyText ?? i18n.t('historyTable.no_rows')}</p>
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
