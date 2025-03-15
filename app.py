from flask import Flask, render_template, request, jsonify
import json
from datetime import datetime, timedelta
app = Flask(__name__)
# File to store vault and account data
DATA_FILE = "vault_data.json"

# Function to load data
def load_data():
    default_data = {
        "main_account": 5000,
        "vault_balance": 0,
        "daily_allocation": 0,
        "remaining_days": 0,
        "last_withdrawal": None,
        "carry_over": 0,
        "budget_cycle_active": False
    }
    try:
        with open(DATA_FILE, "r") as file:
            data = json.load(file)
            for key, value in default_data.items():
                if key not in data:
                    data[key] = value
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        return default_data

# Function to save data
def save_data(data):
    with open(DATA_FILE, "w") as file:
        json.dump(data, file, indent=4)

# Function to transfer funds from main account to vault
def transfer_to_vault(amount, days):
    """
    Transfers funds from main account to the budget vault.
    
    This function allocates a specified amount from the main account to the vault
    and calculates the daily allocation for the specified number of days.
    
    Parameters:
    - amount: The amount to transfer from main account to vault
    - days: The number of days to divide the amount over
    
    Returns:
    - A message indicating success or failure
    """
    data = load_data()
    if amount <= 0 or days <= 0:
        return "Invalid transfer amount or duration."
    if amount > data["main_account"]:
        return "Insufficient funds in main account."
    
    data["main_account"] -= amount
    data["vault_balance"] = amount
    data["daily_allocation"] = round(amount / days, 2)
    data["remaining_days"] = days
    data["last_withdrawal"] = None
    data["carry_over"] = 0
    data["budget_cycle_active"] = True
    save_data(data)
    return f"Transfer successful! R{amount:.2f} moved to Budget Vault for {days} days. Daily budget: R{data['daily_allocation']:.2f}." 

# Function to release daily funds
def release_funds(percentage=100):
    """
    Releases funds from the vault based on daily allocation and specified percentage.
    
    This function calculates the amount to release based on daily allocation,
    missed days, and the percentage the user wants to withdraw. Any undrawn
    amount is added to carry-over for future withdrawals.
    
    Parameters:
    - percentage: The percentage of available funds to withdraw (default: 100%)
    
    Returns:
    - A message indicating success or failure
    """
    data = load_data()
    today = datetime.now().date()
    
    # Convert percentage to decimal and validate
    percentage = float(percentage)
    if percentage <= 0 or percentage > 100:
        return "Invalid percentage. Please enter a value between 1 and 100."
    percentage_decimal = percentage / 100
    
    # Check if budget cycle is active
    if not data["budget_cycle_active"]:
        return "No active budget cycle. Please transfer funds to the vault first."
    
    # Check if there are any remaining days in the budget
    if data["remaining_days"] <= 0 and data["carry_over"] <= 0:
        return "No more funds available."
    
    last_withdrawal = data["last_withdrawal"]
    days_missed = 0
    
    # Calculate days missed since last withdrawal
    if last_withdrawal is not None:
        last_withdrawal_date = datetime.strptime(last_withdrawal, "%Y-%m-%d").date()
        if last_withdrawal_date == today:
            return "Daily funds already withdrawn for today."
        
        # Calculate missed days (excluding today)
        days_missed = (today - last_withdrawal_date).days - 1
        if days_missed < 0:
            days_missed = 0
    
    # Calculate how many days to account for (limited by remaining days)
    days_to_account = min(days_missed + 1, data["remaining_days"])
    
    # Calculate total available funds
    total_available = data["daily_allocation"] * days_to_account + data["carry_over"]
    
    # Calculate funds to release based on percentage
    funds_to_release = total_available * percentage_decimal
    funds_to_release = round(funds_to_release, 2)
    
    # Calculate new carry-over amount
    new_carry_over = total_available - funds_to_release
    
    # Update vault balance and remaining days
    deduction_from_vault = data["daily_allocation"] * days_to_account
    if deduction_from_vault > data["vault_balance"]:
        deduction_from_vault = data["vault_balance"]
    
    data["vault_balance"] -= deduction_from_vault
    data["remaining_days"] -= days_to_account
    if data["remaining_days"] < 0:
        data["remaining_days"] = 0
    
    # Update last withdrawal date and carry over
    data["last_withdrawal"] = today.strftime("%Y-%m-%d")
    data["carry_over"] = new_carry_over
    
    # Check if budget cycle is complete
    if data["remaining_days"] <= 0 and data["vault_balance"] <= 0:
        data["budget_cycle_active"] = False
    
    save_data(data)
    return f"R{funds_to_release:.2f} released ({percentage:.0f}% of available R{total_available:.2f}). R{new_carry_over:.2f} added to carry-over. Remaining vault balance: R{data['vault_balance']:.2f}."

# Function to withdraw all remaining funds
def withdraw_all_funds():
    """
    Withdraws all remaining funds from the vault back to the main account.
    
    This function can only be executed when the budget cycle is complete
    (no remaining days) or when there is only carry-over funds left.
    This ensures budget discipline is maintained during the active cycle.
    
    Returns:
    - A message indicating success or failure
    """
    data = load_data()
    
    if data["vault_balance"] <= 0 and data["carry_over"] <= 0:
        return "No funds available to withdraw."
    
    # Check if budget cycle is active and has remaining days
    if data["budget_cycle_active"] and data["remaining_days"] > 0:
        return "Cannot withdraw funds while budget cycle is active. Complete the cycle first or withdraw your daily allocation."
    
    # Calculate total amount to withdraw
    amount_withdrawn = data["vault_balance"] + data["carry_over"]
    
    # Update balances
    data["main_account"] += amount_withdrawn
    data["vault_balance"] = 0
    data["remaining_days"] = 0
    data["daily_allocation"] = 0
    data["carry_over"] = 0
    data["budget_cycle_active"] = False
    
    save_data(data)
    return f"R{amount_withdrawn:.2f} withdrawn from vault and returned to main account."

# Flask Routes
@app.route('/')
def home():
    data = load_data()
    return render_template("index.html", data=data)

@app.route('/transfer', methods=['POST'])
def transfer():
    """API endpoint to transfer funds from main account to vault"""
    amount = float(request.form['amount'])
    days = int(request.form['days'])
    message = transfer_to_vault(amount, days)
    return jsonify({"message": message, "status": "success"})

@app.route('/release', methods=['POST'])
def release():
    """API endpoint to release daily funds based on percentage"""
    percentage = request.form.get('percentage', 100)
    message = release_funds(percentage)
    data = load_data()
    return jsonify({
        "message": message, 
        "status": "success", 
        "data": data
    })

@app.route('/withdraw-remaining', methods=['POST'])
def withdraw_remaining():
    """API endpoint to withdraw all remaining funds"""
    message = withdraw_all_funds()
    data = load_data()
    return jsonify({
        "message": message,
        "status": "success",
        "data": data
    })

@app.route('/balance', methods=['GET'])
def balance():
    """API endpoint to get current balance information"""
    data = load_data()
    return jsonify(data)

if __name__ == "__main__":
    app.run(debug=True)
