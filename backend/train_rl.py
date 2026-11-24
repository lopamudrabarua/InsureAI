#!/usr/bin/env python3
"""
InsureAI RL Training Script

Trains a Q-learning agent for claim decision making using historical fraud data.
States: risk_band (Low/Medium/High) x complexity (Low/Medium/High) x cost_tier (Low/High)
Actions: Approve, Review, Investigate
Rewards: Based on fraud detection accuracy and cost savings
"""

import os
import pickle
import numpy as np
import pandas as pd
import joblib
from pathlib import Path

BASE_DIR = Path(__file__).parent

# Load models
fraud_model = joblib.load(BASE_DIR / "fraud_model_improved.pkl")
low_cost_model = joblib.load(BASE_DIR / "low_cost_model.pkl")
collision_cost_model = joblib.load(BASE_DIR / "collision_cost_model.pkl")

with open(BASE_DIR / "fraud_threshold.txt", "r") as f:
    FRAUD_THRESHOLD = float(f.read().strip())

# Load historical data
fraud_data = pd.read_excel(BASE_DIR.parent / "fraud_detection.xlsx")

print(f"Loaded {len(fraud_data)} historical claims")

# ==========================================
# FEATURE ENGINEERING FOR RL STATES
# ==========================================

fraud_features = fraud_model.feature_names_in_.tolist()
cost_features = low_cost_model.regressor_.feature_names_in_.tolist()

def prepare_input(data, features, model):
    """Prepare input for model prediction (same as app.py)"""
    missing = [f for f in features if f not in data.columns]
    if missing:
        # Fill missing with defaults
        for f in missing:
            data[f] = 0 if data[f].dtype in ['int64', 'float64'] else 'unknown'

    df_input = data[features].copy()

    if hasattr(model, "regressor_"):
        pipeline = model.regressor_
    else:
        pipeline = model

    preprocessor = pipeline.named_steps["preprocessor"]

    for name, transformer, columns in preprocessor.transformers_:
        if name == "num":
            for column in columns:
                if column in df_input.columns:
                    df_input[column] = pd.to_numeric(df_input[column], errors="coerce")
        elif name == "cat":
            for column in columns:
                if column in df_input.columns:
                    df_input[column] = df_input[column].map(
                        lambda v: str(v) if pd.notna(v) else np.nan
                    )

    return df_input

def calculate_complexity(row):
    """Calculate claim complexity (same as app.py)"""
    score = 0

    severity = str(row.get("incident_severity", "")).strip().lower()
    if severity in ["major damage", "total loss"]:
        score += 2
    elif severity == "minor damage":
        score += 1

    vehicles = pd.to_numeric(row.get("number_of_vehicles_involved", 0), errors="coerce")
    injuries = pd.to_numeric(row.get("bodily_injuries", 0), errors="coerce")
    witnesses = pd.to_numeric(row.get("witnesses", 0), errors="coerce")

    if pd.notna(vehicles):
        if vehicles >= 3:
            score += 2
        elif vehicles == 2:
            score += 1

    if pd.notna(injuries):
        if injuries >= 2:
            score += 2
        elif injuries == 1:
            score += 1

    if pd.notna(witnesses) and witnesses >= 2:
        score += 1

    police_report = str(row.get("police_report_available", "")).strip().upper()
    if police_report == "YES":
        score += 1

    if score <= 2:
        return "Low"
    elif score <= 4:
        return "Medium"
    return "High"

def get_risk_band(probability):
    """Three-band risk classification"""
    if probability >= FRAUD_THRESHOLD:
        return "High"
    if probability >= FRAUD_THRESHOLD * 0.5:
        return "Medium"
    return "Low"

def get_cost_tier(expected_cost, median_cost):
    """Classify expected cost as Low or High"""
    return "High" if expected_cost > median_cost else "Low"

# ==========================================
# PREPARE TRAINING DATA
# ==========================================

print("Preparing training data...")

# Predict fraud probabilities for all historical claims
fraud_input = prepare_input(fraud_data, fraud_features, fraud_model)
fraud_probs = fraud_model.predict_proba(fraud_input)[:, list(fraud_model.classes_).index("Y")]

# Predict expected costs
cost_input = prepare_input(fraud_data, cost_features, low_cost_model)

incident_types = fraud_data["incident_type"].values
expected_costs = []
for i, itype in enumerate(incident_types):
    row_input = cost_input.iloc[[i]]
    if itype in ["Vehicle Theft", "Parked Car"]:
        cost = low_cost_model.predict(row_input)[0]
    elif itype in ["Single Vehicle Collision", "Multi-vehicle Collision"]:
        cost = collision_cost_model.predict(row_input)[0]
    else:
        cost = low_cost_model.predict(row_input)[0]
    expected_costs.append(max(0, float(cost)))

expected_costs = np.array(expected_costs)
median_cost = np.median(expected_costs)

# Calculate complexity and risk bands
complexities = fraud_data.apply(calculate_complexity, axis=1)
risk_bands = [get_risk_band(p) for p in fraud_probs]
cost_tiers = [get_cost_tier(c, median_cost) for c in expected_costs]

# True fraud labels
true_fraud = (fraud_data["fraud_reported"] == "Y").astype(int)

# Add to dataframe
fraud_data["fraud_prob"] = fraud_probs
fraud_data["expected_cost"] = expected_costs
fraud_data["complexity"] = complexities
fraud_data["risk_band"] = risk_bands
fraud_data["cost_tier"] = cost_tiers
fraud_data["true_fraud"] = true_fraud

print(f"Fraud distribution: {fraud_data['true_fraud'].value_counts().to_dict()}")
print(f"Risk band distribution: {fraud_data['risk_band'].value_counts().to_dict()}")
print(f"Complexity distribution: {fraud_data['complexity'].value_counts().to_dict()}")
print(f"Cost tier distribution: {fraud_data['cost_tier'].value_counts().to_dict()}")

# ==========================================
# Q-LEARNING TRAINING
# ==========================================

# State space: risk_band (3) x complexity (3) x cost_tier (2) = 18 states
risk_bands_list = ["Low", "Medium", "High"]
complexities_list = ["Low", "Medium", "High"]
cost_tiers_list = ["Low", "High"]
actions = ["Approve", "Review", "Investigate"]

state_to_idx = {}
idx = 0
for rb in risk_bands_list:
    for c in complexities_list:
        for ct in cost_tiers_list:
            state_to_idx[(rb, c, ct)] = idx
            idx += 1

n_states = len(state_to_idx)
n_actions = len(actions)

print(f"State space size: {n_states}")
print(f"Action space size: {n_actions}")

# Initialize Q-table
q_table = np.zeros((n_states, n_actions))

# Q-learning hyperparameters
alpha = 0.1      # learning rate
gamma = 0.95     # discount factor
epsilon = 1.0    # exploration rate
epsilon_min = 0.01
epsilon_decay = 0.995
episodes = 5000

# Reward function
def get_reward(action, true_fraud, expected_cost, fraud_prob):
    """
    Reward design:
    - Approve genuine claim: +10 (cost saved from not investigating)
    - Approve fraudulent claim: -50 (fraud loss)
    - Review genuine claim: -5 (unnecessary review cost)
    - Review fraudulent claim: +20 (fraud caught via review)
    - Investigate genuine claim: -20 (investigation cost)
    - Investigate fraudulent claim: +50 (fraud caught via investigation)
    """
    if action == "Approve":
        if true_fraud == 1:
            return -50 * fraud_prob  # Scale by fraud probability
        else:
            return 10
    elif action == "Review":
        if true_fraud == 1:
            return 20 * fraud_prob
        else:
            return -5
    elif action == "Investigate":
        if true_fraud == 1:
            return 50 * fraud_prob
        else:
            return -20
    return 0

# Training loop
print("Training Q-learning agent...")
for episode in range(episodes):
    # Sample a random historical claim
    idx_claim = np.random.randint(len(fraud_data))
    row = fraud_data.iloc[idx_claim]

    state = (row["risk_band"], row["complexity"], row["cost_tier"])
    state_idx = state_to_idx[state]
    true_fraud = row["true_fraud"]
    exp_cost = row["expected_cost"]
    fraud_prob = row["fraud_prob"]

    # Epsilon-greedy action selection
    if np.random.random() < epsilon:
        action_idx = np.random.randint(n_actions)
    else:
        action_idx = np.argmax(q_table[state_idx])

    action = actions[action_idx]
    reward = get_reward(action, true_fraud, exp_cost, fraud_prob)

    # For simplicity, assume next state is terminal (single-step decisions)
    # In a more complex setup, we'd model state transitions
    next_max = 0  # Terminal state

    # Q-learning update
    q_table[state_idx, action_idx] += alpha * (reward + gamma * next_max - q_table[state_idx, action_idx])

    # Decay epsilon
    if epsilon > epsilon_min:
        epsilon *= epsilon_decay

    if episode % 1000 == 0:
        print(f"Episode {episode}, epsilon: {epsilon:.4f}")

print("Training complete!")

# ==========================================
# EVALUATE TRAINED POLICY
# ==========================================

print("\nEvaluating trained policy...")

# Test on all data
correct_decisions = 0
total_reward = 0

for i in range(len(fraud_data)):
    row = fraud_data.iloc[i]
    state = (row["risk_band"], row["complexity"], row["cost_tier"])
    state_idx = state_to_idx[state]

    best_action_idx = np.argmax(q_table[state_idx])
    best_action = actions[best_action_idx]

    reward = get_reward(best_action, row["true_fraud"], row["expected_cost"], row["fraud_prob"])
    total_reward += reward

    # Check if decision aligns with fraud status
    if (best_action == "Investigate" and row["true_fraud"] == 1) or \
       (best_action == "Review" and row["true_fraud"] == 1) or \
       (best_action == "Approve" and row["true_fraud"] == 0):
        correct_decisions += 1

accuracy = correct_decisions / len(fraud_data)
avg_reward = total_reward / len(fraud_data)

print(f"Decision accuracy: {accuracy:.2%}")
print(f"Average reward per claim: {avg_reward:.2f}")

# Print Q-table
print("\nLearned Q-table:")
q_df = pd.DataFrame(q_table, columns=actions, index=[f"{rb}_{c}_{ct}" for (rb, c, ct) in state_to_idx.keys()])
print(q_df.round(2))

# Save Q-table as CSV (compatible with app.py format)
# app.py expects index: Low, Medium, High and columns: Approve, Review, Investigate
# We'll aggregate over complexity and cost_tier for backward compatibility
simple_q_table = pd.DataFrame(0.0, index=risk_bands_list, columns=actions)

for rb in risk_bands_list:
    for action_idx, action in enumerate(actions):
        # Average over complexity and cost_tier
        values = []
        for c in complexities_list:
            for ct in cost_tiers_list:
                state_idx = state_to_idx[(rb, c, ct)]
                values.append(q_table[state_idx, action_idx])
        simple_q_table.loc[rb, action] = np.mean(values)

print("\nAggregated Q-table (for app.py compatibility):")
print(simple_q_table.round(2))

# Save
simple_q_table.to_csv(BASE_DIR / "rl_q_table.csv")
print(f"\nSaved Q-table to {BASE_DIR / 'rl_q_table.csv'}")

# Also save the full Q-table for future reference
full_q_df = pd.DataFrame(
    q_table,
    columns=actions,
    index=pd.MultiIndex.from_tuples(state_to_idx.keys(), names=["risk_band", "complexity", "cost_tier"])
)
full_q_df.to_csv(BASE_DIR / "rl_q_table_full.csv")
print(f"Saved full Q-table to {BASE_DIR / 'rl_q_table_full.csv'}")

# Save training metadata
metadata = {
    "n_states": n_states,
    "n_actions": n_actions,
    "alpha": alpha,
    "gamma": gamma,
    "episodes": episodes,
    "accuracy": accuracy,
    "avg_reward": avg_reward,
    "fraud_threshold": FRAUD_THRESHOLD,
    "median_cost": median_cost,
    "state_mapping": state_to_idx,
    "actions": actions
}

import json
with open(BASE_DIR / "rl_training_metadata.json", "w") as f:
    # Convert non-serializable items
    serializable_meta = {k: v for k, v in metadata.items() if k != "state_mapping"}
    serializable_meta["state_mapping"] = {str(k): v for k, v in state_to_idx.items()}
    json.dump(serializable_meta, f, indent=2)

print("Training metadata saved.")

# ==========================================
# VERIFICATION: Test the new Q-table with app.py logic
# ==========================================

print("\n" + "="*50)
print("VERIFICATION: Testing with app.py decision logic")
print("="*50)

# Load the new Q-table as app.py would
new_q_table = pd.read_csv(BASE_DIR / "rl_q_table.csv", index_col=0)

def get_rl_decision_new(risk_state, complexity):
    """New decision logic using risk_band (3-level) and complexity"""
    if risk_state not in new_q_table.index:
        return "Review"

    best_action = new_q_table.loc[risk_state].astype(float).idxmax()

    # Apply complexity override only for extreme cases
    if risk_state == "High":
        return "Investigate"
    if complexity == "High" and risk_state == "Medium":
        return "Review"

    return best_action

# Test decisions
decisions = []
for i in range(min(20, len(fraud_data))):
    row = fraud_data.iloc[i]
    decision = get_rl_decision_new(row["risk_band"], row["complexity"])
    decisions.append({
        "risk_band": row["risk_band"],
        "complexity": row["complexity"],
        "true_fraud": row["true_fraud"],
        "decision": decision
    })

for d in decisions:
    print(f"Risk: {d['risk_band']:6s} | Complexity: {d['complexity']:6s} | Fraud: {d['true_fraud']} | Decision: {d['decision']}")

print("\nTraining script completed successfully!")