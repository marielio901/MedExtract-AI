from app.services.extraction_service import ExtractionService
from app.services.billing_statement_cv_service import BillingStatementCVService


class DummyConfig:
    AI_CONFIDENCE_THRESHOLD = 0.72


class DummyAIService:
    enabled = False


def test_regex_extraction_returns_valid_medical_payload():
    service = ExtractionService.__new__(ExtractionService)
    service.config = DummyConfig()
    service.ai_service = DummyAIService()

    text = """
    Hospital: General Medical Center
    Patient Name: Jane Doe
    MRN: A12345
    DOB: 01/20/1980
    Admission Diagnosis: Pneumonia
    ICD-10: J18.9
    Discharge Medications: Amoxicillin; Ibuprofen
    Physician: Dr. Smith
    """

    payload = service.extract_structured_data(
        raw_text=text,
        source_file_name="summary.pdf",
        source_file_type="pdf",
        ocr_confidence=0.91,
    )

    assert payload["hospital_name"] == "General Medical Center"
    assert payload["patient_name"] == "Jane Doe"
    assert payload["icd10_code"] == "J18.9"
    assert payload["extraction_status"] == "validated"


def test_regex_extraction_reads_patient_account_statement():
    service = ExtractionService.__new__(ExtractionService)
    service.config = DummyConfig()
    service.ai_service = DummyAIService()

    text = """
    Lilavati Hospital
    Bandra Reclamation, Mumbai, Maharashtra 400050
    NPI: 1482950384 | Phone: (555) 019-8372

    PATIENT ACCOUNT STATEMENT
    Statement Date: 05/22/2026
    Guarantor No: MRN-1039485
    Patient Name: Amit Singh
    Date of Birth: 1978-11-03
    Primary Insurance: HDFC ERGO General Insurance
    Group No: GRP-2960
    Primary Diagnosis: Hyperlipidemia
    ICD-10 Code: E78.5

    Date CPT Description Charges
    05/22/2026 0260 IV Therapy $243.00
    05/22/2026 99283 Emergency Room Level 3 $801.00
    05/22/2026 36415 Venipuncture $15.00

    Total Billed Charges: $1508.00
    Insurance Adjustments: -$1309.00
    Patient Amount Due: $199.00
    """

    payload = service.extract_structured_data(
        raw_text=text,
        source_file_name="statement.pdf",
        source_file_type="pdf",
        ocr_confidence=0.95,
    )

    assert payload["hospital_name"] == "Lilavati Hospital"
    assert payload["hospital_npi"] == "1482950384"
    assert payload["patient_name"] == "Amit Singh"
    assert payload["document_type"] == "billing_statement"
    assert payload["guarantor_no"] == "MRN-1039485"
    assert payload["primary_insurance"] == "HDFC ERGO General Insurance"
    assert payload["primary_diagnosis"] == "Hyperlipidemia"
    assert payload["icd10_code"] == "E78.5"
    assert payload["patient_amount_due"] == 199.0
    assert payload["extraction_confidence"] >= 0.95
    assert payload["billing_items"][1]["cpt"] == "99283"


def test_cv_bill_parser_reads_table_lines_and_money():
    table_text = """
    Date CPT Description Charges
    05/22/2026
    93000
    Electrocardiogram, Routine ECG
    $55.00
    05/22/2026
    80048
    Basic Metabolic Panel (BMP)
    $51.00
    """
    totals_text = """
    Total Billed Charges: $106.00
    Insurance Adjustments:
    NTIAL
    -$83.00
    PATIENT AMOUNT DUE:
    $23.00
    """

    items = BillingStatementCVService._billing_items(table_text)

    assert items == [
        {
            "date": "05/22/2026",
            "cpt": "93000",
            "description": "Electrocardiogram, Routine ECG",
            "charges": 55.0,
        },
        {
            "date": "05/22/2026",
            "cpt": "80048",
            "description": "Basic Metabolic Panel (BMP)",
            "charges": 51.0,
        },
    ]
    assert BillingStatementCVService._money(totals_text, "Total Billed Charges") == 106.0
    assert BillingStatementCVService._money(totals_text, "Insurance Adjustments") == -83.0
    assert BillingStatementCVService._money(totals_text, "Patient Amount Due") == 23.0
