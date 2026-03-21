def calculate_trade(account_size, risk_percent, entry, stop, target):
    # Determine trade direction
    if entry > stop:
        trade_type = "LONG"
    elif entry < stop:
        trade_type = "SHORT"
    else:
        return {"error": "Entry and stop cannot be the same"}

    # Basic calculations
    risk_amount = account_size * (risk_percent / 100)
    risk_per_unit = abs(entry - stop)
    reward_per_unit = abs(target - entry)

    position_size = risk_amount / risk_per_unit
    rr_ratio = reward_per_unit / risk_per_unit

    # Validation rules
    warnings = []

    if risk_percent > 2:
        warnings.append("Risk per trade is above 2%")

    if rr_ratio < 2:
        warnings.append("Risk/Reward ratio is below 2.0")

    if position_size <= 0:
        return {"error": "Invalid position size"}

    # Final output
    return {
        "trade_type": trade_type,
        "position_size": round(position_size, 2),
        "risk_amount": round(risk_amount, 2),
        "risk_per_unit": round(risk_per_unit, 2),
        "reward_per_unit": round(reward_per_unit, 2),
        "risk_reward_ratio": round(rr_ratio, 2),
        "warnings": warnings
    }
