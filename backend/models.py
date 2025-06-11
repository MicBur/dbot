from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func # für server_default=func.now()
from database import Base # Geändert

# Hier könnten später andere Modelle für den Trading-Bot definiert werden,
# z.B. für Trades, Konfigurationen, etc.
# Vorerst ist diese Datei leer, da wir das User-Modell entfernen.

class StockPrice(Base):
    __tablename__ = "stock_prices"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime(timezone=True), index=True, nullable=False) # Oder Date, wenn nur Tagesdaten
    open = Column(Float, nullable=True)
    high = Column(Float, nullable=True)
    low = Column(Float, nullable=True)
    close = Column(Float, nullable=False)
    adj_close = Column(Float, nullable=True)
    volume = Column(Float, nullable=True) # Float, da Volumen sehr groß sein kann
    source = Column(String, nullable=True, default="FMP") # Quelle der Daten, z.B. FMP

class StockSentiment(Base):
    __tablename__ = "stock_sentiments"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False)
    date = Column(Date, index=True, nullable=False) # Sentiment ist oft tagesbasiert
    sentiment_score = Column(Float, nullable=False) # z.B. -1 bis 1
    source = Column(String, nullable=True, default="GeminiNews") # Quelle, z.B. Gemini, NewsAPI
    fetched_at = Column(DateTime(timezone=True), server_default=func.now())