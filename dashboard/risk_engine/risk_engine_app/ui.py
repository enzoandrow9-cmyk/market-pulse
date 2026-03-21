from core import calculate_trade

def run():
    print("=== Standalone Risk Engine ===")

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

