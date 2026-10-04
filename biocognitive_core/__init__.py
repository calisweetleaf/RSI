# biocognitive_core/__init__.py
"""
BioCognitive Core Package

Core framework for the BioCognitive AI system including:
- SIS: Synthetic Immune Symbiont
- NTP: Neural Transparency Protocol  
- SECT: Self-Evolving Cognitive Therapist
"""

from .config import settings, get_settings
from .exceptions import BiocognitiveError
from .metrics import SISMetrics, NTPMetrics, SECTMetrics

__all__ = [
    'settings',
    'get_settings',
    'BiocognitiveError',
    'SISMetrics',
    'NTPMetrics',
    'SECTMetrics',
]
