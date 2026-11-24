"""Focused API checks for document intake and risk band semantics."""
import io
import unittest
from unittest.mock import patch

from PIL import Image

import app as service


class ClaimOcrApiTests(unittest.TestCase):
    def setUp(self):
        self.client = service.app.test_client()

    @staticmethod
    def image_bytes():
        image = Image.new("RGB", (40, 30), "white")
        output = io.BytesIO()
        image.save(output, format="PNG")
        return output.getvalue()

    def test_png_upload_returns_structured_ocr(self):
        with patch.object(service, "run_ocr", return_value=("Policy number: ABC12345", [0.95])):
            response = self.client.post(
                "/api/claims/ocr",
                data={"file": (io.BytesIO(self.image_bytes()), "claim.png")},
                content_type="multipart/form-data",
            )
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["status"], "success")
        self.assertEqual(body["claim_information"]["policy_number"], "ABC12345")
        self.assertEqual(body["pages_processed"], 1)

    def test_pdf_upload_processes_pages(self):
        document = service.fitz.open()
        document.new_page()
        document.new_page()
        payload = document.tobytes()
        document.close()
        with patch.object(service, "run_ocr", return_value=("Claim number: CLM123", [0.8])) as ocr:
            response = self.client.post(
                "/api/claims/ocr",
                data={"file": (io.BytesIO(payload), "claim.pdf")},
                content_type="multipart/form-data",
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["pages_processed"], 2)
        self.assertEqual(ocr.call_count, 2)

    def test_empty_ocr_and_invalid_format_are_reported(self):
        with patch.object(service, "run_ocr", return_value=("", [])):
            response = self.client.post(
                "/api/claims/ocr",
                data={"file": (io.BytesIO(self.image_bytes()), "claim.png")},
                content_type="multipart/form-data",
            )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.get_json()["status"], "error")
        response = self.client.post(
            "/api/claims/ocr",
            data={"file": (io.BytesIO(b"x"), "claim.exe")},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 400)

    def test_vehicle_claim_aliases_line_breaks_and_separate_identifiers(self):
        text = """VEHICLE CLAIM FORM
Name of insured
Aarav Sen
Policy No: EMA-MOTOR-2026-004821
Claim number / reference:
EMA-CLM-2026-009193
Claim Type - Own Damage
Date of loss: 2026-04-09
Vehicle damage description: Front bumper and right fender damaged
Repair required after inspection
Workshop name: North Garage
Repair garage address:
14 Lake Road, Pune
Maharashtra 411001
Surveyor: R. Mehta
Date of vehicle inspection: 10 Apr 2026
Vehicle release date: 2026-04-15
Total repair cost: INR 40,250.00
Invoice number: NGAR-EST-2026-00881
Member ID: EMA-MEM-2026-771904
Contact information: aarav.sen.sample@example.com"""
        fields, confidence, statuses, originals = service.structure_claim_text(text)
        self.assertEqual(fields["insured_person_name"], "Aarav Sen")
        self.assertEqual(fields["policy_number"], "EMA-MOTOR-2026-004821")
        self.assertEqual(fields["claim_number"], "EMA-CLM-2026-009193")
        self.assertNotEqual(fields["claim_number"], fields["invoice_number"])
        self.assertEqual(fields["claim_type"], "Own Damage")
        self.assertEqual(fields["incident_date"], "2026-04-09")
        self.assertEqual(fields["vehicle_release_date"], "2026-04-15")
        self.assertIn("right fender damaged Repair required", fields["vehicle_damage_description"])
        self.assertIn("Maharashtra 411001", fields["repair_garage_address"])
        self.assertEqual(fields["total_repair_estimate"], 40250.0)
        self.assertEqual(fields["vehicle_inspection_date"], "2026-04-10")
        self.assertEqual(fields["invoice_number"], "NGAR-EST-2026-00881")
        self.assertEqual(fields["member_id"], "EMA-MEM-2026-771904")
        self.assertEqual(fields["contact_information"], "aarav.sen.sample@example.com")
        self.assertEqual(statuses["claim_number"], "needs_review")
        self.assertEqual(statuses["surveyor_name"], "needs_review")
        self.assertIsNone(confidence["total_repair_estimate"])
        self.assertEqual(originals["total_repair_estimate"], "INR 40,250.00")

    def test_table_like_row_and_claim_aliases(self):
        text = "Claim ID: CLM-2026-0042 | Policy ID: POL-2026-0081\nAccident date - 09/04/2026\nRepairer: Eastside Auto Works\nEstimated claim amount: $12,345.50"
        fields, _, _, originals = service.structure_claim_text(text)
        self.assertEqual(fields["claim_number"], "CLM-2026-0042")
        self.assertEqual(fields["policy_number"], "POL-2026-0081")
        self.assertEqual(fields["incident_date"], "2026-04-09")
        self.assertEqual(fields["repair_garage_name"], "Eastside Auto Works")
        self.assertEqual(fields["amount_claimed"], 12345.5)
        self.assertEqual(originals["total_repair_estimate"], "$12,345.50")

    def test_pdf_text_is_extracted_and_vehicle_fields_returned(self):
        document = service.fitz.open()
        page = document.new_page()
        page.insert_text((72, 72), "Claim reference: CLM-2026-005\nInsured name: Aarav Sen\nAccident date: 2026-04-09\nRepair garage: North Garage")
        payload = document.tobytes()
        document.close()
        response = self.client.post(
            "/api/claims/ocr",
            data={"file": (io.BytesIO(payload), "vehicle.pdf")},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertIn("Claim reference", body["extracted_text"])
        self.assertEqual(body["claim_information"]["claim_number"], "CLM-2026-005")
        self.assertEqual(body["claim_information"]["incident_date"], "2026-04-09")
        self.assertEqual(body["extraction_status"]["vehicle_release_date"], "not_found")

    def test_risk_bands_use_configured_threshold_without_changing_state_rule(self):
        self.assertEqual(service.get_risk_band(service.FRAUD_THRESHOLD), "High")
        self.assertEqual(service.get_risk_band(service.FRAUD_THRESHOLD * 0.75), "Medium")
        self.assertEqual(service.get_risk_band(service.FRAUD_THRESHOLD * 0.25), "Low")
        self.assertEqual(service.get_risk_state(service.FRAUD_THRESHOLD * 0.75), "Low")


if __name__ == "__main__":
    unittest.main()
