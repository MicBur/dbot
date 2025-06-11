import os
import torch
import torch.nn as nn
import joblib
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Pfad, unter dem trainierte Modelle, Scaler und Konfigurationen erwartet werden
# Dieser Pfad ist relativ zum Backend-App-Verzeichnis im Docker-Container
BASE_MODEL_DIR = "/app/trained_models" # Angepasst für dbot Struktur

# Standard-Modellparameter (können durch geladene Konfiguration überschrieben werden)
SEQ_LENGTH_DEFAULT = 60
FORECAST_HORIZON_DEFAULT = 7
INPUT_DIM_MODEL_DEFAULT = 2  # Close-Preis + Sentiment-Score
D_MODEL_DEFAULT = 64
NHEAD_DEFAULT = 4
NUM_ENCODER_LAYERS_DEFAULT = 2
DIM_FEEDFORWARD_DEFAULT = 256
DROPOUT_MODEL_DEFAULT = 0.1

class TransformerForecastModel(nn.Module):
    def __init__(self, input_dim, d_model, nhead, num_encoder_layers, dim_feedforward, forecast_horizon, seq_length, dropout=0.1):
        super().__init__()
        self.seq_length = seq_length
        self.input_proj = nn.Linear(input_dim, d_model)
        # Verwende lernbare Positional Embeddings, die zur SEQ_LENGTH passen
        self.pos_encoder = nn.Parameter(torch.zeros(1, seq_length, d_model))
        encoder_layer = nn.TransformerEncoderLayer(d_model=d_model, nhead=nhead, dim_feedforward=dim_feedforward, dropout=dropout, batch_first=True)
        self.transformer_encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_encoder_layers)
        self.output_linear = nn.Linear(d_model, forecast_horizon) # Output für jeden Tag des Horizonts

    def forward(self, src): # src shape: (batch, seq_len, input_dim)
        src = self.input_proj(src)  # (batch, seq_len, d_model)
        # Stelle sicher, dass pos_encoder zur aktuellen Sequenzlänge von src passt
        # Dies ist wichtig, falls das Modell mit variabler Sequenzlänge verwendet wird (hier nicht der Fall)
        src = src + self.pos_encoder[:, :src.size(1), :] # Add positional encoding
        output = self.transformer_encoder(src) # (batch, seq_len, d_model)
        # Nimm den Output des letzten Zeitpunkts der Sequenz für die Vorhersage
        prediction = self.output_linear(output[:, -1, :]) # (batch, forecast_horizon)
        return prediction


LOADED_MODELS_CACHE = {} # Cache für geladene Modelle

def load_model_components_for_ticker(ticker_symbol: str, device_str: str = "cpu"):
    """
    Lädt das trainierte Modell, den Scaler und die Konfiguration für einen bestimmten Ticker.
    """
    if ticker_symbol in LOADED_MODELS_CACHE:
        # print(f"DEBUG: Verwende gecachte Modellkomponenten für {ticker_symbol}")
        return LOADED_MODELS_CACHE[ticker_symbol]

    model_path = os.path.join(BASE_MODEL_DIR, f"{ticker_symbol}_transformer_model.pth")
    scaler_path = os.path.join(BASE_MODEL_DIR, f"{ticker_symbol}_scaler.pkl")
    config_path = os.path.join(BASE_MODEL_DIR, f"{ticker_symbol}_model_config.json")

    if not all(os.path.exists(p) for p in [model_path, scaler_path, config_path]):
        print(f"WARNUNG: Modell, Scaler oder Konfigurationsdatei für {ticker_symbol} nicht gefunden in {BASE_MODEL_DIR}.")
        return None

    try:
        with open(config_path, 'r') as f_cfg:
            model_cfg = json.load(f_cfg)

        scaler = joblib.load(scaler_path)

        model = TransformerForecastModel(
            input_dim=model_cfg.get('input_dim_model', INPUT_DIM_MODEL_DEFAULT),
            d_model=model_cfg.get('d_model', D_MODEL_DEFAULT),
            nhead=model_cfg.get('nhead', NHEAD_DEFAULT),
            num_encoder_layers=model_cfg.get('num_encoder_layers', NUM_ENCODER_LAYERS_DEFAULT),
            dim_feedforward=model_cfg.get('dim_feedforward', DIM_FEEDFORWARD_DEFAULT),
            forecast_horizon=model_cfg.get('forecast_horizon', FORECAST_HORIZON_DEFAULT),
            seq_length=model_cfg.get('sequence_length', SEQ_LENGTH_DEFAULT), # Wichtig für pos_encoder
            dropout=model_cfg.get('dropout_model', DROPOUT_MODEL_DEFAULT)
        ).to(device_str)
        model.load_state_dict(torch.load(model_path, map_location=device_str))
        model.eval()

        components = {'model': model, 'scaler': scaler, 'config': model_cfg, 'device': device_str}
        LOADED_MODELS_CACHE[ticker_symbol] = components
        print(f"INFO: Modellkomponenten für {ticker_symbol} erfolgreich geladen.")
        return components
    except Exception as e:
        print(f"FEHLER beim Laden der Modellkomponenten für {ticker_symbol}: {e}")
        return None

def predict_for_ticker(model_components, latest_sequence_data_np: np.ndarray) -> np.ndarray | None:
    """
    Macht eine Vorhersage mit den geladenen Komponenten und den neuesten Sequenzdaten.
    latest_sequence_data_np: Shape (SEQ_LENGTH, INPUT_DIM_MODEL), unskaliert.
    """
    if not model_components: return None
    model = model_components['model']
    scaler = model_components['scaler']
    config = model_components['config']
    device = model_components['device']

    try:
        scaled_sequence = scaler.transform(latest_sequence_data_np)
        input_tensor = torch.from_numpy(scaled_sequence).unsqueeze(0).float().to(device)
        with torch.no_grad():
            prediction_scaled = model(input_tensor).squeeze().cpu().numpy() # (forecast_horizon,)

        dummy_array_for_inverse = np.zeros((config.get('forecast_horizon', FORECAST_HORIZON_DEFAULT), scaler.n_features_in_))
        dummy_array_for_inverse[:, 0] = prediction_scaled # Annahme: Vorhersage ist für den ersten Feature (Close-Preis)
        prediction_actual_price = scaler.inverse_transform(dummy_array_for_inverse)[:, 0]
        return prediction_actual_price
    except Exception as e:
        print(f"FEHLER bei der Vorhersage: {e}")
        return None