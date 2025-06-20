import math

def kelly_criterion(odds: float, probability: float) -> float:
    """
    Calcola la frazione di Kelly.
    
    Args:
        odds (float): Quota della scommessa.
        probability (float): Probabilità stimata di vincita (tra 0 e 1).
    
    Returns:
        float: Frazione di Kelly.
    """
    if odds <= 1 or probability <= 0 or probability >= 1:
        return 0.0
    return ((odds * probability) - 1) / (odds - 1)

def round_to_nearest_five_cents(amount: float) -> float:
    """
    Arrotonda l'importo al multiplo di 5 centesimi più vicino.
    
    Args:
        amount (float): Importo da arrotondare.
    
    Returns:
        float: Importo arrotondato al multiplo di 5 centesimi più vicino.
    """
    # Converti in centesimi per evitare errori di precisione
    cents = amount * 100
    # Calcola i multipli di 5 centesimi per difetto e per eccesso
    floor_cents = math.floor(cents / 5) * 5
    ceil_cents = math.ceil(cents / 5) * 5
    # Converti di nuovo in euro
    floor_amount = floor_cents / 100
    ceil_amount = ceil_cents / 100
    # Scegli il valore più vicino
    if abs(amount - floor_amount) <= abs(amount - ceil_amount):
        return floor_amount
    return ceil_amount