"""
Self-evolving ontology: unknown ingredients log and dynamic ontology management.
"""
from .unknown_log import UnknownIngredientsLog, log_unknown_ingredient, get_unknown_log
from .dynamic_ontology import DynamicOntology, load_dynamic_ontology, append_to_dynamic_ontology

__all__ = [
    "UnknownIngredientsLog",
    "log_unknown_ingredient",
    "get_unknown_log",
    "DynamicOntology",
    "load_dynamic_ontology",
    "append_to_dynamic_ontology",
]
