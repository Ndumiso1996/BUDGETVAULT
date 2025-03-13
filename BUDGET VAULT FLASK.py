from flask import Flask, render_template, request, jsonify
import json
from datetime import datetime

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
        "carry_over": 0
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
    save_data(data)
    return f"Transfer successful! R{amount} moved to Budget Vault for {days} days. Daily budget: R{data['daily_allocation']}." 

# Function to release daily funds
def release_funds():
    data = load_data()
    if data["remaining_days"] <= 0:
        return "No more funds available."
    
    today = datetime.now().date()
    last_withdrawal = data["last_withdrawal"]
    
    if last_withdrawal is not None:
        last_withdrawal_date = datetime.strptime(last_withdrawal, "%Y-%m-%d").date()
        if last_withdrawal_date == today:
            return "Daily funds already withdrawn for today."
    
    available_funds = data["daily_allocation"] + data["carry_over"]
    data["vault_balance"] -= data["daily_allocation"]
    data["remaining_days"] -= 1
    data["last_withdrawal"] = today.strftime("%Y-%m-%d")
    data["carry_over"] = 0
    save_data(data)
    return f"R{available_funds} released for today. Remaining vault balance: R{data['vault_balance']}."

# Flask Routes
@app.route('/')
def home():
    data = load_data()
    return render_template("index.html", data=data)

@app.route('/transfer', methods=['POST'])
def transfer():
    amount = float(request.form['amount'])
    days = int(request.form['days'])
    message = transfer_to_vault(amount, days)
    return jsonify({"message": message})

@app.route('/release', methods=['POST'])
def release():
    message = release_funds()
    return jsonify({"message": message})

@app.route('/balance', methods=['GET'])
def balance():
    data = load_data()
    return jsonify(data)

if __name__ == "__main__":
    app.run(debug=True)
