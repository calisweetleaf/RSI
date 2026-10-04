# integration/__init__.py
"""
Integration Layer Package

Provides cross-system coordination between BioCognitive and Rosemary systems.
"""

from typing import TYPE_CHECKING

# Lazy imports to avoid circular dependencies
if TYPE_CHECKING:
    from .coordinator import BiocognitiveCoordinator
    from .gateway import IntegrationGateway, GatewayRouter, IntegrationMessage
    from .translator import TranslationEngine, TranslationContext, TranslationDirection
    from .enhanced_gateway import EnhancedGateway

__all__ = [
    "BiocognitiveCoordinator",
    "IntegrationGateway",
    "GatewayRouter",
    "IntegrationMessage",
    "TranslationEngine",
    "TranslationContext",
    "TranslationDirection",
    "EnhancedGateway",
]


def get_coordinator():
    """Lazy load coordinator to avoid import issues."""
    from .coordinator import BiocognitiveCoordinator
    return BiocognitiveCoordinator


def get_gateway():
    """Lazy load gateway to avoid import issues."""
    from .gateway import IntegrationGateway
    return IntegrationGateway


def get_translator():
    """Lazy load translator to avoid import issues."""
    from .translator import TranslationEngine
    return TranslationEngine
