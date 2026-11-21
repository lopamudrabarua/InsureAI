from flask import Flask, request, jsonify
from flask_cors import CORS

import pandas as pd
import numpy as np
import joblib
import os

# ==========================================
# INSUREAI - FLASK BACKEND
# ==========================================

app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# ==========================================
# LOAD IMPROVED FRAUD MODEL
# ==========================================

fraud_model = joblib.load(
    os.path.join(BASE_DIR, "fraud_model_improved.pkl")
)

with open(
    os.path.join(BASE_DIR, "fraud_threshold.txt"),
    "r"
) as file:
    FRAUD_THRESHOLD = float(file.read().strip())


# ==========================================
# LOAD SEGMENTED COST MODELS
# ==========================================

low_cost_model = joblib.load(
    os.path.join(BASE_DIR, "low_cost_model.pkl")
)

collision_cost_model = joblib.load(
    os.path.join(BASE_DIR, "collision_cost_model.pkl")
)

print("Segmented cost models loaded successfully!")


# ==========================================
# LOAD Q-TABLE
# ==========================================

q_table = pd.read_csv(
    os.path.join(BASE_DIR, "rl_q_table.csv"),
    index_col=0
)

print("InsureAI models loaded successfully!")
print("Improved fraud model loaded!")
print("Fraud threshold:", FRAUD_THRESHOLD)


# ==========================================
# MODEL INPUT FEATURES
# ==========================================

fraud_features = fraud_model.feature_names_in_.tolist()

# TransformedTargetRegressor wraps the original Pipeline.
# Access the fitted pipeline using regressor_.
cost_pipeline = low_cost_model.regressor_

cost_features = cost_pipeline.feature_names_in_.tolist()

# Make sure both segmented models expect the same features.
collision_features = (
    collision_cost_model.regressor_.feature_names_in_.tolist()
)

if cost_features != collision_features:
    raise ValueError(
        "Low-cost and collision models have different input features."
    )


# ==========================================
# HOME ROUTE
# ==========================================

@app.route("/", methods=["GET"])
def home():

    return jsonify({
        "status": "success",
        "message": "Welcome to InsureAI Backend!"
    })


# ==========================================
# PREPARE INPUT DATA
# ==========================================

def prepare_input(data, features, model):

    missing = [
        feature for feature in features
        if feature not in data
    ]

    if missing:
        raise ValueError(
            "Missing required fields: " + ", ".join(missing)
        )

    row = {
        feature: data[feature]
        for feature in features
    }

    df_input = pd.DataFrame(
        [row],
        columns=features
    )

    # Unwrap TransformedTargetRegressor if necessary.
    if hasattr(model, "regressor_"):
        pipeline = model.regressor_
    else:
        pipeline = model

    preprocessor = pipeline.named_steps["preprocessor"]

    for name, transformer, columns in preprocessor.transformers_:

        if name == "num":

            for column in columns:
                df_input[column] = pd.to_numeric(
                    df_input[column],
                    errors="coerce"
                )

        elif name == "cat":

            for column in columns:
                df_input[column] = df_input[column].map(
                    lambda value: (
                        str(value)
                        if pd.notna(value)
                        else np.nan
                    )
                )

    return df_input


# ==========================================
# CLAIM COMPLEXITY CALCULATION
# ==========================================

def calculate_complexity(data):

    score = 0

    severity = str(
        data.get("incident_severity", "")
    ).strip().lower()

    if severity in ["major damage", "total loss"]:
        score += 2

    elif severity == "minor damage":
        score += 1

    vehicles = pd.to_numeric(
        data.get("number_of_vehicles_involved", 0),
        errors="coerce"
    )

    injuries = pd.to_numeric(
        data.get("bodily_injuries", 0),
        errors="coerce"
    )

    witnesses = pd.to_numeric(
        data.get("witnesses", 0),
        errors="coerce"
    )

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

    police_report = str(
        data.get("police_report_available", "")
    ).strip().upper()

    if police_report == "YES":
        score += 1

    if score <= 2:
        return "Low"

    elif score <= 4:
        return "Medium"

    return "High"


# ==========================================
# FRAUD RISK LEVEL
# ==========================================

def get_risk_state(probability):

    if probability >= FRAUD_THRESHOLD:
        return "High"

    return "Low"


# ==========================================
# Q-TABLE DECISION
# ==========================================

def get_rl_decision(risk_state, complexity):

    if risk_state not in q_table.index:
        raise ValueError("Invalid risk state in Q-table")

    best_action = (
        q_table.loc[risk_state]
        .astype(float)
        .idxmax()
    )

    if risk_state == "High":
        return "Investigate"

    if complexity == "High":
        return "Review"

    return best_action


# ==========================================
# HEALTH CHECK
# ==========================================

@app.route("/api/health", methods=["GET"])
def health():

    return jsonify({
        "status": "success",
        "message": "InsureAI backend is running!",
        "fraud_model": "Improved Random Forest",
        "fraud_threshold": FRAUD_THRESHOLD,
        "cost_models": [
            "Low-cost model",
            "Collision model"
        ]
    })


# ==========================================
# CLAIM ANALYSIS API
# ==========================================

@app.route("/api/analyze", methods=["POST"])
def analyze_claim():

    try:

        data = request.get_json(silent=True)

        if not isinstance(data, dict):

            return jsonify({
                "status": "error",
                "message": "Please send valid JSON claim data."
            }), 400

        # 1. Prepare fraud model input
        fraud_input = prepare_input(
            data,
            fraud_features,
            fraud_model
        )

        # 2. Prepare cost model input
        cost_input = prepare_input(
            data,
            cost_features,
            low_cost_model
        )

        # 3. Predict fraud probability
        fraud_classes = list(fraud_model.classes_)

        if "Y" not in fraud_classes:
            raise ValueError(
                "Fraud class 'Y' was not found in the trained model."
            )

        fraud_index = fraud_classes.index("Y")

        fraud_probability = float(
            fraud_model.predict_proba(
                fraud_input
            )[0][fraud_index]
        )

        # 4. Select the correct cost model
        incident_type = data.get("incident_type")

        if incident_type in ["Vehicle Theft", "Parked Car"]:

            expected_cost = low_cost_model.predict(
                cost_input
            )[0]

        elif incident_type in [
            "Single Vehicle Collision",
            "Multi-vehicle Collision"
        ]:

            expected_cost = collision_cost_model.predict(
                cost_input
            )[0]

        else:

            return jsonify({
                "status": "error",
                "message": "Unsupported incident type for cost prediction."
            }), 400

        expected_cost = max(
            0,
            float(expected_cost)
        )

        # 5. Calculate claim complexity
        complexity = calculate_complexity(data)

        # 6. Determine fraud risk
        risk_state = get_risk_state(
            fraud_probability
        )

        # 7. Generate final decision
        decision = get_rl_decision(
            risk_state,
            complexity
        )

        # 8. Return complete analysis
        return jsonify({

            "status": "success",

            "fraud_probability": round(
                fraud_probability * 100,
                2
            ),

            "expected_cost": round(
                expected_cost,
                2
            ),

            "complexity": complexity,

            "risk_state": risk_state,

            "decision": decision

        })

    except ValueError as error:

        return jsonify({
            "status": "error",
            "message": str(error)
        }), 400

    except Exception:

        app.logger.exception(
            "Claim analysis failed"
        )

        return jsonify({
            "status": "error",
            "message": "Claim analysis failed. Please check the backend logs."
        }), 500


# ==========================================
# RUN FLASK SERVER
# ==========================================

if __name__ == "__main__":
    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )
