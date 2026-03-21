def calculate_trade(account_size, risk_percent, entry, stop, target):
    risk_amount = account_size * (risk_percent / 100)
    risk_per_unit = abs(entry - stop)

    if risk_per_unit == 0:
        return {"error": "Stop loss cannot equal entry"}

    position_size = risk_amount / risk_per_unit
    reward_per_unit = abs(target - entry)

    rr_ratio = reward_per_unit / risk_per_unit if risk_per_unit != 0 else 0

    return {
        "position_size": round(position_size, 2),
        "risk_amount": round(risk_amount, 2),
        "risk_per_unit": round(risk_per_unit, 2),
        "reward_per_unit": round(reward_per_unit, 2),
        "risk_reward_ratio": round(rr_ratio, 2)
    }


def run():
    print("=== Risk Engine v1 ===")

    try:
        account_size = float(input("Account size: "))
        risk_percent = float(input("Risk % per trade: "))
        entry = float(input("Entry price: "))
        stop = float(input("Stop loss: "))
        target = float(input("Target price: "))

        result = calculate_trade(account_size, risk_percent, entry, stop, target)

        print("\n--- Result ---")
        for key, value in result.items():
            print(f"{key}: {value}")

    except Exception as e:
        print("Error:", e)


if __name__ == "__main__":
    run()
