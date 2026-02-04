import os

import json
import pandas as pd
import yfinance as yf
import google.generativeai as genai
from flask import Flask, request, jsonify

# --- AYARLAR ---
 
genai.configure(api_key=os.environ["GEMINI_API_KEY"])

app = Flask(__name__)

def get_working_model():
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                if 'flash' in m.name or 'pro' in m.name:
                    return genai.GenerativeModel(m.name)
    except: pass
    return genai.GenerativeModel('gemini-1.5-flash')

model = get_working_model()

@app.route('/')
def home():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.route('/api/analyze', methods=['POST'])
def analyze():
    try:
        data = request.json
        tv_symbol = data.get('symbol', 'BINANCE:BTCUSDT')
        
        # --- GENİŞLETİLMİŞ SEMBOL EŞLEŞTİRME LİSTESİ ---
        mapping = {
            # Kripto
            "BINANCE:BTCUSDT": "BTC-USD", "BINANCE:ETHUSDT": "ETH-USD",
            "BINANCE:SOLUSDT": "SOL-USD", "BINANCE:AVAXUSDT": "AVAX-USD",
            "BINANCE:XRPUSDT": "XRP-USD", "BINANCE:ADAUSDT": "ADA-USD",
            "BINANCE:DOTUSDT": "DOT-USD", "BINANCE:LINKUSDT": "LINK-USD",
            # Madenler & Emtia
            "XAUUSD": "GC=F", "XAGUSD": "SI=F", "UKOIL": "BZ=F", 
            "USOIL": "CL=F", "HG=F": "HG=F", "PA=F": "PA=F",
            # Endeksler & Pariteler
            "US30": "^DJI", "NAS100": "^NDX", "SPX500": "^GSPC",
            "EURUSD": "EURUSD=X", "GBPUSD": "GBPUSD=X", "USDTRY": "USDTRY=X"
        }
        
        yf_sym = mapping.get(tv_symbol, tv_symbol.replace("BINANCE:", "").replace("USDT", "-USD"))

        # Veri Çekme
        df = yf.download(yf_sym, period="1mo", interval="1d", progress=False)
        if df.empty or len(df) < 5:
            return jsonify({"error": "Borsa verisi çekilemedi. Sembol: " + yf_sym}), 400

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        data_summary = df.tail(15).to_string()
        
        prompt = f"""
        Aşağıdaki son 15 günlük borsa verilerini ({yf_sym}) bir trader gibi analiz et:
        {data_summary}
        
        SADECE aşağıdaki JSON formatında yanıt ver, başka hiçbir metin ekleme:
        {{
            "signal": "BUY veya SELL veya NEUTRAL",
            "confidence": "Sinyalin doğruluk ve tutma oranı(yüzdelik olarak)",
            "leverage": "5x - 10x",
            "stop_loss": "Belirlediğin fiyat",
            "take_profit": "Belirlediğin fiyat",
            "comment": "Türkçe teknik analiz yorumun."
        }}
        """
        
        response = model.generate_content(prompt)
        clean_text = response.text.strip().replace("```json", "").replace("```", "")
        
        return jsonify(json.loads(clean_text))

    except Exception as e:
        return jsonify({"error": str(e)}), 500

import os
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))

    app.run(host='0.0.0.0', port=port)



