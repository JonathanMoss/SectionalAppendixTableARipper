""" Custom implementation of EasyOCR for use with img2table"""

# pylint: disable=W0102, E0401, C0103 W0235, C0116, R0903

from typing import List, Tuple, Dict
from img2table.ocr import EasyOCR
from img2table.document.base import Document

class EasyOcrCustom(EasyOCR):
    """ EasyOCR object"""

    def __init__(self, lang: List[str] = ['en'], kw: Dict = None):
        super().__init__(lang, kw)

    def content(self, document: Document) -> List[List[Tuple]]:
        # Get OCR of all images
        ocrs = [self.reader.readtext(
            image,
            width_ths=0.9,
            batch_size=10
        ) for image in document.images]

        return ocrs
