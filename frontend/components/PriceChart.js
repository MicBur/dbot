import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

export default function PriceChart({ data, dataKey = "close", currency = "USD" }) {
  if (!data || data.length === 0) {
    return <p className="text-gray-400">Keine Daten für den Chart verfügbar.</p>;
  }

  // Daten für Recharts vorbereiten (falls nötig, hier sind sie schon fast passend)
  // Recharts erwartet, dass die X-Achsen-Daten (hier 'date') direkt im Datenobjekt sind.
  // Und die Y-Achsen-Daten (hier 'close') ebenfalls.

  // Tooltip-Formatter für Währung
  const currencyFormatter = (value) => {
    return new Intl.NumberFormat('de-DE', { style: 'currency', currency: currency }).format(value);
  };

  return (
    <ResponsiveContainer width="100%" height={250}>
      <LineChart
        data={data}
        margin={{
          top: 5,
          right: 20, // Etwas Platz für Labels
          left: 10, // Etwas Platz für Y-Achsen-Labels
          bottom: 5,
        }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="#4A5568" /> {/* Dunkleres Grid für Dark Mode */}
        <XAxis dataKey="date" stroke="#A0AEC0" tick={{ fontSize: 10 }} />
        <YAxis stroke="#A0AEC0" tickFormatter={currencyFormatter} tick={{ fontSize: 10 }} domain={['auto', 'auto']} />
        <Tooltip
          formatter={(value) => currencyFormatter(value)}
          contentStyle={{ backgroundColor: '#2D3748', border: 'none', borderRadius: '0.5rem' }} // Dunkler Tooltip
          labelStyle={{ color: '#E2E8F0' }}
          itemStyle={{ color: '#90CDF4' }}
        />
        <Legend wrapperStyle={{ fontSize: '12px' }} />
        <Line type="monotone" dataKey={dataKey} stroke="#63B3ED" strokeWidth={2} dot={false} name="Schlusskurs" />
        {/* Weitere Linien (z.B. für 'open', 'high', 'low') könnten hier hinzugefügt werden */}
      </LineChart>
    </ResponsiveContainer>
  );
}