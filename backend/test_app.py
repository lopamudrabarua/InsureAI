"""Focused API checks for document intake and risk band semantics."""
import io
import unittest
from unittest.mock import patch

from PIL import Image

from backend import app as service


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

    def test_risk_bands_use_configured_threshold_without_changing_state_rule(self):
        self.assertEqual(service.get_risk_band(service.FRAUD_THRESHOLD), "High")
        self.assertEqual(service.get_risk_band(service.FRAUD_THRESHOLD * 0.75), "Medium")
        self.assertEqual(service.get_risk_band(service.FRAUD_THRESHOLD * 0.25), "Low")
        self.assertEqual(service.get_risk_state(service.FRAUD_THRESHOLD * 0.75), "Low")


if __name__ == "__main__":
    unittest.main()
