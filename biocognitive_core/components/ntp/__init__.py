"""
Neural Transparency Protocol (NTP) Component.

This package implements the NTP component of the biocognitive framework,
which provides secure bidirectional brain-computer interfaces enabling
thought transmission.
"""

from __future__ import annotations

import logging
import os
from typing import List

logger = logging.getLogger(__name__)

__all__: List[str] = []


def _safe_import(module_name: str, symbols: List[str]) -> None:
    try:
        module = __import__(f"{__name__}.{module_name}", fromlist=symbols)
    except Exception as exc:
        logger.warning("NTP %s import skipped: %s", module_name, exc)
        return
    for symbol in symbols:
        if hasattr(module, symbol):
            globals()[symbol] = getattr(module, symbol)
            __all__.append(symbol)
        else:
            logger.warning("NTP %s missing symbol: %s", module_name, symbol)


_safe_import("encryption", ["QuantumSecureSignalProcessor", "QuantumEncryption"])

# ConsentManagementEngine is always eagerly exported — receiver.py depends on it unconditionally
_safe_import(
    "consent",
    [
        "ConsentLevel",
        "ConsentDomain",
        "ConsentStatus",
        "ConsentScope",
        "ConsentRecord",
        "ConsentManagementEngine",
        "InMemoryConsentRepository",
    ],
)

if os.getenv("BIOC_NTP_IMPORT_ALL") == "1":
    _safe_import(
        "interface",
        [
            "ThoughtDomain",
            "NeuralSignal",
            "ThoughtPacket",
            "TransmissionProfile",
            "NeuralInterface",
            "BreathPhaseSync",
            "DreamPhaseIntegration",
        ],
    )
    _safe_import(
        "receiver",
        [
            "NeuralReceiver",
            "ReceiverMode",
            "SignalQuality",
            "ThoughtDecoder",
            "TransparencySession",
        ],
    )
    _safe_import(
        "arfs_aware_reciever",
        [
            "ARFSAwareReceiver",
            "ARFSPacket",
            "ARFSSignalType",
            "create_arfs_aware_receiver",
        ],
    )


def initialize_ntp() -> bool:
    """Initialize NTP component and verify correct setup."""
    from biocognitive_core.metrics import NTPMetrics

    metrics = NTPMetrics()
    metrics.initialize_collectors()
    return True


if os.getenv("BIOC_NTP_VALIDATE_IMPORT") == "1":
    initialize_ntp()
