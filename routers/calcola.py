from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional

from utils.kelly import round_to_nearest_five_cents

router = APIRouter()
templates = Jinja2Templates(directory="templates")

class KellyResult(BaseModel):
    odds: float
    probability: float
    bankroll: float
    kelly_percentage: float
    implied_probability: float
    is_value_bet: bool
    value_bet_text: str
    ev_per_unit: float
    advantage: float
    advantage_judgment: str
    fraction_lines: list
    expected_profit_percentage: float

@router.get("/calcola", response_class=HTMLResponse)
async def get_calcola_form(request: Request):
    return templates.TemplateResponse("calcola.html", {"request": request})

@router.post("/calcola", response_class=HTMLResponse)
async def post_calcola_form(
    request: Request,
    odds: float = Form(...),
    probability: float = Form(...),
    bankroll: float = Form(...)
):
    error = None
    if odds <= 1:
        error = "La quota deve essere maggiore di 1."
    elif not 0 < probability < 1:
        error = "La probabilità deve essere compresa tra 0 e 1."
    elif bankroll <= 0:
        error = "Il bankroll deve essere maggiore di 0."
    
    if error:
        return templates.TemplateResponse("calcola.html", {"request": request, "error": error})

    kelly_percentage = ((odds * probability) - 1) / (odds - 1)
    
    if kelly_percentage <= 0:
        error = "La frazione di Kelly è negativa o zero. Non c'è valore atteso positivo per questa scommessa."
        return templates.TemplateResponse("calcola.html", {"request": request, "error": error})

    implied_probability = 1 / odds
    is_value_bet = probability > implied_probability
    value_bet_text = "✅ Sì" if is_value_bet else "❌ No"
    ev_per_unit = (probability * (odds - 1)) - (1 - probability)
    advantage = (probability - implied_probability) / implied_probability * 100 if implied_probability > 0 else 0

    if advantage > 10:
        advantage_judgment = "⭐ Ottimo vantaggio!"
    elif advantage > 5:
        advantage_judgment = "👍 Buon vantaggio"
    elif advantage > 0:
        advantage_judgment = "👌 Vantaggio minimo"
    else:
        advantage_judgment = "⚠ Nessun vantaggio significativo"

    fractions = [(1/8, "1/8"), (1/10, "1/10"), (1/15, "1/15"), (1/20, "1/20")]
    fraction_lines = []
    for frac_value, frac_label in fractions:
        bet_amount = kelly_percentage * bankroll * frac_value
        bet_amount_rounded = round_to_nearest_five_cents(bet_amount)
        bet_percentage = (bet_amount_rounded / bankroll) * 100
        prize = bet_amount_rounded * odds
        fraction_lines.append({
            "label": frac_label,
            "bet_amount": f"{bet_amount_rounded:.2f}",
            "bet_percentage": f"{bet_percentage:.2f}%",
            "prize": f"{prize:.2f}"
        })
    
    expected_profit_percentage = ev_per_unit * 100

    results = KellyResult(
        odds=odds,
        probability=probability,
        bankroll=bankroll,
        kelly_percentage=kelly_percentage,
        implied_probability=implied_probability,
        is_value_bet=is_value_bet,
        value_bet_text=value_bet_text,
        ev_per_unit=ev_per_unit,
        advantage=advantage,
        advantage_judgment=advantage_judgment,
        fraction_lines=fraction_lines,
        expected_profit_percentage=expected_profit_percentage,
    )

    return templates.TemplateResponse("calcola.html", {"request": request, "results": results.dict()}) 