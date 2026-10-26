# vector-pilot-144-alan-vo

> Work in progress. This checkpoint may be incomplete or fail tests. See PLAN.md and STATUS.md before use.


Give your agent CAD superpowers.

## Project Structure

```
vector-pilot-144-alan-vo/
├── packages/
│   └── cadgen/           # CAD generation utilities
│       ├── src/cadgen/
│       │   ├── __init__.py
│       │   ├── lazy.py
│       │   ├── flatten.py
│       │   └── unfold.py
│       ├── pyproject.toml
│       └── README.md
├── tests/
│   └── test_unfold.py
├── models/
│   └── drawings/
├── PLAN.md
├── feature-plan.json
└── README.md
```

## cadgen Package

The `cadgen` package provides CAD generation utilities for text-to-cad.

### Modules

- **cadgen.flatten** - Flatten planar faces into XY plane (utilities for unfold)
- **cadgen.unfold** - Sheet-metal unfolding for build123d solids

### unfold Module

```python
from cadgen import unfold
from build123d import Box, BuildPart

with BuildPart() as part:
    Box(100, 50, 2.0)  # 2mm thick plate

result = unfold.unfold(part.part, k_factor=0.33, kerf=0.15)

# result.profile - flat blank Face
# result.bend_lines - list of Edges for BEND layer
# result.bends - list of BendRecord with detailed bend info
```

### Installation

```bash
cd packages/cadgen
pip install -e .
```

### Testing

```bash
pytest tests/test_unfold.py -v
```

## Features

### Completed
- **unfold-core**: Sheet-metal unfolding with thickness detection, bend detection, bend allowance calculation, and Unfolded output

### Planned
- **dxf-workflow**: $dxf skill integration for flat pattern export
- **dfm-sendcutsend-integration**: Consume Unfolded.bends for DFM and SendCutSend
- **test-fixtures**: U-channel bracket test fixtures

## License

MIT

Maintainer: Alan Vo <alanvo@gmail.com>
