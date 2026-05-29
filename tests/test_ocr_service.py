from app.services.ocr_service import OCRService


def test_parse_paddleocr_result():
    result = [
        [
            [None, ("Hospital: General Medical Center", 0.93)],
            [None, ("Patient Name: Jane Doe", 0.87)],
        ]
    ]

    text, confidences = OCRService._parse_result(result)

    assert "Hospital: General Medical Center" in text
    assert "Patient Name: Jane Doe" in text
    assert confidences == [0.93, 0.87]


def test_parse_paddleocr_v3_dict_result():
    result = [
        {
            "res": {
                "rec_texts": ["Hospital: General Medical Center", "Patient Name: Jane Doe"],
                "rec_scores": [0.93, 0.87],
            }
        }
    ]

    text, confidences = OCRService._parse_result(result)

    assert "Hospital: General Medical Center" in text
    assert "Patient Name: Jane Doe" in text
    assert confidences == [0.93, 0.87]
