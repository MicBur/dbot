from fastapi import FastAPI, HTTPException, Query
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

app = FastAPI(
    title="yFinance Data Service",
    description="Provides historical stock data using yfinance.",
    version="0.1.0"
)

@app.get("/")
async def read_root_yfinance():
    return {"message": "yFinance Data Service is running."}

@app.get("/history/{symbol}")
async def get_historical_data(
    symbol: str,
    period: str = Query("5y", description="Period for historical data (e.g., 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)"),
    interval: str = Query("1d", description="Data interval (e.g., 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)")
):
    try:
        ticker = yf.Ticker(symbol.upper())
        # yfinance gibt einen Pandas DataFrame zurück
        hist_df = ticker.history(period=period, interval=interval)

        if hist_df.empty:
            raise HTTPException(status_code=404, detail=f"No historical data found for symbol {symbol} with period {period} and interval {interval}.")

        # Konvertiere den DataFrame in ein JSON-freundliches Format (Liste von Dictionaries)
        # Stelle sicher, dass der Index (Datum) eine Spalte wird und als String formatiert ist
        hist_df.reset_index(inplace=True)
        
        # Konvertiere Timestamp-Spalten in ISO-Format Strings
        for col in hist_df.columns:
            if pd.api.types.is_datetime64_any_dtype(hist_df[col]):
                # Für Datetime-Spalten (wie der Index, der jetzt eine Spalte ist)
                hist_df[col] = hist_df[col].dt.strftime('%Y-%m-%dT%H:%M:%S%z') # ISO 8601 mit Zeitzone
            elif pd.api.types.is_timedelta64_dtype(hist_df[col]):
                 hist_df[col] = hist_df[col].astype(str) # Timedeltas als Strings

        # Ersetze NaN/NaT durch None für JSON-Kompatibilität
        hist_df = hist_df.where(pd.notnull(hist_df), None)
        
        data_list = hist_df.to_dict(orient="records")
        
        return {
            "symbol": symbol.upper(),
            "period": period,
            "interval": interval,
            "data_count": len(data_list),
            "data": data_list
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching data for {symbol} from yfinance: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

