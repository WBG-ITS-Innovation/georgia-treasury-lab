import easyocr

class OCRSkill:
    def __init__(self):
        self.reader = easyocr.Reader(['en'], gpu=False)

    def extract_text(self, image_path: str) -> str:
        try:
            results = self.reader.readtext(image_path, detail=0)
            return " ".join(results).strip()
        except Exception as e:
            return f"OCR error: {str(e)}"
