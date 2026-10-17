"""New-source adapters for IKE-2 bulk ingestion (Item 1 / Item 17 strangler-fig).

Existing Layer-1 transforms (USDA, OFF, …) are **not** migrated here.
Only produce / animal / INFOODS / future licensed feeds implement ``SourceAdapter``.
"""

from core.knowledge.ike2.etl.adapters.animal import AnimalCatalogAdapter
from core.knowledge.ike2.etl.adapters.animal import write_layer1_dump as write_animal_layer1_dump
from core.knowledge.ike2.etl.adapters.infoods_anfood import InfoodsAnfoodAdapter
from core.knowledge.ike2.etl.adapters.infoods_anfood import (
    write_layer1_dump as write_infoods_layer1_dump,
)
from core.knowledge.ike2.etl.adapters.produce import ProduceCatalogAdapter
from core.knowledge.ike2.etl.adapters.produce import write_layer1_dump as write_produce_layer1_dump
from core.knowledge.ike2.etl.adapters.protocol import SourceAdapter, emit_layer1_records

__all__ = [
    "SourceAdapter",
    "emit_layer1_records",
    "ProduceCatalogAdapter",
    "AnimalCatalogAdapter",
    "InfoodsAnfoodAdapter",
    "write_produce_layer1_dump",
    "write_animal_layer1_dump",
    "write_infoods_layer1_dump",
]

# Back-compat alias used by produce tests / operators
write_layer1_dump = write_produce_layer1_dump

