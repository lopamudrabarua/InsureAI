from flask import Flask, request, jsonify
from flask_cors import CORS

import pandas as pd
import numpy as np
import joblib
import os
import re
from pathlib import Path
import shutil
from io import BytesIO

from werkzeug.utils import secure_filename
from PIL import Image, ImageChops, ImageEnhance, ImageFilter, ImageOps, UnidentifiedImageError
import pytesseract
from pytesseract import Output

try:
    import fitz
except Exception:
    fitz = None

# ==========================================
# INSUREAI - FLASK BACKEND
# ==========================================

app = Flask(__name__)
cors_origins = [
    origin.strip().rstrip("/")
    for origin in os.environ.get(
        "INSUREAI_FRONTEND_ORIGINS",
        "http://localhost:8000,http://127.0.0.1:8000",
    ).split(",")
    if origin.strip()
]
if any("*" in origin for origin in cors_origins):
    raise RuntimeError("INSUREAI_FRONTEND_ORIGINS must list exact origins; wildcard CORS is disabled.")
CORS(app, resources={r"/api/*": {"origins": cors_origins}}, supports_credentials=False)
app.config["MAX_CONTENT_LENGTH"] = 12 * 1024 * 1024

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OCR_EXTENSIONS = {"jpg", "jpeg", "png", "pdf"}
MAX_IMAGE_PIXELS = 20_000_000
OCR_TIMEOUT_SECONDS = 30


def preprocess_image(image):
    """Return a cleaned, high-contrast grayscale image suitable for Tesseract."""
    gray = ImageOps.grayscale(image)
    gray = ImageOps.autocontrast(gray, cutoff=1)
    gray = ImageEnhance.Contrast(gray).enhance(1.35)
    gray = gray.filter(ImageFilter.MedianFilter(size=3))
    local_background = gray.filter(ImageFilter.BoxBlur(radius=15))
    local_contrast = ImageChops.subtract(gray, local_background, offset=128)
    return local_contrast.point(lambda pixel: 255 if pixel > 120 else 0, mode="1")


def run_ocr(image):
    """Extract text and per-word confidence in one Tesseract invocation."""
    data = pytesseract.image_to_data(
        preprocess_image(image),
        lang="eng",
        config="--oem 3 --psm 6",
        output_type=Output.DICT,
        timeout=OCR_TIMEOUT_SECONDS,
    )
    grouped_lines = {}
    scores = []
    for index, word in enumerate(data.get("text", [])):
        word = word.strip()
        if not word:
            continue
        line_key = (
            data["page_num"][index],
            data["block_num"][index],
            data["par_num"][index],
            data["line_num"][index],
        )
        grouped_lines.setdefault(line_key, []).append(word)
        try:
            confidence = float(data["conf"][index])
            if confidence >= 0:
                scores.append(confidence / 100)
        except (TypeError, ValueError):
            pass
    text = "\n".join(" ".join(words) for words in grouped_lines.values())
    return text, scores


def structure_claim_text(text):
    patterns = {
        "claimant_name": [r"(?:(?:patient|claimant|insured|customer)(?:\s+name)?|name)\s*[:#-]?\s*([A-Z][A-Za-z .'-]{2,})"],
        "policy_number": [r"(?:policy(?:\s*(?:no|number))?)\s*[:#-]?\s*([A-Z0-9/-]{4,})"],
        "claim_number": [r"(?:claim\s*(?:no\.?|number|#)|claim\s+id)\s*[:#-]?\s*([A-Z0-9/-]{3,})"],
        "hospital_workshop_name": [r"(?:hospital|workshop|garage|clinic)(?:\s+name)?\s*[:#-]?\s*([A-Z][A-Za-z0-9 &'.,-]{2,})"],
        "invoice_number": [r"(?:invoice(?:\s*(?:no\.?|number|#))?|bill(?:\s*(?:no\.?|number|#)|(?=\s*[:#-])))\s*[:#-]?\s*([A-Z0-9/-]{3,})"],
        "incident_date": [r"(?:date of (?:incident|accident)|incident date)\s*[:#-]?\s*([0-9]{1,4}[./-][0-9]{1,2}[./-][0-9]{1,4})"],
        "treatment_repair_date": [r"(?:date of (?:treatment|repair)|treatment date|repair date)\s*[:#-]?\s*([0-9]{1,4}[./-][0-9]{1,2}[./-][0-9]{1,4})"],
        "claim_amount": [r"(?:claim amount|amount claimed)\s*[:#-]?\s*(?:[$₹])?\s*([\d,]+(?:\.\d{1,2})?)"],
        "total_bill_amount": [r"(?:grand total|total bill amount|total bill|total amount|amount due)\s*[:#-]?\s*(?:[$₹])?\s*([\d,]+(?:\.\d{1,2})?)"],
        "description_of_incident": [r"(?:incident description|description of incident|accident details)\s*[:#-]?\s*(.{5,180})"],
        "contact_information": [r"(?:\+?\d[\d ()-]{7,}\d|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,})"]
    }
    fields, confidence = {}, {}
    for field, expressions in patterns.items():
        if field == "contact_information":
            email = re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text)
            phone = re.search(r"\+?\d[\d ()-]{7,}\d", text)
            phone_digits = re.sub(r"\D", "", phone.group(0)) if phone else ""
            value = email.group(0) if email else (phone.group(0) if 10 <= len(phone_digits) <= 15 else None)
            fields[field] = value
            confidence[field] = None
            continue
        match = next((m for pattern in expressions if (m := re.search(pattern, text, re.I | re.M))), None)
        value = match.group(1).strip(" .,:;\n") if match and match.lastindex else (match.group(0).strip() if match else None)
        fields[field] = value
        confidence[field] = None
    for field in ("claim_amount", "total_bill_amount"):
        if fields[field]:
            fields[field] = float(fields[field].replace(",", ""))
    return fields, confidence


@app.errorhandler(413)
def too_large(_error):
    return jsonify({"status": "error", "message": "File exceeds the 12 MB upload limit."}), 413


@app.route("/api/claims/ocr", methods=["POST"])
def ocr_claim_document():
    upload = request.files.get("file")
    if not upload or not upload.filename:
        return jsonify({"status": "error", "message": "Choose an image or PDF to process."}), 400
    filename = secure_filename(upload.filename)
    extension = Path(filename).suffix.lower().lstrip(".")
    if extension not in OCR_EXTENSIONS:
        return jsonify({"status": "error", "message": "Supported formats are JPG, JPEG, PNG, and PDF."}), 400
    try:
        payload = upload.read()
        if not payload:
            return jsonify({"status": "error", "message": "The uploaded file is empty."}), 400
        lines, scores = [], []
        page_count = 1
        if extension == "pdf":
            if fitz is None:
                raise RuntimeError("PDF support is unavailable. Install PyMuPDF from requirements.txt.")
            try:
                document = fitz.open(stream=payload, filetype="pdf")
            except Exception:
                return jsonify({"status": "error", "message": "The PDF is invalid, damaged, or encrypted."}), 400
            if document.page_count > 20:
                return jsonify({"status": "error", "message": "PDFs may contain at most 20 pages."}), 400
            page_count = document.page_count
            if page_count == 0:
                return jsonify({"status": "error", "message": "The PDF contains no pages."}), 400
            for page in document:
                embedded_text = page.get_text("text").strip()
                if embedded_text:
                    lines.append(embedded_text)
                    continue
                largest_pt = max(page.rect.width, page.rect.height)
                scale = min(2.0, 3500 / max(largest_pt, 1))
                pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
                with Image.open(BytesIO(pixmap.tobytes("png"))) as page_image:
                    page_image = page_image.convert("RGB")
                    page_text, page_scores = run_ocr(page_image)
                    if page_text:
                        lines.append(page_text)
                    scores.extend(page_scores)
        else:
            try:
                image = Image.open(BytesIO(payload))
                actual_format = (image.format or "").lower()
                expected_formats = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png"}
                if actual_format != expected_formats[extension]:
                    return jsonify({"status": "error", "message": "The file contents do not match the selected image format."}), 400
                if image.width * image.height > MAX_IMAGE_PIXELS:
                    image.close()
                    return jsonify({"status": "error", "message": "Image dimensions exceed the 20-megapixel processing limit."}), 400
                image.load()
                image = ImageOps.exif_transpose(image).convert("RGB")
            except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
                return jsonify({"status": "error", "message": "The image could not be decoded."}), 400
            if image.width * image.height > MAX_IMAGE_PIXELS:
                return jsonify({"status": "error", "message": "Image dimensions exceed the 20-megapixel processing limit."}), 400
            image_text, scores = run_ocr(image)
            if image_text:
                lines.append(image_text)
        extracted_text = "\n".join(lines).strip()
        if not extracted_text:
            return jsonify({"status": "error", "message": "No readable text was found. Try a clearer image or enter claim details manually."}), 422
        fields, field_confidence = structure_claim_text(extracted_text)
        return jsonify({"status": "success", "extracted_text": extracted_text,
                        "claim_information": fields, "confidence_scores": field_confidence,
                        "ocr_confidence": round(sum(scores) / len(scores), 3) if scores else None,
                        "fields_requiring_verification": list(fields.keys()),
                        "pages_processed": page_count})
    except pytesseract.TesseractNotFoundError:
        return jsonify({"status": "error", "message": "Tesseract is not installed on the backend. Install the tesseract-ocr system package."}), 503
    except pytesseract.TesseractError:
        app.logger.exception("Tesseract OCR failed")
        return jsonify({"status": "error", "message": "Tesseract could not process this document. Try a clearer file."}), 422
    except RuntimeError as error:
        return jsonify({"status": "error", "message": str(error)}), 503
    except Exception:
        app.logger.exception("Claim document OCR failed")
        return jsonify({"status": "error", "message": "Document processing failed. Check file readability and try again."}), 500


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


def get_risk_band(probability):
    """Expose a three-band view while retaining the trained model threshold."""
    if probability >= FRAUD_THRESHOLD:
        return "High"
    if probability >= FRAUD_THRESHOLD * 0.5:
        return "Medium"
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
        "ocr_dependencies_available": bool(shutil.which("tesseract")) and fitz is not None,
        "ocr_engine": "Tesseract OCR",
        "ocr_model_downloads": False,
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
        risk_band = get_risk_band(fraud_probability)

        # 7. Generate final decision
        decision = get_rl_decision(
            risk_state,
            complexity
        )

        # 8. Return complete analysis
        probability_percent = round(fraud_probability * 100, 2)
        explanations = [
            f"The trained model estimated a {probability_percent:.2f}% fraud probability; its configured high-risk threshold is {FRAUD_THRESHOLD * 100:.2f}%.",
            "The probability is a model estimate based on the submitted structured claim fields, not a verified finding.",
        ]
        if complexity == "High":
            explanations.append("The claim has high incident complexity and should receive human review.")
        explanations.append("Policy, provider, and duplicate-claim records were not checked against external sources.")

        return jsonify({

            "status": "success",

            "fraud_probability": probability_percent,

            "expected_cost": round(
                expected_cost,
                2
            ),

            "complexity": complexity,

            "risk_state": risk_state,

            "risk_band": risk_band,

            "manual_verification_required": decision in ["Review", "Investigate"] or risk_band == "Medium",

            "indicators": [
                f"Model probability: {probability_percent:.2f}%",
                f"Incident complexity: {complexity}",
            ],

            "explanations": explanations,

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
        debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "5000")),
    )
