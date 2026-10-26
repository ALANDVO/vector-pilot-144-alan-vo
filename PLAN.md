# Product development plan

Each round completes one feature or repair. Future items are planned, not implemented claims.

## Current round

unfold-core

## Roadmap

### unfold-core — cadgen.unfold core: thickness, bends, flanges, allowance, Unfolded output

Status: done

Acceptance:
- cadgen.unfold.unfold(shape, k_factor=0.33, kerf=0.0) -> Unfolded
- Thickness detection: parallel planar face pairs vote on constant offset
- Bend detection: coaxial cylindrical pairs with radius diff = thickness
- Flange tree rooted at largest flat, laid into XY via bend-axis rotations
- Bend allowance BA = θ·(r + K·t) or bend table
- Unfolded: profile, bend_lines, bends[] with angle, direction, r_in, allowance, line, flange lengths, nearest cut/hole distance

Implementation: `packages/cadgen/src/cadgen/unfold.py`

Tests: `tests/test_unfold.py`

### dxf-workflow — $dxf skill: flat pattern of bent part workflow

Status: planned

Acceptance:
- SKILLS.md documents 4th workflow
- references/generator-templates.md updated

### dfm-sendcutsend-integration — DFM/SendCutSend consume Unfolded.bends

Status: planned

Acceptance:
- $dfm sheet-metal references Unfolded.bends
- $sendcutsend bend checks use Unfolded.bends

### test-fixtures — Test fixtures: u_channel_bracket folded + unfolded

Status: planned

Acceptance:
- models/drawings/u_channel_bracket_folded.step
- models/drawings/u_channel_bracket_unfolded.step

