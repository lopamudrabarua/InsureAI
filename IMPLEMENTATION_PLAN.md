# InsureAI Implementation Plan

## Part 1: OCR Extraction Fixes (Urgent)

### Issue Analysis
The test at `backend/test_app.py:67-107` shows `surveyor_name` is "not_found" despite "Surveyor: R. Mehta" in text. Current aliases:
```python
"surveyor_name": ["surveyor name", "appointed surveyor", "surveyor", "loss assessor name"]
```

**Missing aliases causing extraction failures:**
- `surveyor_name`: "Surveyor:", "Loss assessor:", "Assessor:"
- `claim_type`: Need more variants for "Own Damage", "Third Party", etc.
- `vehicle_damage_description`: Handle multi-line descriptions better
- `repair_garage_address`: Multi-line address handling

### Fixes Required

1. **Expand aliases in `structure_claim_text()`** (`backend/app.py:96-111`)
   - Add colon variants: "Surveyor:", "Loss assessor:", "Assessor:"
   - Add "claim category", "nature of claim" for claim_type
   - Add "repairer:", "workshop:" for repair_garage_name
   - Ensure multiline extraction works for address and damage description

2. **Fix label pattern matching** (`backend/app.py:115-119`)
   - Current regex uses `(?<![\w])` and `(?![\w])` which may not handle colons well
   - Test with "Surveyor: R. Mehta" format

3. **Improve multiline extraction** (`backend/app.py:121-146`)
   - Better handling of labels and values on separate lines
   - Table/multi-column layout support

4. **Add field validation** - Don't confuse claim_number, policy_number, invoice_number

---

## Part 2: Frontend Terminology Correction

### Current State
- **OCR Review labels** (`script.js:1502-1511`): Already vehicle-specific ✓
- **Form sections** (`script.js:13-311`): Generic insurance terminology ✗

### Fields to Update in `formData` (`script.js`)

| Section | Current Field | Current Label | New Vehicle Label |
|---------|---------------|---------------|-------------------|
| Policyholder | `policyholder_name` (not in form) | - | Add "Policyholder name" |
| Policyholder | `insured_sex` | "Insured sex" | "Policyholder gender" |
| Policyholder | `insured_education_level` | "Education level" | "Policyholder education" |
| Policyholder | `insured_occupation` | "Occupation" | "Policyholder occupation" |
| Policyholder | `insured_hobbies` | "Hobbies" | Remove or "Vehicle usage" |
| Policyholder | `insured_relationship` | "Relationship" | "Policyholder relationship" |
| Policyholder | `capital-gains` | "Capital gains ($)" | Remove (health insurance) |
| Policyholder | `capital-loss` | "Capital loss ($)" | Remove (health insurance) |
| Incident | `incident_date` | "Incident date" | Keep ✓ |
| Incident | `incident_type` | "Incident type" | Keep ✓ |
| Incident | `collision_type` | "Collision type" | Keep ✓ |
| Incident | `incident_severity` | "Incident severity" | Keep ✓ |
| Financial | `total_claim_amount` | "Total claim amount ($)" | "Total claim amount (₹)" |
| Financial | `injury_claim` | "Injury claim ($)" | "Injury claim (₹)" |
| Financial | `property_claim` | "Property claim ($)" | "Property claim (₹)" |
| Financial | `vehicle_claim` | "Vehicle claim ($)" | "Vehicle claim (₹)" |
| Vehicle | All fields | Keep | Keep ✓ |

### Additional Frontend Changes
- Update currency formatting from USD to INR (`formatCurrency` in `script.js:383`)
- Update OCR field labels if any health terms remain
- Ensure form field mapping matches backend expectations

---

## Part 3: RL Implementation Enhancement

### Current RL (`backend/app.py:529-547`)
```python
def get_rl_decision(risk_state, complexity):
    best_action = q_table.loc[risk_state].astype(float).idxmax()
    if risk_state == "High": return "Investigate"
    if complexity == "High": return "Review"
    return best_action
```

### Issues
1. Hardcoded overrides bypass Q-table for High risk/complexity
2. Q-table is static CSV, not trained from data
3. No exploration/exploitation strategy
4. No integration with fraud probability or cost predictions

### Enhancement Plan

1. **Keep Q-table as decision lookup** but remove hardcoded overrides
2. **Add RL training script** (`backend/train_rl.py`) that:
   - Uses historical claim data (fraud_detection.xlsx)
   - Defines states: risk_band (Low/Medium/High) × complexity (Low/Medium/High)
   - Defines actions: Approve, Review, Investigate
   - Reward function: based on fraud detection accuracy + cost savings
   - Trains Q-table via Q-learning
   - Outputs updated `rl_q_table.csv`

3. **Integrate with analysis pipeline**:
   - Use `risk_band` (3-level) instead of `risk_state` (2-level) for state
   - Include expected cost in state representation
   - Log decisions for future retraining

---

## Part 4: Integration & Testing

### Files to Modify
1. `backend/app.py` - OCR aliases, RL decision logic
2. `script.js` - Form fields, currency, labels
3. `style.css` - No changes needed (responsive layout preserved)
4. `index.html` - No changes needed (structure preserved)

### New Files
1. `backend/train_rl.py` - RL training script
2. `backend/requirements.txt` - Add any RL dependencies

### Testing
1. Run existing tests: `python -m pytest backend/test_app.py -v`
2. Test OCR with sample PDF
3. Verify form submission works with new fields
4. Test RL decision output

---

## Priority Order
1. **OCR Fixes** (Part 1) - Urgent, blocking field extraction
2. **Frontend Terminology** (Part 2) - User-facing correctness
3. **RL Enhancement** (Part 3) - Core ML improvement
4. **Integration Testing** (Part 4) - Verify everything works