from paddleocr import PaddleOCR
import numpy as np
from PIL import Image
import logging

logger = logging.getLogger(__name__)

class OCREngine:
    def __init__(self):
        # Initialize PaddleOCR (English)
        # use_angle_cls=True enables orientation correction
        logger.info("Loading PaddleOCR model...")
        self.ocr = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)

    def extract_text(self, image_bytes: bytes) -> str:
        """
        Extracts text from image bytes.
        """
        try:
            # Convert bytes to numpy array for PaddleOCR
            # 1. Open image with PIL
            from io import BytesIO
            img = Image.open(BytesIO(image_bytes)).convert('RGB')
            img_np = np.array(img)

            # 2. Run OCR
            result = self.ocr.ocr(img_np, cls=True)
            
            # 3. Parse result
            # Result structure: [[[[x1,y1],[x2,y2]...], ("text", confidence)], ...]
            full_text = []
            if result and result[0]:
                for line in result[0]:
                    text = line[1][0]
                    full_text.append(text)
            
            return "\n".join(full_text)

        except Exception as e:
            logger.error(f"OCR Failed: {e}")
            return ""
