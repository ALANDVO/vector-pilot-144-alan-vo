"""
cadgen: CAD generation utilities for text-to-cad.
"""

from cadgen.lazy import LazyModule

# Lazy submodules
flatten = LazyModule("cadgen.flatten")
unfold = LazyModule("cadgen.unfold")

__all__ = ["flatten", "unfold"]
