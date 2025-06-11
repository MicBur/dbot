from sqlalchemy.orm import Session
import models, schemas # Diese Imports bleiben vorerst, falls du später andere CRUDs hinzufügst
from datetime import date, datetime, timedelta

# Hier könnten später andere CRUD-Operationen für den Trading-Bot definiert werden.
# Vorerst ist diese Datei leer, da wir die User-CRUDs entfernen.

def create_stock_price(db: Session, price: schemas.StockPriceCreate):
    db_price = models.StockPrice(**price.model_dump())
    db.add(db_price)
    db.commit()
    db.refresh(db_price)
    return db_price

def get_stock_prices(db: Session, symbol: str, start_date: datetime, end_date: datetime, limit: int = 1000):
    return db.query(models.StockPrice)\
             .filter(models.StockPrice.symbol == symbol.upper())\
             .filter(models.StockPrice.timestamp >= start_date)\
             .filter(models.StockPrice.timestamp <= end_date)\
             .order_by(models.StockPrice.timestamp.asc())\
             .limit(limit)\
             .all()

def get_latest_stock_prices_for_sequence(db: Session, symbol: str, sequence_length: int):
    """Holt die letzten 'sequence_length' Schlusskurse für ein Symbol."""
    return db.query(models.StockPrice.timestamp, models.StockPrice.close)\
             .filter(models.StockPrice.symbol == symbol.upper())\
             .order_by(models.StockPrice.timestamp.desc())\
             .limit(sequence_length)\
             .all() # Gibt eine Liste von Tupeln (timestamp, close) zurück, neueste zuerst

def create_stock_sentiment(db: Session, sentiment: schemas.StockSentimentCreate):
    db_sentiment = models.StockSentiment(**sentiment.model_dump())
    db.add(db_sentiment)
    db.commit()
    db.refresh(db_sentiment)
    return db_sentiment

def get_stock_sentiments(db: Session, symbol: str, start_date: date, end_date: date, limit: int = 100):
    return db.query(models.StockSentiment)\
             .filter(models.StockSentiment.symbol == symbol.upper())\
             .filter(models.StockSentiment.date >= start_date)\
             .filter(models.StockSentiment.date <= end_date)\
             .order_by(models.StockSentiment.date.asc())\
             .limit(limit)\
             .all()

def get_latest_sentiments_for_sequence(db: Session, symbol: str, sequence_length: int):
    """Holt die letzten 'sequence_length' Sentiment-Scores für ein Symbol."""
    return db.query(models.StockSentiment.date, models.StockSentiment.sentiment_score)\
             .filter(models.StockSentiment.symbol == symbol.upper())\
             .order_by(models.StockSentiment.date.desc())\
             .limit(sequence_length)\
             .all() # Gibt eine Liste von Tupeln (date, sentiment_score) zurück, neueste zuerst