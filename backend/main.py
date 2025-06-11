from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
import os
from fastapi.middleware.cors import CORSMiddleware # Neu
from dotenv import load_dotenv
from sqlalchemy.orm import Session
import alpaca_trade_api as tradeapi # Neu
import requests # Neu für FMP
import asyncio # Neu für die Bot-Schleife
import pandas as pd # Neu für gleitende Durchschnitte
from datetime import datetime, timedelta, date as py_date # Neu für Datumsmanipulation

import crud, models, schemas # Geändert
from database import SessionLocal, engine
# import security # Nicht mehr benötigt für Benutzer-Auth
from ml_utils import load_model_components_for_ticker, predict_for_ticker # NEU

# Lade Umgebungsvariablen aus .env (besonders nützlich für lokale Entwicklung außerhalb von Docker)
load_dotenv()

# models.Base.metadata.create_all(bind=engine) # Vorerst auskommentiert, da keine Tabellen mehr da sind

app = FastAPI()

# Alpaca API-Client Initialisierung
ALPACA_API_KEY_ID = os.getenv("ALPACA_API_KEY_ID")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
ALPACA_BASE_URL = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets") # Standard auf Paper Trading
FMP_API_KEY = os.getenv("FMP_API_KEY") # Neu

alpaca_api = None
if ALPACA_API_KEY_ID and ALPACA_SECRET_KEY:
    alpaca_api = tradeapi.REST(ALPACA_API_KEY_ID, ALPACA_SECRET_KEY, base_url=ALPACA_BASE_URL)
    print("Alpaca API Client erfolgreich initialisiert.")
else:
    print("WARNUNG: Alpaca API Keys nicht gefunden. Alpaca-Funktionalität ist nicht verfügbar.")

# Einfacher In-Memory-Status für den Bot
bot_is_running = False
bot_task = None # Hält die Referenz zur laufenden Bot-Aufgabe
current_monitoring_symbol = "AAPL" # Standard-Symbol, das der Bot überwacht

# CORS-Middleware hinzufügen
origins = [
    "http://localhost",      # Erlaube Anfragen von localhost (ohne Port)
    "http://localhost:3000", # Erlaube Anfragen von deinem Frontend-Entwicklungsserver
    "http://micbur1488.ddns.net:3000", # Deine DDNS-Adresse für das Frontend
    "http://micbur1488.ddns.net",      # Deine DDNS-Adresse HTTP ohne Port
    "https://micbur1488.ddns.net:3000", # Deine DDNS-Adresse HTTPS mit Port (falls du HTTPS auf 3000 hast)
    "https://micbur1488.ddns.net",      # Deine DDNS-Adresse HTTPS ohne Port
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Erlaube alle Methoden (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"], # Erlaube alle Header
)

# Dependency, um eine DB-Session pro Request zu erhalten
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
async def read_root():
    return {"message": "Hallo vom Trading-Bot Backend!"}

@app.get("/db_test")
async def test_db_connection(db: Session = Depends(get_db)):
    try:
        # Einfache Testabfrage, da die User-Tabelle nicht mehr existiert
        # result = db.execute(models.User.__table__.select().limit(0)) # Testet ob die Tabelle existiert
        version_result = db.execute("SELECT version()").scalar_one_or_none()
        return {"message": "Datenbankverbindung über SQLAlchemy erfolgreich.", "db_version": version_result}
    except Exception as e:
        return {"error": f"Datenbankfehler: {str(e)}"}

@app.get("/health")
async def health_check():
    # Hier könnte man auch den DB-Status prüfen
    return {"status": "ok"}

@app.get("/api/v1/bot-status")
async def get_bot_status():
    # Greife auf den globalen Status zu
    global bot_is_running
    status_text = "aktiv" if bot_is_running else "inaktiv"
    monitoring_info = f"Überwacht: {current_monitoring_symbol}" if bot_is_running else "Nicht aktiv."
    return {"status": status_text, "message": f"Trading Bot ist {status_text}. {monitoring_info}"}

@app.get("/api/v1/alpaca/account")
async def get_alpaca_account_info():
    if not alpaca_api:
        raise HTTPException(status_code=503, detail="Alpaca API Client nicht initialisiert (API Keys fehlen oder sind ungültig).")
    try:
        account_info = alpaca_api.get_account()
        # Wandle das Account-Objekt in ein Dictionary um, um es als JSON zurückzugeben
        # oder verwende Pydantic-Modelle für eine strukturiertere Antwort.
        return {
            "id": account_info.id,
            "account_number": account_info.account_number,
            "currency": account_info.currency,
            "cash": account_info.cash,
            "portfolio_value": account_info.portfolio_value,
            "equity": account_info.equity,
            "status": account_info.status,
        }
    except tradeapi.rest.APIError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Allgemeiner Fehler beim Abrufen der Alpaca Kontoinformationen: {str(e)}")

@app.get("/api/v1/alpaca/positions", response_model=list[schemas.AlpacaPosition])
async def get_alpaca_positions():
    if not alpaca_api:
        raise HTTPException(status_code=503, detail="Alpaca API Client nicht initialisiert.")
    try:
        positions_raw = alpaca_api.list_positions()
        # Konvertiere die rohen Position-Objekte in unser Pydantic-Modell
        # Die Alpaca-Bibliothek gibt Objekte zurück, deren Attribute direkt zugänglich sind.
        # Pydantic's from_attributes (oder orm_mode in v1) kann hier helfen.
        positions_response = [schemas.AlpacaPosition.from_orm(p) for p in positions_raw]
        return positions_response
    except tradeapi.rest.APIError as e:
        # Versuche, eine spezifischere Nachricht aus dem Fehlerobjekt zu extrahieren
        error_detail = str(e)
        if hasattr(e, '_error') and isinstance(e._error, dict) and 'message' in e._error:
            error_detail = e._error['message']
        raise HTTPException(status_code=e.status_code if hasattr(e, 'status_code') and e.status_code else 400, detail=error_detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Allgemeiner Fehler beim Abrufen der Alpaca Positionen: {str(e)}")

@app.get("/api/v1/alpaca/orders", response_model=list[schemas.AlpacaOrder])
async def get_alpaca_orders(status: str = 'filled', limit: int = 50, direction: str = 'desc'):
    if not alpaca_api:
        raise HTTPException(status_code=503, detail="Alpaca API Client nicht initialisiert.")
    try:
        # Parameter für list_orders: status, limit, after, until, direction, nested (True/False für legs)
        orders_raw = alpaca_api.list_orders(
            status=status,
            limit=limit,
            direction=direction
        )
        orders_response = [schemas.AlpacaOrder.from_orm(o) for o in orders_raw]
        return orders_response
    except tradeapi.rest.APIError as e:
        error_detail = str(e)
        if hasattr(e, '_error') and isinstance(e._error, dict) and 'message' in e._error:
            error_detail = e._error['message']
        raise HTTPException(status_code=e.status_code if hasattr(e, 'status_code') and e.status_code else 400, detail=error_detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Allgemeiner Fehler beim Abrufen der Alpaca Orders: {str(e)}")

@app.get("/api/v1/fmp/historical-price/{symbol}", response_model=list[schemas.HistoricalPricePoint])
async def get_fmp_historical_prices(symbol: str, from_date: str | None = None, to_date: str | None = None):
    if not FMP_API_KEY:
        raise HTTPException(status_code=503, detail="FMP API Key nicht konfiguriert.")
    
    # Standardmäßig die letzten 30 Tage, wenn keine Daten angegeben sind
    # FMP erwartet YYYY-MM-DD
    # Diese Logik kann bei Bedarf verfeinert werden
    # to_date_param = to_date if to_date else datetime.now().strftime('%Y-%m-%d')
    # from_date_param = from_date if from_date else (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

    # Für diesen Endpunkt verwenden wir den "full" Endpunkt, der viele Daten liefert.
    # Query-Parameter für from/to können hinzugefügt werden, wenn FMP sie für diesen spezifischen Endpunkt unterstützt.
    # Für /historical-price-full/{symbol} sind from/to nicht die primären Filter, oft wird eine Serie zurückgegeben.
    # Wir holen die Standardserie und filtern später, falls nötig, oder verwenden einen anderen FMP-Endpunkt.
    fmp_url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{symbol.upper()}?apikey={FMP_API_KEY}"
    
    try:
        response = requests.get(fmp_url)
        response.raise_for_status() # Wirft einen Fehler bei 4xx/5xx Statuscodes
        data = response.json()
        # FMP gibt oft ein Dictionary mit einem 'historical'-Schlüssel zurück, der eine Liste enthält
        historical_data = data.get("historical", [])
        # Validierung gegen Pydantic-Schema geschieht automatisch durch response_model
        return historical_data
    except requests.exceptions.HTTPError as e:
        # Versuche, eine spezifischere Fehlermeldung von FMP zu bekommen, falls vorhanden
        error_detail = f"FMP API Fehler: {e.response.status_code}"
        try:
            fmp_error = e.response.json()
            if "Error Message" in fmp_error:
                error_detail = fmp_error["Error Message"]
        except ValueError: # Falls die Antwort kein JSON ist
            error_detail = e.response.text[:200] # Zeige die ersten 200 Zeichen
        raise HTTPException(status_code=e.response.status_code, detail=error_detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Allgemeiner Fehler beim Abrufen der FMP-Daten für {symbol}: {str(e)}")

async def bot_loop():
    global bot_is_running
    global current_monitoring_symbol
    print(f"INFO: Bot-Schleife gestartet. Überwacht: {current_monitoring_symbol}")

    # Konfiguration für das Transformer-Modell (aus ml_utils oder einer config-Datei)
    # Diese Werte werden von der geladenen Modellkonfiguration überschrieben, dienen hier als Fallback/Info
    SEQ_LENGTH = SEQ_LENGTH_DEFAULT # aus ml_utils importieren oder hier definieren
    FORECAST_HORIZON = FORECAST_HORIZON_DEFAULT # aus ml_utils
    INPUT_DIM_MODEL = INPUT_DIM_MODEL_DEFAULT # aus ml_utils (Close + Sentiment)

    # Ziel-Ticker (könnte dynamisch aus DB oder Gemini-ähnlicher Quelle kommen)
    target_symbols = ["AAPL", "MSFT", "GOOGL", "NVDA", "AMZN"] # Beispielhafte Top 5 für den Anfang
    
    db_for_loop = SessionLocal() # Eigene DB-Session für die Schleife

    while bot_is_running:
        print(f"BOT-LOG: Starte neuen Strategie-Durchlauf für Symbole: {target_symbols}")
        active_buy_signals = [] # Format: [{'symbol': str, 'strength': float, 'price_for_qty_calc': float}]

        # --- PASS 1: Signal-Generierung und Stärke-Bewertung ---
        print(f"BOT-LOG: Pass 1 - Signal-Generierung für Symbole: {target_symbols}")
        for symbol_to_process in target_symbols:
            try:
                if not alpaca_api:
                    print(f"BOT-LOG [{symbol_to_process}]: Alpaca API nicht initialisiert. Überspringe.")
                    await asyncio.sleep(5) # Kurze Pause bevor nächstes Symbol
                    continue

                # Lade Modellkomponenten für den aktuellen Ticker
                model_components = load_model_components_for_ticker(symbol_to_process.upper())
                if not model_components:
                    print(f"BOT-LOG [{symbol_to_process}]: Keine Modellkomponenten gefunden. Überspringe.")
                    continue
                
                # Aktuelle Sequenzdaten (Close + Sentiment) aus der DB holen
                # Annahme: crud-Funktionen geben Daten in korrekter Reihenfolge (älteste zuerst)
                latest_prices_db = crud.get_latest_stock_prices_for_sequence(db_for_loop, symbol_to_process.upper(), SEQ_LENGTH)
                latest_sentiments_db = crud.get_latest_sentiments_for_sequence(db_for_loop, symbol_to_process.upper(), SEQ_LENGTH)

                # Daten aufbereiten (in DataFrame umwandeln, mergen, sicherstellen, dass SEQ_LENGTH Punkte vorhanden sind)
                if len(latest_prices_db) < SEQ_LENGTH or len(latest_sentiments_db) < SEQ_LENGTH:
                    print(f"BOT-LOG [{symbol_to_process}]: Nicht genügend Preis- ({len(latest_prices_db)}) oder Sentiment-Daten ({len(latest_sentiments_db)}) für Sequenzlänge {SEQ_LENGTH}. Überspringe.")
                    continue

                # Konvertiere zu DataFrames und merge sie basierend auf dem Datum
                # Die DB-Abfragen geben neueste zuerst zurück, also umkehren für chronologische Reihenfolge
                df_prices = pd.DataFrame(latest_prices_db, columns=['timestamp', 'Close']).iloc[::-1]
                df_sentiments = pd.DataFrame(latest_sentiments_db, columns=['date', 'Sentiment']).iloc[::-1]

                df_prices['date'] = pd.to_datetime(df_prices['timestamp']).dt.date
                df_sentiments['date'] = pd.to_datetime(df_sentiments['date']) # Ist schon ein Datum

                # Merge basierend auf dem Datum
                # Wir brauchen ein tägliches Sentiment, das zum Close-Preis passt.
                # Wenn Sentiment seltener ist, muss man entscheiden, wie man es zuordnet (z.B. ffill)
                merged_df = pd.merge(df_prices, df_sentiments, on='date', how='left')
                merged_df['Sentiment'] = merged_df['Sentiment'].fillna(0) # Fehlendes Sentiment als neutral (0)

                if len(merged_df) < SEQ_LENGTH:
                    print(f"BOT-LOG [{symbol_to_process}]: Nicht genügend gemergte Datenpunkte ({len(merged_df)}) für Sequenzlänge {SEQ_LENGTH}. Überspringe.")
                    continue
                
                # Nimm die letzten SEQ_LENGTH Datenpunkte für das Modell
                sequence_data_for_model_np = merged_df[['Close', 'Sentiment']].tail(SEQ_LENGTH).values.astype(np.float32)
                
                if sequence_data_for_model_np.shape[0] != SEQ_LENGTH or sequence_data_for_model_np.shape[1] != INPUT_DIM_MODEL:
                    print(f"BOT-LOG [{symbol_to_process}]: Falsche Form der Sequenzdaten ({sequence_data_for_model_np.shape}). Erwartet ({SEQ_LENGTH}, {INPUT_DIM_MODEL}). Überspringe.")
                    continue

                # Vorhersage treffen
                predicted_prices_actual = predict_for_ticker(model_components, sequence_data_for_model_np)

                if predicted_prices_actual is not None and len(predicted_prices_actual) > 0:
                    current_close_price = sequence_data_for_model_np[-1, 0] # Letzter bekannter Close-Preis
                    # Stärke basierend auf der Vorhersage für den ersten Tag des Horizonts
                    predicted_first_day_price = predicted_prices_actual[0]
                    
                    if current_close_price > 0:
                        strength = (predicted_first_day_price - current_close_price) / current_close_price
                        print(f"BOT-LOG [{symbol_to_process}]: Aktuell: {current_close_price:.2f}, Vorhersage Tag 1: {predicted_first_day_price:.2f}, Stärke: {strength:.4f}")

                        # Hier deine Logik für Kaufsignal basierend auf Stärke
                        model_buy_threshold = model_components['config'].get('prediction_threshold_buy_signal', 0.01) # Beispiel: 1% Anstieg
                        if strength > model_buy_threshold: # Stelle sicher, dass diese if-Anweisung korrekt eingerückt ist
                            print(f"BOT-SIGNAL [{symbol_to_process}]: KAUFSIGNAL (Modell) mit Stärke: {strength:.4f}") # 4 Leerzeichen mehr als das 'if'
                            active_buy_signals.append({ # Exakt gleiche Einrückung wie die print-Zeile darüber
                                'symbol': symbol_to_process,
                                'strength': strength, # Positive Stärke für Kauf
                                'price_for_qty_calc': current_close_price
                            }) # Stelle sicher, dass diese Einrückung mit der print-Zeile darüber übereinstimmt
                        elif strength < -model_components['config'].get('prediction_threshold_sell_signal', 0.01): # Beispiel für Verkauf
                            print(f"BOT-SIGNAL [{symbol_to_process}]: VERKAUFSSIGNAL (Modell) mit Stärke: {strength:.4f}")
                            # Hier könnte Verkaufslogik implementiert werden
                        else:
                            print(f"BOT-SIGNAL [{symbol_to_process}]: Kein starkes Handelssignal vom Modell (Stärke: {strength:.4f}).")
                    else:
                        print(f"BOT-LOG [{symbol_to_process}]: Aktueller Preis ist 0, kann Stärke nicht berechnen.")
                else:
                    print(f"BOT-LOG [{symbol_to_process}]: Keine Vorhersage vom Modell erhalten.")

            except Exception as e:
                print(f"FEHLER in Bot-Schleife (Pass 1) für Symbol {symbol_to_process}: {e}")
                import traceback
                traceback.print_exc()
            await asyncio.sleep(2) # Kurze Pause zwischen der Verarbeitung der Symbole in Pass 1

        # --- Kapitalallokation und Orderplatzierung (Pass 2) ---
        if active_buy_signals:
            # Sortiere Signale nach Stärke (optional, aber kann sinnvoll sein)
            active_buy_signals.sort(key=lambda x: x['strength'], reverse=True)
            
            total_positive_strength = sum(s['strength'] for s in active_buy_signals if s['strength'] > 0)
            print(f"BOT-LOG: Pass 2 - Gesamt-Kauf-Signalstärke (positiv): {total_positive_strength:.4f} für {len(active_buy_signals)} Signale.")

            if total_positive_strength > 0.0001: # Nur fortfahren, wenn eine Gesamtstärke vorhanden ist
                try:
                    if not alpaca_api:
                        print(f"BOT-LOG: Alpaca API nicht initialisiert. Orderplatzierung übersprungen.")
                    else:
                        account_info = alpaca_api.get_account()
                        cash_buffer = 10000 
                        cash_to_use = float(account_info.cash) - cash_buffer
                        print(f"BOT-LOG: Verfügbares Kapital für Trades (nach Puffer von {cash_buffer}): {cash_to_use:.2f} {account_info.currency}")

                        if cash_to_use > 0:
                            print(f"BOT-LOG: Starte Order-Platzierung basierend auf gewichteter Kapitalallokation.")
                            for buy_signal_info in active_buy_signals:
                                if buy_signal_info['strength'] <= 0: continue # Nur positive Stärken für Kauf

                                symbol = buy_signal_info['symbol']
                                strength = buy_signal_info['strength']
                                price_for_qty_calc = buy_signal_info['price_for_qty_calc']

                                # Kapitalallokation proportional zur Stärke
                                capital_for_this_trade = (strength / total_positive_strength) * cash_to_use
                                print(f"BOT-LOG [{symbol}]: Allokiertes Kapital: {capital_for_this_trade:.2f} (Stärke: {strength:.4f})")

                                if price_for_qty_calc > 0 and capital_for_this_trade > 1.0: # Mindestens 1 USD/EUR für einen Trade
                                    qty_to_buy = int(capital_for_this_trade / price_for_qty_calc)
                                    if qty_to_buy > 0:
                                        print(f"BOT-ORDER [{symbol}]: Beabsichtige KAUF-Order für {qty_to_buy} Aktien zum Preis ~{price_for_qty_calc:.2f}.")
                                        # Hier die tatsächliche Orderplatzierung (auskommentiert für Sicherheit):
                                        # try:
                                        #     order = alpaca_api.submit_order(
                                        #         symbol=symbol, qty=qty_to_buy, side='buy', type='market', time_in_force='day'
                                        #     )
                                        #     print(f"BOT-ORDER [{symbol}]: Order platziert: {order.id}")
                                        # except Exception as order_err:
                                        #     print(f"FEHLER bei Orderplatzierung für {symbol}: {order_err}")
                                    else:
                                        print(f"BOT-ORDER [{symbol}]: Nicht genügend allokiertes Kapital für mind. 1 Aktie (Preis: {price_for_qty_calc:.2f}, Kapital: {capital_for_this_trade:.2f}).")
                                else:
                                    print(f"BOT-ORDER [{symbol}]: Ungültiger Preis ({price_for_qty_calc:.2f}) oder zu geringes Kapital ({capital_for_this_trade:.2f}) für Order.")
                                await asyncio.sleep(1) # Kleine Pause zwischen (simulierten) Orderplatzierungen
                        else:
                            print(f"BOT-LOG: Nicht genügend Kapital nach Puffer ({cash_buffer} {account_info.currency}) für Trades verfügbar.")
                except Exception as e:
                    print(f"FEHLER bei Kapitalabruf oder Order-Vorbereitung (Pass 2): {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print("BOT-LOG: Keine Kaufsignale mit ausreichender Gesamtstärke gefunden.")
        else:
            print("BOT-LOG: Keine aktiven Kaufsignale in diesem Durchlauf gefunden.")

        print(f"BOT-LOG: Strategie-Durchlauf beendet. Warte 60 Sekunden bis zum nächsten Durchlauf.")
        await asyncio.sleep(60)  # Warte 60 Sekunden bis zum nächsten kompletten Durchlauf der Strategie

    db_for_loop.close() # Schließe die DB-Session, wenn die Schleife endet
    print("INFO: Bot-Schleife beendet.")

@app.on_event("startup")
async def startup_event():
    # Erstelle Tabellen, falls sie nicht existieren
    # Diese Zeile sollte hier sein, nachdem alle Modelle importiert wurden.
    try:
        models.Base.metadata.create_all(bind=engine)
        print("INFO: Datenbanktabellen (falls nicht vorhanden) erstellt.")
    except Exception as e:
        print(f"FEHLER beim Erstellen der Datenbanktabellen: {e}")

    # Lade alle Modelle beim Start des Bots vor (optional, kann auch on-demand in bot_loop geschehen)
    # initial_target_symbols = ["AAPL", "MSFT", "GOOGL", "NVDA", "AMZN"] # Beispiel
    # print("INFO: Lade Modelle beim Start vor...")
    # for symbol in initial_target_symbols:
    #     load_model_components_for_ticker(symbol.upper())
    # print("INFO: Vorladen der Modelle abgeschlossen.")

# --- ALLES AB HIER ENTFERNEN ---
#                                active_buy_signals.append({
#                                    'symbol': symbol_to_process,
#                                    'strength': strength,
#                                    'price_for_qty_calc': df['close'].iloc[-1] # Aktuellen Schlusskurs für spätere Mengenberechnung speichern
#                                })
#                            else:
#                                print(f"BOT-SIGNAL [{symbol_to_process}]: Schwaches Kaufsignal (Stärke {strength:.4f}), wird ignoriert.")
#                                signal = "NEUTRAL" # Zurücksetzen, wenn zu schwach
#
#                        elif prev_short_ma > prev_long_ma and latest_short_ma < latest_long_ma:
#                            signal = "SELL"
#                            print(f"BOT-SIGNAL [{symbol_to_process}]: VERKAUFSSIGNAL (MA Crossover)")
#                            # Verkaufslogik (noch nicht implementiert für Kapitalallokation)
#                        else:
#                            print(f"BOT-SIGNAL [{symbol_to_process}]: Kein klares MA-Signal")
#                        
#                    else:
#                        print(f"BOT-LOG [{symbol_to_process}]: Nicht genügend historische Daten für MA ({len(historical_data_raw)}/{long_window_ma}).")
#                else:
#                    print(f"BOT-LOG [{symbol_to_process}]: Fehler beim Abrufen hist. Daten von FMP: {hist_response.status_code}")
#
#            except Exception as e:
#                print(f"FEHLER in Bot-Schleife (Pass 1) für Symbol {symbol_to_process}: {e}")
#            await asyncio.sleep(2) # Kurze Pause zwischen der Verarbeitung der Symbole in Pass 1
#
#        # --- Kapitalallokation und Orderplatzierung (Pass 2) ---
#        if active_buy_signals:
#            total_buy_strength = sum(s['strength'] for s in active_buy_signals)
#            print(f"BOT-LOG: Pass 2 - Gesamt-Kauf-Signalstärke: {total_buy_strength:.4f} für {len(active_buy_signals)} Signale.")
#
#            if total_buy_strength > 0.0001: # Nur fortfahren, wenn eine Gesamtstärke vorhanden ist
#                try:
#                    if not alpaca_api:
#                        print(f"BOT-LOG: Alpaca API nicht initialisiert. Orderplatzierung übersprungen.")
#                    else:
#                        account_info = alpaca_api.get_account()
#                        # Dein Puffer, z.B. 10000 EUR/USD
#                        cash_buffer = 10000 
#                        cash_to_use = float(account_info.cash) - cash_buffer
#                        print(f"BOT-LOG: Verfügbares Kapital für Trades (nach Puffer von {cash_buffer}): {cash_to_use:.2f} {account_info.currency}")
#
#                        if cash_to_use > 0:
#                            print(f"BOT-LOG: Starte Order-Platzierung basierend auf gewichteter Kapitalallokation.")
#                            for buy_signal_info in active_buy_signals:
#                                symbol = buy_signal_info['symbol']
#                                strength = buy_signal_info['strength']
#                                price_for_qty_calc = buy_signal_info['price_for_qty_calc']
#
#                                capital_for_this_trade = (strength / total_buy_strength) * cash_to_use
#                                print(f"BOT-LOG [{symbol}]: Allokiertes Kapital: {capital_for_this_trade:.2f} (Stärke: {strength:.4f})")
#
#                                if price_for_qty_calc > 0 and capital_for_this_trade > 1.0: # Mindestens 1 USD/EUR für einen Trade
#                                    qty_to_buy = int(capital_for_this_trade / price_for_qty_calc)
#                                    if qty_to_buy > 0:
#                                        print(f"BOT-ORDER [{symbol}]: Beabsichtige KAUF-Order für {qty_to_buy} Aktien zum Preis ~{price_for_qty_calc:.2f}.")
#                                        # Hier die tatsächliche Orderplatzierung (auskommentiert für Sicherheit):
#                                        # try:
#                                        #     order = alpaca_api.submit_order(
#                                        #         symbol=symbol, qty=qty_to_buy, side='buy', type='market', time_in_force='day'
#                                        #     )
#                                        #     print(f"BOT-ORDER [{symbol}]: Order platziert: {order.id}")
#                                        # except Exception as order_err:
#                                        #     print(f"FEHLER bei Orderplatzierung für {symbol}: {order_err}")
#                                    else:
#                                        print(f"BOT-ORDER [{symbol}]: Nicht genügend allokiertes Kapital für mind. 1 Aktie (Preis: {price_for_qty_calc:.2f}, Kapital: {capital_for_this_trade:.2f}).")
#                                else:
#                                    print(f"BOT-ORDER [{symbol}]: Ungültiger Preis ({price_for_qty_calc:.2f}) oder zu geringes Kapital ({capital_for_this_trade:.2f}) für Order.")
#                                await asyncio.sleep(1) # Kleine Pause zwischen (simulierten) Orderplatzierungen
#                        else:
#                            print(f"BOT-LOG: Nicht genügend Kapital nach Puffer ({cash_buffer} {account_info.currency}) für Trades verfügbar.")
#                except Exception as e:
#                    print(f"FEHLER bei Kapitalabruf oder Order-Vorbereitung (Pass 2): {e}")
#            else:
#                print("BOT-LOG: Keine Kaufsignale mit ausreichender Gesamtstärke gefunden.")
#        else:
#            print("BOT-LOG: Keine aktiven Kaufsignale in diesem Durchlauf gefunden.")
#
#        print(f"BOT-LOG: Strategie-Durchlauf beendet. Warte 60 Sekunden bis zum nächsten Durchlauf.")
#        await asyncio.sleep(60)  # Warte 60 Sekunden bis zum nächsten kompletten Durchlauf der Strategie
#
#    print("INFO: Bot-Schleife beendet.")
# --- BIS HIER ENTFERNEN ---

@app.post("/api/v1/bot/start")
async def start_bot(background_tasks: BackgroundTasks, symbol: str | None = None):
    global bot_is_running, bot_task, current_monitoring_symbol
    if bot_is_running:
        raise HTTPException(status_code=400, detail="Bot läuft bereits.")
    
    # Das `symbol` Argument vom Frontend wird hier für die `current_monitoring_symbol` verwendet,
    # aber die `bot_loop` verwendet jetzt ihre eigene `target_symbols` Liste.
    if symbol: 
        current_monitoring_symbol = symbol.upper()
    bot_is_running = True
    # Starte die bot_loop als Hintergrundaufgabe
    bot_task = asyncio.create_task(bot_loop())
    # background_tasks.add_task(bot_loop) # Alternative mit FastAPI BackgroundTasks
    return {"message": f"Bot erfolgreich gestartet. Überwacht: {current_monitoring_symbol}"}

@app.post("/api/v1/bot/stop")
async def stop_bot():
    global bot_is_running, bot_task
    if not bot_is_running:
        raise HTTPException(status_code=400, detail="Bot läuft nicht.")
    bot_is_running = False
    if bot_task:
        # Hier könnte man versuchen, die Task sauber zu beenden,
        # aber für eine einfache Schleife reicht es, bot_is_running zu setzen.
        # bot_task.cancel() # Könnte verwendet werden, erfordert aber Fehlerbehandlung in der Schleife
        pass
    print("INFO: Bot-Stopp-Anfrage erhalten. Bot wird gestoppt...")
    return {"message": "Bot erfolgreich gestoppt."}