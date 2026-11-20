# Skills

This project provides CAD generation utilities for text-to-cad. Each skill represents a capability for generating, transforming, or analyzing CAD geometry.

## Available Skills

### 1. flatten — Planar face flattening
Flatten planar faces of a solid into the XY plane.

### 2. unfold — Sheet-metal unfolding
Unfold a bent part into a flat pattern. See `unfold.py` for the core implementation.

### 3. dxf — DXF generation
Generate DXF files from CAD geometry.

### 4. **flat pattern of a bent part** — **$dxf skill: flat pattern of bent part workflow**

This is the 4th workflow, combining `unfold` with `dxf` export to produce a flat pattern of a bent part ready for laser cutting or waterjet.

#### Usage

```python
from cadgen import dxf, unfold
from build123d import Box

# Create a bent part (e.g., a bracket with bends)
# ...

# Unfold it into a flat pattern
result = unfold.unfold(bent_part, k_factor=0.33, kerf=0.15)

# Export as DXF with CUT and BEND layers
def bracket_dxf():
    return {
        "CUT": result.profile,       # Outer profile edge
        "BEND": result.bend_lines   # Bend lines on the blank
    }

dxf_export = dxf(bracket_dxf)
```

#### Output

- `profile`: The blank geometry (outer boundary of the flat pattern), suitable for CUT layer
- `bend_lines`: One open line per bend on the blank, ready for the existing BEND layer
- The viewer's bend preview folds the flat pattern back into the original shape

#### Example: U-Channel Bracket

A U-channel with 2mm sheet, two 90° bends, and r_in=2mm unfolds to a blank approximately 82.36 × 60 mm with K=0.33. The profile edge goes to CUT layer, bend lines go to BEND layer.

---

Alan Vo · [alanvo.net](https://alanvo.net) · [X: @alanvoasi](https://x.com/alanvoasi)
