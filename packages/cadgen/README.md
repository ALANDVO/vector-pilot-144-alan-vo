# cadgen

CAD generation utilities for text-to-cad.

## Modules

- `cadgen.flatten` - Planar face flattening utilities
- `cadgen.unfold` - Sheet-metal unfolding

## unfold API

```python
from cadgen import unfold
from build123d import Solid

result: unfold.Unfolded = unfold.unfold(
    shape: Solid,
    k_factor: float = 0.33,
    bend_table: dict | None = None,
    kerf: float = 0.0
)

# Unfolded attributes:
# - profile: Face (flat blank)
# - bend_lines: list[Edge] (for BEND layer)
# - bends: list[BendRecord]
```

### BendRecord

```python
@dataclass
class BendRecord:
    index: int
    angle_rad: float
    angle_deg: float
    direction: str  # "UP" or "DOWN"
    inside_radius: float
    allowance: float
    bend_line: Edge
    flange_lengths: tuple[float, float]
    nearest_cut_distance: float
```

## Installation

```bash
pip install -e .
```

## Testing

```bash
pytest ../../tests/test_unfold.py -v
```
