from fastapi import APIRouter, Request, File, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import pandas as pd
import numpy as np
import io
from datetime import datetime
import os

# Get the absolute path of the project's root directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

def calculate_confidence_interval(wins, total, confidence=0.95):
    """Calculate confidence interval for win rate."""
    if total == 0:
        return 0, 0
    
    p = wins / total
    z = 1.96  # 95% confidence level
    margin = z * np.sqrt((p * (1 - p)) / total)
    return (p - margin) * 100, (p + margin) * 100

def analyze_risk(profit_std, avg_profit, sharpe_ratio):
    """
    Analizza il rischio basato su deviazione standard, profitto medio e Sharpe Ratio.
    """
    if avg_profit == 0:
        return "⚠️ Non determinabile: nessun profitto medio"
    
    cv = profit_std / abs(avg_profit)  # Coefficient of variation
    
    sharpe_analysis = ""
    if sharpe_ratio > 1.5:
        sharpe_analysis = "Eccellente rapporto rischio/rendimento"
    elif sharpe_ratio > 1.0:
        sharpe_analysis = "Buon rapporto rischio/rendimento"
    elif sharpe_ratio > 0.5:
        sharpe_analysis = "Discreto rapporto rischio/rendimento"
    else:
        sharpe_analysis = "Basso rapporto rischio/rendimento"
    
    if cv > 2:
        return f"❌ Rischioso: alta variabilità dei risultati. {sharpe_analysis}."
    elif cv > 1:
        return f"⚠️ Moderatamente rischioso: variabilità significativa. {sharpe_analysis}."
    else:
        return f"✅ Stabile: risultati consistenti. {sharpe_analysis}."

def analyze_sample_size(total_bets):
    """Analyze if the sample size is sufficient."""
    if total_bets >= 100:
        return "✅ Solido: campione sufficiente per un'analisi affidabile."
    elif total_bets >= 50:
        return "⚠️ Parziale: Hai {} eventi, ma si consigliano almeno 100 per un backtest solido.".format(total_bets)
    else:
        return "❌ Limitato: il campione è troppo piccolo per un'analisi affidabile."

def process_betting_data(df: pd.DataFrame):
    """Process the betting data from a DataFrame and return statistics."""
    # Clean column names
    df.columns = [col.strip().replace(' ', '_') for col in df.columns]

    # Data transformation
    df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
    df['Puntata'] = pd.to_numeric(df['Puntata'].astype(str).str.replace(',', '.'), errors='coerce')
    df['Quote'] = pd.to_numeric(df['Quote'].astype(str).str.replace(',', '.'), errors='coerce')
    df['Profitto'] = pd.to_numeric(df['Profitto'].astype(str).str.replace(',', '.'), errors='coerce')

    # Remove rows with missing essential data
    df.dropna(subset=['Data', 'Puntata', 'Quote', 'Stato'], inplace=True)
    df = df[df['Stato'] != 'Rimborso']
    
    # Calculate profit if not present
    if 'Profitto' not in df.columns or df['Profitto'].isnull().all():
        df['Profitto'] = np.where(df['Stato'] == 'Vinto', (df['Puntata'] * df['Quote']) - df['Puntata'], -df['Puntata'])
        df.loc[df['Stato'] == 'Nullo', 'Profitto'] = 0

    # Basic statistics
    total_bets = len(df)
    wins = (df['Stato'] == 'Vinto').sum()
    losses = (df['Stato'] == 'Perso').sum()
    voids = (df['Stato'] == 'Nullo').sum()
    win_rate = (wins / total_bets) * 100 if total_bets > 0 else 0
    avg_odds = df['Quote'].mean()
    total_staked = df['Puntata'].sum()
    total_profit = df['Profitto'].sum()
    roi = (total_profit / total_staked) * 100 if total_staked > 0 else 0

    # Advanced metrics
    df['Cumulative_Profit'] = df['Profitto'].cumsum()
    peak = df['Cumulative_Profit'].cummax()
    drawdown = (df['Cumulative_Profit'] - peak)
    max_drawdown = drawdown.min()
    
    # Sharpe Ratio
    daily_profit = df.set_index('Data')['Profitto'].resample('D').sum()
    if len(daily_profit) > 1 and daily_profit.std() != 0:
        sharpe_ratio = (daily_profit.mean() / daily_profit.std()) * np.sqrt(365)
    else:
        sharpe_ratio = 0

    # Confidence Interval
    ci_lower, ci_upper = calculate_confidence_interval(wins, total_bets)
    
    # Risk analysis
    risk_analysis = analyze_risk(df['Profitto'].std(), df['Profitto'].mean(), sharpe_ratio)
    sample_size_analysis = analyze_sample_size(total_bets)

    return {
        "total_bets": total_bets,
        "wins": wins,
        "losses": losses,
        "voids": voids,
        "win_rate": f"{win_rate:.2f}%",
        "avg_odds": f"{avg_odds:.2f}",
        "total_staked": f"{total_staked:.2f}",
        "total_profit": f"{total_profit:.2f}",
        "roi": f"{roi:.2f}%",
        "max_drawdown": f"{max_drawdown:.2f}",
        "sharpe_ratio": f"{sharpe_ratio:.2f}",
        "confidence_interval": f"{ci_lower:.2f}% - {ci_upper:.2f}%",
        "risk_analysis": risk_analysis,
        "sample_size_analysis": sample_size_analysis,
    }

@router.get("/backtest", response_class=HTMLResponse)
async def get_backtest_form(request: Request):
    return templates.TemplateResponse("backtest.html", {"request": request})

@router.post("/backtest", response_class=HTMLResponse)
async def post_backtest_form(request: Request, csv_file: UploadFile = File(...)):
    try:
        content = await csv_file.read()
        # Use a different separator if needed, e.g., sep=';'
        df = pd.read_csv(io.StringIO(content.decode('utf-8')), sep=';')
        
        results = process_betting_data(df)
        results["filename"] = csv_file.filename

        return templates.TemplateResponse("backtest.html", {"request": request, "results": results})
    except Exception as e:
        return templates.TemplateResponse("backtest.html", {"request": request, "error": str(e)}) 