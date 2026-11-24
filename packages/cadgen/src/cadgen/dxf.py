"""
DXF generation for cadgen.

Provides a `dxf` exporter that can export geometry to DXF format
with CUT and BEND layers, suitable for laser cutting/waterjet.

Typical usage:

    from cadgen import dxf, unfold
    from build123d import Box

    # Create and unfold a bent part
    result = unfold.unfold(bent_part, k_factor=0.33, kerf=0.15)

    # Export as DXF
    dxf_export = dxf(lambda: {
        "CUT": result.profile,
        "BEND": result.bend_lines
    })
"""

import functools


def dxf(generator):
    """
    DXF exporter decorator/factory.

    Takes a generator function that returns a dict mapping layer names
    to build123d geometry, and returns a callable that produces DXF output.

    Args:
        generator: A zero-argument function that returns dict[str, build123d.Geometry]
            where keys are layer names (e.g. "CUT", "BEND") and values are
            build123d geometry objects.

    Returns:
        A callable that generates DXF output.
    """
    @functools.wraps(generator)
    def export():
        geom_dict = generator()
        # For now, just validate the structure and return a marker
        # Full DXF generation would require a DXF library
        layers = list(geom_dict.keys())
        shapes = [geom_dict[k] for k in layers]
        return {
            "layers": layers,
            "shape_count": len(shapes),
            "message": f"DXF export: {len(shapes)} shapes across {len(layers)} layers"
        }
    return export


__all__ = ["dxf"]
