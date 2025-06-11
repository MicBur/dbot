import { useState, useEffect } from 'react';
import Clock from '../components/Clock';
import PriceChart from '../components/PriceChart'; // Neu importieren

export default function HomePage() {
  const [botStatus, setBotStatus] = useState(null);
  const [loadingBotStatus, setLoadingBotStatus] = useState(true);
  const [errorBotStatus, setErrorBotStatus] = useState(null);

  const [alpacaAccount, setAlpacaAccount] = useState(null);
  const [loadingAlpaca, setLoadingAlpaca] = useState(true);
  const [errorAlpaca, setErrorAlpaca] = useState(null);

  const [alpacaPositions, setAlpacaPositions] = useState([]);
  const [loadingPositions, setLoadingPositions] = useState(true);
  const [errorPositions, setErrorPositions] = useState(null);

  const [alpacaOrders, setAlpacaOrders] = useState([]);
  const [loadingOrders, setLoadingOrders] = useState(true);
  const [errorOrders, setErrorOrders] = useState(null);

  const [historicalData, setHistoricalData] = useState([]);
  const [loadingHistorical, setLoadingHistorical] = useState(true);
  const [errorHistorical, setErrorHistorical] = useState(null);
  const [selectedSymbolForChart, setSelectedSymbolForChart] = useState('AAPL'); // Beispielsymbol

  const backendBaseUrl = process.env.NEXT_PUBLIC_BACKEND_BASE_URL || 'http://localhost:8000';

  useEffect(() => {
    async function fetchBotStatus() {
      try {
        const response = await fetch(`${backendBaseUrl}/api/v1/bot-status`);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        setBotStatus(data);
      } catch (e) {
        setErrorBotStatus(e.message);
      } finally {
        setLoadingBotStatus(false);
      }
    }

    async function fetchAlpacaAccount() {
      try {
        const response = await fetch(`${backendBaseUrl}/api/v1/alpaca/account`);
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(`HTTP error! status: ${response.status} - ${errorData.detail || response.statusText}`);
        }
        const data = await response.json();
        setAlpacaAccount(data);
      } catch (e) {
        setErrorAlpaca(e.message);
      } finally {
        setLoadingAlpaca(false);
      }
    }

    async function fetchAlpacaPositions() {
      try {
        const response = await fetch(`${backendBaseUrl}/api/v1/alpaca/positions`);
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(`HTTP error! status: ${response.status} - ${errorData.detail || response.statusText}`);
        }
        const data = await response.json();
        setAlpacaPositions(data);
      } catch (e) {
        setErrorPositions(e.message);
      } finally {
        setLoadingPositions(false);
      }
    }

    async function fetchAlpacaOrders() {
      try {
        const response = await fetch(`${backendBaseUrl}/api/v1/alpaca/orders?status=filled&limit=10`); // Lade die letzten 10 gefüllten Orders
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(`HTTP error! status: ${response.status} - ${errorData.detail || response.statusText}`);
        }
        const data = await response.json();
        setAlpacaOrders(data);
      } catch (e) {
        setErrorOrders(e.message);
      } finally {
        setLoadingOrders(false);
      }
    }

    async function fetchHistoricalData(symbol) {
      if (!symbol) return;
      setLoadingHistorical(true);
      setErrorHistorical(null);
      try {
        // Optional: from/to Parameter hinzufügen, z.B. &from_date=YYYY-MM-DD&to_date=YYYY-MM-DD
        const response = await fetch(`${backendBaseUrl}/api/v1/fmp/historical-price/${symbol}`);
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(`HTTP error! status: ${response.status} - ${errorData.detail || response.statusText}`);
        }
        const data = await response.json();
        setHistoricalData(data.slice(0, 30)); // Zeige z.B. die letzten 30 Datenpunkte
      } catch (e) {
        setErrorHistorical(e.message);
      } finally {
        setLoadingHistorical(false);
      }
    }

    fetchBotStatus();
    fetchAlpacaAccount();
    fetchAlpacaPositions();
    fetchAlpacaOrders();
    fetchHistoricalData(selectedSymbolForChart); // Lade Daten für das initial ausgewählte Symbol
  }, [selectedSymbolForChart]); // Führe erneut aus, wenn selectedSymbolForChart sich ändert

  const handleStartBot = async () => {
    try {
      // Sende das aktuell ausgewählte Symbol mit
      const response = await fetch(`${backendBaseUrl}/api/v1/bot/start?symbol=${selectedSymbolForChart}`, { 
        method: 'POST' 
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(`HTTP error! status: ${response.status} - ${errorData.detail || response.statusText}`);
      }
      const data = await response.json();
      alert(data.message); // Einfache Benachrichtigung
      // Bot-Status neu laden, um die Änderung anzuzeigen
      setLoadingBotStatus(true);
      // Um den Status sofort zu aktualisieren, könnten wir den State direkt setzen
      // oder warten, bis fetchBotStatus die neuen Daten holt.
      // Für eine bessere UX wäre es gut, den Status direkt optimistischer zu aktualisieren.
      fetchBotStatus(); 
    } catch (e) {
      alert(`Fehler beim Starten des Bots: ${e.message}`);
    }
  };

  const handleStopBot = async () => {
    try {
      const response = await fetch(`${backendBaseUrl}/api/v1/bot/stop`, { method: 'POST' });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(`HTTP error! status: ${response.status} - ${errorData.detail || response.statusText}`);
      }
      const data = await response.json();
      alert(data.message); // Einfache Benachrichtigung
      setLoadingBotStatus(true);
      fetchBotStatus(); // Bot-Status neu laden
    } catch (e) {
      alert(`Fehler beim Stoppen des Bots: ${e.message}`);
    }
  };

  // Frühes Return, wenn noch Daten geladen werden
  if (loadingBotStatus || loadingAlpaca || loadingPositions || loadingOrders /* || loadingHistorical - Ladezustand wird pro Karte behandelt */) {
    return (
      <main className="min-h-screen flex flex-col items-center justify-center p-4">
        <p className="text-xl">Lade Dashboard Daten...</p>
      </main>
    );
  }

  // Fehlerbehandlung (optional hier zusammenfassen oder pro Sektion beibehalten)
  // Für dieses Beispiel belassen wir die Fehlerbehandlung pro Sektion,
  // aber eine globale Fehleranzeige wäre auch eine Option.

  return (
    <main className="min-h-screen flex flex-col p-4">
      <header className="w-full flex justify-between items-center mb-8">
        <h1 className="text-4xl font-bold">Trading Bot</h1>
        <Clock />
      </header>

      <section className="mb-8 p-6 bg-gray-800 rounded-lg shadow-lg">
        <h2 className="text-xl font-semibold mb-2">Bot Status</h2>
        {loadingBotStatus && <p>Lade Bot-Status...</p>}
        {errorBotStatus && <p className="text-red-400">Fehler beim Laden des Status: {errorBotStatus}</p>}
        {!loadingBotStatus && botStatus && (
          <div>
            <p>Status: <span className={`font-semibold ${botStatus.status === 'aktiv' ? 'text-green-400' : 'text-yellow-400'}`}>{botStatus.status}</span></p>
            <p>Nachricht: {botStatus.message}</p>
            <div className="mt-4 space-x-2">
              <button
                onClick={handleStartBot}
                disabled={botStatus.status === 'aktiv'}
                className="bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-4 rounded disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Bot Starten
              </button>
              <button
                onClick={handleStopBot}
                disabled={botStatus.status !== 'aktiv'}
                className="bg-red-600 hover:bg-red-700 text-white font-bold py-2 px-4 rounded disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Bot Stoppen
              </button>
            </div>
          </div>
        )}
      </section>

      {/* Alpaca Kontoinformationen anzeigen */}
      <section className="mb-8 p-6 bg-gray-800 rounded-lg shadow-lg">
        <h2 className="text-xl font-semibold mb-2">Alpaca Konto</h2>
        {loadingAlpaca && <p>Lade Alpaca Kontoinformationen...</p>}
        {errorAlpaca && <p className="text-red-400">Fehler: {errorAlpaca}</p>}
        {alpacaAccount && (
          <div className="grid grid-cols-2 gap-x-4 gap-y-2">
            <p>Kontostatus:</p><p className="font-semibold text-blue-400">{alpacaAccount.status}</p>
            <p>Portfolio Wert:</p><p className="font-semibold">{parseFloat(alpacaAccount.portfolio_value).toLocaleString('de-DE', { style: 'currency', currency: alpacaAccount.currency })}</p>
            <p>Bargeld:</p><p className="font-semibold">{parseFloat(alpacaAccount.cash).toLocaleString('de-DE', { style: 'currency', currency: alpacaAccount.currency })}</p>
            <p>Eigenkapital:</p><p className="font-semibold">{parseFloat(alpacaAccount.equity).toLocaleString('de-DE', { style: 'currency', currency: alpacaAccount.currency })}</p>
          </div>
        )}
      </section>

      <section className="flex-grow grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* Platzhalter-Karte 1: Marktdaten / Chart */}
        <div className="bg-gray-800 p-6 rounded-lg shadow-lg">
          <h2 className="text-xl font-semibold mb-4">Marktdaten</h2>
          {/* Einfache Symbolauswahl (kann später verbessert werden) */}
          <div className="mb-4">
            <label htmlFor="symbolSelect" className="mr-2">Symbol:</label>
            <select 
              id="symbolSelect" 
              value={selectedSymbolForChart} 
              onChange={(e) => setSelectedSymbolForChart(e.target.value)}
              className="bg-gray-700 border border-gray-600 rounded px-2 py-1"
            >
              <option value="AAPL">AAPL</option>
              <option value="MSFT">MSFT</option>
              <option value="GOOGL">GOOGL</option>
              <option value="NVDA">NVDA</option>
              {/* Füge hier weitere Symbole hinzu oder lade sie dynamisch */}
            </select>
          </div>
          {loadingHistorical && <p>Lade historische Daten...</p>}
          {errorHistorical && <p className="text-red-400">Fehler: {errorHistorical}</p>}
          {!loadingHistorical && !errorHistorical && historicalData.length === 0 && (
            <p className="text-gray-400">Keine historischen Daten für {selectedSymbolForChart} gefunden.</p>
          )}
          {historicalData.length > 0 && (
            <div className="h-64 bg-gray-700 rounded p-2 text-xs overflow-y-auto">
              {historicalData.map(item => (
                <div key={item.date} className="grid grid-cols-2 gap-x-2">
                  <span>{item.date}:</span>
                  <span className="text-right">{parseFloat(item.close).toLocaleString('de-DE', { style: 'currency', currency: 'USD' })}</span>
                </div>
              ))}
            </div>
          )}
        </div> {/* Dieses schließende div hat gefehlt */}

        {/* Platzhalter-Karte 2: Aktuelle Positionen */}
        <div className="bg-gray-800 p-6 rounded-lg shadow-lg">
          <h2 className="text-xl font-semibold mb-4">Aktuelle Positionen</h2>
          {loadingPositions && <p>Lade Positionen...</p>}
          {errorPositions && <p className="text-red-400">Fehler: {errorPositions}</p>}
          {!loadingPositions && !errorPositions && alpacaPositions.length === 0 && (
            <p className="text-gray-400">Keine offenen Positionen.</p>
          )}
          {alpacaPositions.length > 0 && (
            <div className="space-y-3 max-h-64 overflow-y-auto">
              {alpacaPositions.map((pos) => (
                <div key={pos.symbol} className="p-3 bg-gray-700 rounded">
                  <div className="flex justify-between items-center">
                    <span className="font-bold text-lg">{pos.symbol}</span>
                    <span className={`px-2 py-0.5 rounded text-xs font-semibold ${pos.side === 'long' ? 'bg-green-700 text-green-100' : 'bg-red-700 text-red-100'}`}>
                      {pos.side.toUpperCase()}
                    </span>
                  </div>
                  <div className="text-sm text-gray-300 mt-1">
                    <p>Menge: {parseFloat(pos.qty).toLocaleString('de-DE')}</p>
                    <p>Ø Einstieg: {parseFloat(pos.avg_entry_price).toLocaleString('de-DE', { style: 'currency', currency: alpacaAccount?.currency || 'USD' })}</p>
                    <p>Akt. Preis: {parseFloat(pos.current_price).toLocaleString('de-DE', { style: 'currency', currency: alpacaAccount?.currency || 'USD' })}</p>
                    <p>Marktwert: {parseFloat(pos.market_value).toLocaleString('de-DE', { style: 'currency', currency: alpacaAccount?.currency || 'USD' })}</p>
                    <p>Unreal. G/V: <span className={parseFloat(pos.unrealized_pl) >= 0 ? 'text-green-400' : 'text-red-400'}>{parseFloat(pos.unrealized_pl).toLocaleString('de-DE', { style: 'currency', currency: alpacaAccount?.currency || 'USD' })} ({parseFloat(pos.unrealized_plpc) * 100}%)</span></p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Platzhalter-Karte 3: Handelsverlauf / Logs */}
        <div className="bg-gray-800 p-6 rounded-lg shadow-lg">
          <h2 className="text-xl font-semibold mb-4">Handelsverlauf / Logs</h2>
          {loadingOrders && <p>Lade Handelsverlauf...</p>}
          {errorOrders && <p className="text-red-400">Fehler: {errorOrders}</p>}
          {!loadingOrders && !errorOrders && alpacaOrders.length === 0 && (
            <p className="text-gray-400">Kein Handelsverlauf gefunden.</p>
          )}
          {alpacaOrders.length > 0 && (
            <div className="space-y-2 max-h-64 overflow-y-auto text-xs">
              {alpacaOrders.map((order) => (
                <div key={order.id} className="p-2 bg-gray-700 rounded">
                  <div className="flex justify-between items-center font-semibold">
                    <span>{order.symbol}</span>
                    <span className={order.side === 'buy' ? 'text-green-400' : 'text-red-400'}>
                      {order.side.toUpperCase()} {parseFloat(order.filled_qty).toLocaleString('de-DE')}
                    </span>
                  </div>
                  <div className="text-gray-400">
                    <span>Typ: {order.type} | Status: {order.status}</span>
                  </div>
                  <div className="text-gray-400">
                    <span>Ø Preis: {order.filled_avg_price ? parseFloat(order.filled_avg_price).toLocaleString('de-DE', { style: 'currency', currency: alpacaAccount?.currency || 'USD' }) : 'N/A'}</span>
                  </div>
                  <div className="text-gray-500 text-right">{new Date(order.filled_at).toLocaleString('de-DE')}</div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Weitere Karten können hier hinzugefügt werden */}
      </section>
    </main>
  );
}