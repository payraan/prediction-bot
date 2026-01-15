/**
 * انتخاب مقدار شرط
 */

export default function AmountSelector({ value, onChange, balance }) {
  const presets = [1, 5, 10, 25, 50]

  return (
    <div className="amount-selector">
      <div className="amount-label">
        <span>مقدار شرط</span>
        <span className="balance-hint">موجودی: {balance?.toFixed(2) || 0} TON</span>
      </div>
      
      <div className="amount-presets">
        {presets.map(amount => (
          <button
            key={amount}
            className={`preset-btn ${value === amount ? 'selected' : ''}`}
            onClick={() => onChange(amount)}
            disabled={balance < amount}
          >
            {amount}
          </button>
        ))}
      </div>

      <div className="amount-input-wrap">
        <input
          type="number"
          value={value}
          onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
          min="1"
          max={balance || 1000}
          step="0.1"
        />
        <span className="currency">TON</span>
      </div>
    </div>
  )
}
