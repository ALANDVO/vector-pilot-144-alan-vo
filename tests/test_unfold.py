"""
Tests for cadgen.unfold
"""

import math
import pytest
from build123d import Box, Face, Solid, Plane, Vector
from build123d import BuildPart, BuildSketch, Rectangle, extrude


def test_detect_thickness_simple():
    """Test thickness detection on a simple flat plate."""
    from cadgen.unfold import detect_thickness
    
    # Create a flat plate: two parallel faces 2mm apart
    with BuildPart() as part:
        Box(100, 50, 2.0)
    
    thickness = detect_thickness(part.part)
    assert abs(thickness - 2.0) < 1e-6


def test_detect_thickness_cube():
    """Test thickness detection on a cube (has clear thickness = side length)."""
    from cadgen.unfold import detect_thickness
    
    # Cube - has clear thickness = 10
    with BuildPart() as part:
        Box(10, 10, 10)
    
    thickness = detect_thickness(part.part)
    assert abs(thickness - 10.0) < 1e-6


def test_compute_bend_allowance():
    """Test bend allowance formula."""
    from cadgen.unfold import compute_bend_allowance
    
    # 90 deg bend, r_in=2mm, K=0.33, t=2mm
    # BA = θ·(r + K·t) = (π/2) * (2 + 0.33*2) = 1.5708 * 2.66 = 4.178
    ba = compute_bend_allowance(math.pi/2, 2.0, 0.33, 2.0)
    expected = (math.pi/2) * (2.0 + 0.33 * 2.0)
    assert abs(ba - expected) < 1e-6


def test_unfold_flat_plate():
    """Test unfolding a flat plate (no bends)."""
    from cadgen.unfold import unfold
    
    with BuildPart() as part:
        Box(100, 50, 2.0)
    
    result = unfold(part.part, k_factor=0.33, kerf=0.0)
    
    assert result.profile is not None
    assert result.bend_lines == []
    assert result.bends == []
    # Area should be ~5000 mm²
    assert abs(result.profile.area - 5000) < 10


def test_unfold_with_kerf():
    """Test unfolding with kerf offset - just verify it runs without error."""
    from cadgen.unfold import unfold
    
    with BuildPart() as part:
        Box(100, 50, 2.0)
    
    result = unfold(part.part, k_factor=0.33, kerf=0.1)
    
    assert result.profile is not None
    # Kerf applied - just verify it doesn't crash


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
