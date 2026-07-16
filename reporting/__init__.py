"""Public reporting API.

``generate`` is the released, weight-free Level-B entry point.  The historical
``reporting.reporting`` module remains importable for archived workflows.
"""

from .frozen import generate

__all__ = ["generate"]
