"""
FDA Food Ingredient and Packaging Inventories (FDCC) bulk export URLs.

SCOGS + GRAS Notices: CSV text files served as .xls (public domain, US government).
"""
from __future__ import annotations

FDA_FDCC_BASE = "https://www.hfpappexternal.fda.gov/scripts/fdcc"

SCOGS_DOWNLOAD_URL = f"{FDA_FDCC_BASE}/cfc/XMLService.cfm?method=downloadxls&set=SCOGS"
GRAS_NOTICES_DOWNLOAD_URL = f"{FDA_FDCC_BASE}/cfc/XMLService.cfm?method=downloadxls&set=GRASNotices"
