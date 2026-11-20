# Generator Templates

This directory contains templates for CAD generators used by the text-to-cad system.

## Available Templates

### dxf Template — Flat pattern of bent part

Template for generating DXF output from an unfolded sheet-metal part.

#### Template Variables

- `profile`: The blank profile geometry (outer boundary)
- `bend_lines`: List of bend lines on the flat pattern
- `bends`: List of bend records with:
  - `angle`: Bend angle in radians
  - `direction`: Fold direction (UP/DOWN relative to original part)
  - `r_in`: Inside radius of the bend
  - `allowance`: Bend allowance computed via BA = θ·(r + K·t)
  - `line`: The bend line edge on the blank
  - `flange_lengths`: Lengths of flanges on either side of the bend
  - `nearest_cut_distance`: Distance from bend tangent to nearest cut/hole edge

#### Usage Example

```python
from cadgen import dxf, unfold
from build123d import Box

# Create and unfold a part
result = unfold.unfold(bent_part, k_factor=0.33, kerf=0.15)

# Generate DXF using the template
dxf_output = dxf_template({
    "profile": result.profile,
    "bend_lines": result.bend_lines,
    "bends": result.bends,
})
```

#### Template File

The template maps the `Unfolded` output to DXF layers:
- Profile edges → `CUT` layer
- Bend lines → `BEND` layer
- Bend annotations → XDATA or layer-name conventions (`BEND_<angle>_<UP|DOWN>`)
