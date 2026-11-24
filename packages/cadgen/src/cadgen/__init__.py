"""
cadgen: CAD generation utilities for text-to-cad.
"""

from cadgen.lazy import LazyModule

# Lazy submodules
flatten = LazyModule("cadgen.flatten")
unfold = LazyModule("cadgen.unfold")

# dxf is a regular function (not lazy), imported directly
from cadgen.dxf import dxf

__all__ = ["flatten", "unfold", "dxf"]
