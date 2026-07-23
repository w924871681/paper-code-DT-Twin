"""Public reporting API.

``generate`` is the released, weight-free Level-B entry point. Final
Fig. 6--12 live only in :mod:`reporting.final_figures`; archived plotting
implementations live under :mod:`reporting.legacy`.
"""

from .frozen import generate

__all__ = ["generate"]
