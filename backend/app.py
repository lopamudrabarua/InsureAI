from flask import Flask, request, jsonify
from flask_cors import CORS

import pandas as pd
import numpy as np
import joblib
import os
import re
from datetime import datetime
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
    """Extract labelled vehicle-claim fields without crossing into adjacent fields."""
    lines = [re.sub(r"[\t\u00a0]+", " ", line).strip() for line in text.splitlines()]
    lines = [re.sub(r" {2,}", " ", line) for line in lines if line.strip()]

    aliases = {
        "policyholder_name": [
            "policyholder name", "policy holder name", "name of insured", "insured person's name",
            "insured person name", "insured name", "policyholder", "policy holder", "insured",
            "policyholder:", "policy holder:", "name of insured:", "insured name:", "insured:"
        ],
        "policy_number": [
            "policy number", "policy no", "policy #", "policy id",
            "policy number:", "policy no:", "policy #:", "policy id:"
        ],
        "claim_number": [
            "claim number / reference", "claim reference number", "claim number", "claim no",
            "claim #", "claim id", "claim reference", "claim / reference", "claim ref",
            "claim number:", "claim reference:", "claim no:", "claim #:", "claim id:", "claim ref:"
        ],
        "member_id": ["member id", "member number", "member no", "member id:", "member number:", "member no:"],
        "claim_type": [
            "claim type", "type of claim", "claim category", "nature of claim",
            "claim type:", "type of claim:", "claim category:", "nature of claim:"
        ],
        "incident_date": [
            "incident date", "accident date", "date of accident", "date of loss",
            "accident / loss date", "loss date", "incident date:", "accident date:",
            "date of accident:", "date of loss:", "loss date:"
        ],
        "vehicle_release_date": [
            "vehicle release date", "release date", "date vehicle released",
            "vehicle release date:", "release date:", "date vehicle released:"
        ],
        "vehicle_damage_description": [
            "vehicle damage description", "damage description", "description of damage",
            "vehicle damage", "damage to vehicle", "vehicle damage description:",
            "damage description:", "description of damage:", "vehicle damage:",
            "damage to vehicle:"
        ],
        "surveyor_name": [
            "surveyor name", "appointed surveyor", "surveyor", "loss assessor name",
            "surveyor:", "appointed surveyor:", "surveyor name:", "loss assessor:",
            "loss assessor name:", "assessor:", "assessor name:"
        ],
        "repair_garage_name": [
            "repair garage name", "garage name", "workshop name", "repairer name",
            "repair garage", "repairer", "workshop", "repair garage name:",
            "garage name:", "workshop name:", "repairer name:", "repair garage:",
            "repairer:", "workshop:"
        ],
        "repair_garage_address": [
            "repair garage address", "garage address", "workshop address", "repairer address",
            "repair garage address:", "garage address:", "workshop address:",
            "repairer address:"
        ],
        "total_repair_estimate": [
            "total repair estimate", "total repair cost", "estimated repair cost",
            "repair estimate", "amount claimed", "estimated claim amount", "claim amount",
            "total repair estimate:", "total repair cost:", "estimated repair cost:",
            "repair estimate:", "amount claimed:", "estimated claim amount:", "claim amount:"
        ],
        "vehicle_inspection_date": [
            "date of vehicle inspection", "vehicle inspection date", "inspection date",
            "date inspected", "survey date", "date of vehicle inspection:",
            "vehicle inspection date:", "inspection date:", "date inspected:",
            "survey date:"
        ],
        "invoice_number": [
            "invoice number", "invoice no", "invoice #", "bill number", "bill no", "bill #",
            "invoice number:", "invoice no:", "invoice #:", "bill number:",
            "bill no:", "bill #:"
        ],
    }
    normalized_aliases = {key: sorted(set(value), key=len, reverse=True) for key, value in aliases.items()}
    all_aliases = sorted({alias for group in normalized_aliases.values() for alias in group}, key=len, reverse=True)

    def alias_pattern(items):
        return re.compile(r"(?<![\w])(?:" + "|".join(re.escape(alias).replace(r"\ ", r"\s+") for alias in items) + r")(?![\w])", re.I)

    label_pattern = alias_pattern(all_aliases)
    field_patterns = {key: alias_pattern(value) for key, value in normalized_aliases.items()}

    def extract_labelled(key, multiline=False):
        pattern = field_patterns[key]
        for line_index, line in enumerate(lines):
            match = pattern.search(line)
            if not match:
                continue
            value = line[match.end():].lstrip(" \t:#=–—-/").strip(" \t:;,.|-")
            if not value and line_index + 1 < len(lines):
                next_line = lines[line_index + 1]
                if not label_pattern.search(next_line):
                    value = next_line.strip(" \t:#=–—-/;,.|")
                    line_index += 1
            if value:
                next_label = label_pattern.search(value)
                if next_label:
                    value = value[:next_label.start()].strip(" \t:#=–—-/;,.|")
            parts = [value] if value else []
            if multiline:
                for following in lines[line_index + 1:]:
                    if label_pattern.search(following):
                        break
                    parts.append(following.strip())
            value = " ".join(part for part in parts if part).strip(" \t:#=–—-/;,.|")
            if value:
                return value
        return ""

    def identifier(value):
        value = re.sub(r"\s+", "", value)
        return value if re.fullmatch(r"[A-Z0-9][A-Z0-9./_-]{2,49}", value, re.I) else ""

    def parse_date(value):
        match = re.search(r"\b\d{1,4}[./-]\d{1,2}[./-]\d{2,4}\b|\b\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}\b", value)
        if not match:
            return ""
        raw = match.group(0)
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%d %b %Y", "%d %B %Y"):
            try:
                parsed = datetime.strptime(raw, fmt).date()
                return parsed.isoformat() if 1900 <= parsed.year <= 2100 else ""
            except ValueError:
                continue
        return ""

    def parse_money(value):
        match = re.search(r"(?<!\w)(?:INR|Rs\.?|₹|\$|USD|EUR|€|GBP|£)?\s*([\d,]+(?:\.\d{1,2})?)(?!\w)", value, re.I)
        if not match:
            return "", ""
        try:
            amount = round(float(match.group(1).replace(",", "")), 2)
        except ValueError:
            return "", ""
        original = match.group(0).strip()
        return amount, original

    raw_values = {key: extract_labelled(key, multiline=key in {"vehicle_damage_description", "repair_garage_address"}) for key in aliases}
    fields = {
        "policyholder_name": raw_values["policyholder_name"],
        "insured_person_name": raw_values["policyholder_name"],
        "policy_number": identifier(raw_values["policy_number"]),
        "claim_number": identifier(raw_values["claim_number"]),
        "member_id": identifier(raw_values["member_id"]),
        "contact_information": "",
        "claim_type": raw_values["claim_type"],
        "incident_date": parse_date(raw_values["incident_date"]),
        "vehicle_release_date": parse_date(raw_values["vehicle_release_date"]),
        "vehicle_damage_description": raw_values["vehicle_damage_description"],
        "surveyor_name": raw_values["surveyor_name"],
        "repair_garage_name": raw_values["repair_garage_name"],
        "repair_garage_address": raw_values["repair_garage_address"],
        "vehicle_inspection_date": parse_date(raw_values["vehicle_inspection_date"]),
        "invoice_number": identifier(raw_values["invoice_number"]),
    }
    fields["amount_claimed"], amount_original = parse_money(raw_values["total_repair_estimate"])
    fields["total_repair_estimate"] = fields["amount_claimed"]
    email = re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text)
    phone = re.search(r"(?<!\w)\+?\d[\d ()-]{7,}\d(?!\w)", text)
    digits = re.sub(r"\D", "", phone.group(0)) if phone else ""
    fields["contact_information"] = email.group(0) if email else (phone.group(0).strip() if 10 <= len(digits) <= 15 else "")

    # Preserve normalized values for existing consumers, and retain source spelling/currency for audit.
    original_values = {key: value for key, value in raw_values.items() if value}
    if amount_original:
        original_values["total_repair_estimate"] = amount_original
        original_values["amount_claimed"] = amount_original
    original_values.update({key: fields[key] for key in ("incident_date", "vehicle_release_date", "vehicle_inspection_date") if fields[key]})
    confidence = {key: None for key in fields}
    statuses = {key: ("needs_review" if value not in ("", None) else "not_found") for key, value in fields.items()}
    return fields, confidence, statuses, original_values


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
        fields, field_confidence, field_status, original_values = structure_claim_text(extracted_text)
        return jsonify({"status": "success", "extracted_text": extracted_text,
                        "claim_information": fields, "confidence_scores": field_confidence,
                        "extraction_status": field_status, "original_values": original_values,
                        "ocr_confidence": round(sum(scores) / len(scores), 3) if scores else None,
                        "fields_requiring_verification": [key for key, value in fields.items() if value not in ("", None)],
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

# Default values for legacy fields removed from the vehicle-insurance frontend
LEGACY_FIELD_DEFAULTS = {
    "insured_hobbies": "driving",
    "capital-gains": 0,
    "capital-loss": 0,
}


def prepare_input(data, features, model):

    row = {}
    for feature in features:
        if feature in data:
            row[feature] = data[feature]
        elif feature in LEGACY_FIELD_DEFAULTS:
            row[feature] = LEGACY_FIELD_DEFAULTS[feature]
        else:
            raise ValueError(f"Missing required field: {feature}")

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
    """
    Determine claim decision using trained Q-table.

    Uses risk_band (Low/Medium/High) and complexity (Low/Medium/High)
    to look up the optimal action from the Q-table trained via
    Q-learning on historical claim data.
    """
    # Use risk_band (3-level) for Q-table lookup
    if risk_state not in q_table.index:
        # Fallback for any unexpected risk state
        return "Review"

    best_action = (
        q_table.loc[risk_state]
        .astype(float)
        .idxmax()
    )

    # Apply domain-informed overrides only for clear-cut cases
    # High fraud risk always warrants investigation
    if risk_state == "High":
        return "Investigate"

    # Medium risk + high complexity warrants review
    if risk_state == "Medium" and complexity == "High":
        return "Review"

    # Otherwise trust the learned Q-table policy
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
        risk_band = get_risk_band(fraud_probability)
        # Keep legacy risk_state for backward compatibility
        risk_state = get_risk_state(fraud_probability)

        # 7. Generate final decision
        # Use risk_band (3-level: Low/Medium/High) for Q-table lookup
        decision = get_rl_decision(
            risk_band,
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
