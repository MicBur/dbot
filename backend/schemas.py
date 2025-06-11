from pydantic import BaseModel
from datetime import datetime, date # Neu importieren

# Hier könnten später andere Schemas für den Trading-Bot definiert werden.
# Vorerst ist diese Datei leer, da wir die User- und Token-Schemas entfernen.
# Beispiel:
# class TradeBase(BaseModel):
#     symbol: str
#     qty: float # Geändert von quantity zu qty für Konsistenz mit Alpaca
#     avg_entry_price: float # Geändert von price zu avg_entry_price

class AlpacaPosition(BaseModel):
    symbol: str
    qty: str
    avg_entry_price: str
    current_price: str
    market_value: str
    unrealized_pl: str
    unrealized_plpc: str # Unrealized profit/loss percent (als String, z.B. "0.01" für 1%)
    side: str
    asset_class: str

    class Config:
        from_attributes = True

class AlpacaOrder(BaseModel):
    id: str
    client_order_id: str
    created_at: datetime
    updated_at: datetime | None = None
    submitted_at: datetime | None = None
    filled_at: datetime | None = None
    symbol: str
    qty: str | None = None # Kann bei Market Orders initial None sein
    filled_qty: str
    side: str
    type: str # z.B. market, limit
    status: str # z.B. filled
    filled_avg_price: str | None = None
    order_class: str | None = None
    legs: list | None = None # Für komplexere Orders

    class Config:
        from_attributes = True

class HistoricalPricePoint(BaseModel):
    date: str # Behalte es als String, da FMP es so liefert
    open: float
    high: float
    low: float
    close: float
    adjClose: float
    volume: float
    unadjustedVolume: float
    change: float
    changePercent: float
    vwap: float | None = None # Manchmal nicht vorhanden
    label: str
    changeOverTime: float

# --- Schemas für neue Modelle ---
class StockPriceBase(BaseModel):
    symbol: str
    timestamp: datetime
    close: float
    open: float | None = None
    high: float | None = None
    low: float | None = None
    adj_close: float | None = None
    volume: float | None = None
    source: str | None = "FMP"

class StockPriceCreate(StockPriceBase):
    pass

class StockPriceInDB(StockPriceBase):
    id: int
    class Config:
        from_attributes = True

class StockSentimentBase(BaseModel):
    symbol: str
    date: date
    sentiment_score: float
    source: str | None = "GeminiNews"
class StockSentimentCreate(StockSentimentBase):
    pass
class StockSentimentInDB(StockSentimentBase):
    id: int
    fetched_at: datetime
    class Config:
        from_attributes = True