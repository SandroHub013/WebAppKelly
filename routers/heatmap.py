from fastapi import APIRouter, Request, File, UploadFile, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import pandas as pd
import io
from datetime import datetime, timedelta
import numpy as np

router = APIRouter()
templates = Jinja2Templates(directory="webapp/templates")

def get_market_from_title(title):
    if pd.isna(title): return "Altro"
    title_lower = str(title).lower()
    if any(keyword in title_lower for keyword in ['under', 'over', 'o/u']): return 'Over/Under'
    if any(keyword in title_lower for keyword in ['1x2', '1)', '2)', 'x)', '(1x)', '(x2)', 'x2', '1x']): return '1X2'
    if any(keyword in title_lower for keyword in ['entrambe', 'segnano', 'gg', 'both teams', 'btts']): return 'Entrambe segnano'
    if any(keyword in title_lower for keyword in ['handicap', 'spread', 'asian']): return 'Handicap'
    if any(keyword in title_lower for keyword in ['corner', 'angolo', 'calcio d\'angolo']): return 'Corner'
    if any(keyword in title_lower for keyword in ['card', 'cartell', 'ammonizio']): return 'Cartellini'
    return 'Altro'

def get_odds_range(odds):
    if pd.isna(odds): return "N/A"
    odds = float(odds)
    if odds < 1.5: return "< 1.5"
    if odds < 1.8: return "1.5-1.8"
    if odds < 2.5: return "1.8-2.5"
    if odds < 3.5: return "2.5-3.5"
    if odds < 5.0: return "3.5-5.0"
    return "5.0+"

def get_performance_note(roi, sample_size):
    if sample_size < 5: return "Campione insufficiente"
    note_suffix = ""
    if sample_size < 20: note_suffix = " (Campione ridotto)"
    elif sample_size < 50: note_suffix = " (Campione minimo)"
    
    if roi > 10: return f"Ottimo{note_suffix}"
    if roi > 5: return f"Buono{note_suffix}"
    if roi > 0: return f"Discreto{note_suffix}"
    if roi > -5: return f"Marginale{note_suffix}"
    return f"Poco efficace{note_suffix}"

def transform_csv_to_heatmap_data(df: pd.DataFrame):
    # Clean column names
    df.columns = [col.strip().replace(' ', '_') for col in df.columns]
    
    # Calculate profit if not present
    if 'Profitto' not in df.columns or df['Profitto'].isnull().all():
        df['Puntata'] = pd.to_numeric(df['Puntata'].astype(str).str.replace(',', '.'), errors='coerce')
        df['Quote'] = pd.to_numeric(df['Quote'].astype(str).str.replace(',', '.'), errors='coerce')
        df['Profitto'] = np.where(df['Stato'] == 'Vinto', (df['Puntata'] * df['Quote']) - df['Puntata'], -df['Puntata'])
        df.loc[df['Stato'] == 'Nullo', 'Profitto'] = 0

    grouped_data = {}
    for _, row in df.iterrows():
        market = get_market_from_title(row['Titolo_della_scommessa'])
        odds_range = get_odds_range(row['Quote'])
        key = (market, odds_range)
        
        if key not in grouped_data:
            grouped_data[key] = {'wins': 0, 'total': 0, 'total_bet': 0, 'total_profit': 0}
        
        grouped_data[key]['total'] += 1
        grouped_data[key]['total_bet'] += row['Puntata']
        grouped_data[key]['total_profit'] += row['Profitto']
        if row['Stato'] == 'Vinto':
            grouped_data[key]['wins'] += 1
    
    heatmap_data = []
    for (market, odds_range), stats in grouped_data.items():
        if stats['total'] == 0: continue
        win_rate = (stats['wins'] / stats['total']) * 100
        roi = (stats['total_profit'] / stats['total_bet']) * 100 if stats['total_bet'] > 0 else -100
        note = get_performance_note(roi, stats['total'])
        heatmap_data.append([market, odds_range, f"{win_rate:.1f}%", f"{roi:+.1f}%", note, str(stats['total'])])

    market_order = ['1X2', 'Over/Under', 'Entrambe segnano', 'Handicap', 'Corner', 'Cartellini', 'Altro']
    odds_order = ['< 1.5', '1.5-1.8', '1.8-2.5', '2.5-3.5', '3.5-5.0', '5.0+']
    
    def sort_key(item):
        market, odds_range = item[0], item[1]
        market_idx = market_order.index(market) if market in market_order else len(market_order)
        odds_idx = odds_order.index(odds_range) if odds_range in odds_order else len(odds_order)
        return (market_idx, odds_idx)
    
    heatmap_data.sort(key=sort_key)
    
    return heatmap_data, market_order, odds_order

@router.get("/heatmap", response_class=HTMLResponse)
async def get_heatmap_form(request: Request):
    return templates.TemplateResponse("heatmap.html", {"request": request})

@router.post("/heatmap", response_class=HTMLResponse)
async def post_heatmap_form(
    request: Request, 
    csv_file: UploadFile = File(...),
    period: str = Form("all")
):
    try:
        content = await csv_file.read()
        df = pd.read_csv(io.StringIO(content.decode('utf-8')), sep=';')
        
        df['Data'] = pd.to_datetime(df['Data'], format='%d/%m/%Y %H:%M', errors='coerce')

        if period != 'all':
            days = int(period.replace('days',''))
            cutoff_date = datetime.now() - timedelta(days=days)
            df = df[df['Data'] > cutoff_date]
        
        df = df[df['Stato'].isin(['Vinto', 'Perso'])]
        
        if len(df) == 0:
            return templates.TemplateResponse("heatmap.html", {"request": request, "error": "Nessuna scommessa trovata per il periodo selezionato."})

        heatmap_data, markets, odds_ranges = transform_csv_to_heatmap_data(df)

        # Pivot data for table display
        pivot_df = pd.DataFrame(heatmap_data, columns=['Market', 'OddsRange', 'WinRate', 'ROI', 'Note', 'Total'])
        heatmap_table = pivot_df.pivot(index='Market', columns='OddsRange', values='ROI').reindex(index=markets, columns=odds_ranges)
        
        results = {
            "filename": csv_file.filename,
            "period": period,
            "num_rows": len(df),
            "heatmap_table": heatmap_table.to_dict(orient='index'),
            "markets": markets,
            "odds_ranges": odds_ranges,
            "raw_data": pivot_df.to_dict(orient='records')
        }

        return templates.TemplateResponse("heatmap.html", {"request": request, "results": results})
    except Exception as e:
        return templates.TemplateResponse("heatmap.html", {"request": request, "error": f"An error occurred: {str(e)}"}) 