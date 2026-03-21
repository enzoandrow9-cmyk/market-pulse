import tkinter as tk
from core import calculate_trade

def calculate():
    try:
        account = float(account_entry.get())
        risk = float(risk_entry.get())
        entry_price = float(entry_entry.get())
        stop = float(stop_entry.get())
        target = float(target_entry.get())

        result = calculate_trade(account, risk, entry_price, stop, target)
        
        output_text.delete("1.0", tk.END)
        for key, value in result.items():
            output_text.insert(tk.END, f"{key}: {value}\n")

    except Exception as e:
        output_text.delete("1.0", tk.END)
        output_text.insert(tk.END, f"Error: {e}")

# Create window
root = tk.Tk()
root.title("Risk Engine")

# Labels
tk.Label(root, text="Account Size").grid(row=0)
tk.Label(root, text="Risk % per trade").grid(row=1)
tk.Label(root, text="Entry Price").grid(row=2)
tk.Label(root, text="Stop Loss").grid(row=3)
tk.Label(root, text="Target Price").grid(row=4)

# Inputs
account_entry = tk.Entry(root)
risk_entry = tk.Entry(root)
entry_entry = tk.Entry(root)
stop_entry = tk.Entry(root)
target_entry = tk.Entry(root)

account_entry.grid(row=0, column=1)
risk_entry.grid(row=1, column=1)
entry_entry.grid(row=2, column=1)
stop_entry.grid(row=3, column=1)
target_entry.grid(row=4, column=1)

# Button
tk.Button(root, text="Calculate", command=calculate).grid(row=5, column=0, columnspan=2)

# Output box
output_text = tk.Text(root, height=10, width=40)
output_text.grid(row=6, column=0, columnspan=2)

# Run app
root.mainloop()
