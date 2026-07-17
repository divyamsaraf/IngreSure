"""
FSSAI Food Safety and Standards regulations — bulk download URLs.

License: Public (Government of India).
"""
from __future__ import annotations

FSSAI_BASE = "https://fssai.gov.in/upload/uploadfiles/files"

# Appendix A: permitted food additives (INS/E-numbers) by food category
APPENDIX_A_PDF_URL = f"{FSSAI_BASE}/Appendix%20A(2).pdf"

# Full compendium (optional; large — use Appendix A for additive tables)
COMPENDIUM_ADDITIVES_PDF_URL = (
    "https://www.fssai.gov.in/upload/uploadfiles/files/"
    "Compendium_Food_Additives_Regulations_20_12_2022.pdf"
)
