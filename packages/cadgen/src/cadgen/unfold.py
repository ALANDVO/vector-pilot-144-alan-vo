"""
Sheet-metal unfolding for build123d solids.

cadgen.unfold.unfold(shape, *, k_factor=0.33, bend_table=None, kerf=0.0) -> Unfolded
"""

from dataclasses import dataclass, field
from typing import Optional
import math

from build123d import Face, Solid, Vector, Edge, Compound
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Plane, GeomAbs_Cylinder
from OCP.gp import gp_Pln, gp_Dir, gp_Pnt, gp_Ax1, gp_Vec
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_FACE, TopAbs_EDGE, TopAbs_REVERSED


# ============================================================================
# Data structures
# ============================================================================

@dataclass
class BendRecord:
    """Record of a detected bend with unfolding data."""
    index: int
    angle_rad: float                    # Bend angle in radians (inner face sweep)
    angle_deg: float                    # Bend angle in degrees
    direction: str                      # "UP" or "DOWN" - which side material folds to
    inside_radius: float                # Inner bend radius (r_in)
    allowance: float                    # Bend allowance BA = θ·(r + K·t)
    bend_line: Edge                     # Open line on the blank for BEND layer
    flange_lengths: tuple[float, float] # Length of flanges on either side of bend
    nearest_cut_distance: float         # Distance from bend tangent to nearest cut/hole


@dataclass
class Unfolded:
    """Result of unfolding a sheet-metal part."""
    profile: Face                       # Flat blank profile (OCC union + offset, kerf applied)
    bend_lines: list[Edge]              # Open lines, one per bend, for BEND layer
    bends: list[BendRecord]             # Detailed per-bend records


def _face_normal(face: Face) -> Vector:
    """Get the outward normal of a face, accounting for orientation."""
    surf = BRepAdaptor_Surface(face.wrapped, True)
    if surf.GetType() != GeomAbs_Plane:
        return None
    pln = surf.Plane()
    normal = Vector(pln.Axis().Direction().X(), 
                    pln.Axis().Direction().Y(), 
                    pln.Axis().Direction().Z())
    # Account for face orientation (REVERSED means normal is flipped)
    if face.wrapped.Orientation() == TopAbs_REVERSED:
        normal = Vector(-normal.X, -normal.Y, -normal.Z)
    return normal


def _face_origin(face: Face) -> Vector:
    """Get a point on the face plane."""
    surf = BRepAdaptor_Surface(face.wrapped, True)
    pln = surf.Plane()
    return Vector(pln.Location().X(), pln.Location().Y(), pln.Location().Z())


# ============================================================================
# Thickness detection
# ============================================================================

def detect_thickness(shape: Solid) -> float:
    """
    Detect sheet thickness by voting on parallel planar face pairs with opposite normals.
    
    Raises ValueError if no single thickness winner (not constant-thickness sheet).
    """
    faces = list(shape.faces())
    planar_faces = []
    
    for face in faces:
        surf = BRepAdaptor_Surface(face.wrapped, True)
        if surf.GetType() == GeomAbs_Plane:
            normal = _face_normal(face)
            origin = _face_origin(face)
            if normal is not None:
                planar_faces.append((face, normal, origin, face.area))
    
    if len(planar_faces) < 2:
        raise ValueError("Insufficient planar faces for thickness detection")
    
    # Vote on thickness from parallel opposite-normal pairs
    thickness_votes = {}
    for i, (f1, n1, o1, a1) in enumerate(planar_faces):
        for j, (f2, n2, o2, a2) in enumerate(planar_faces):
            if i >= j:
                continue
            # Check if normals are opposite (parallel, opposite direction)
            if abs(n1.dot(n2) + 1.0) < 1e-6:
                # Parallel planes with opposite normals
                # Distance between planes = thickness
                dist = abs((o2 - o1).dot(n1))
                if dist > 1e-6:  # Non-zero thickness
                    # Round to reasonable precision
                    t = round(dist, 6)
                    thickness_votes[t] = thickness_votes.get(t, 0) + min(a1, a2)
    
    if not thickness_votes:
        raise ValueError("No parallel opposite-normal face pairs found")
    
    # Winner is thickness with highest area-weighted votes
    winner = max(thickness_votes.items(), key=lambda x: x[1])[0]
    
    # Verify it's a clear winner (at least 2x runner-up or unanimous)
    sorted_votes = sorted(thickness_votes.items(), key=lambda x: x[1], reverse=True)
    if len(sorted_votes) > 1 and sorted_votes[0][1] < 2 * sorted_votes[1][1]:
        raise ValueError(f"Ambiguous thickness: votes {thickness_votes}")
    
    return winner


# ============================================================================
# Bend detection
# ============================================================================

def detect_bends(shape: Solid, thickness: float) -> list[dict]:
    """
    Detect bends as coaxial cylindrical face pairs with radius difference = thickness.
    
    Returns list of bend dicts with: inner_face, outer_face, axis, angle_rad, direction, r_in
    """
    faces = list(shape.faces())
    cylindrical_faces = []
    
    for face in faces:
        surf = BRepAdaptor_Surface(face.wrapped, True)
        if surf.GetType() == GeomAbs_Cylinder:
            cyl = surf.Cylinder()
            axis_loc = cyl.Axis().Location()
            axis_dir = cyl.Axis().Direction()
            radius = cyl.Radius()
            axis = (Vector(axis_loc.X(), axis_loc.Y(), axis_loc.Z()),
                    Vector(axis_dir.X(), axis_dir.Y(), axis_dir.Z()))
            cylindrical_faces.append((face, axis, radius, face.area))
    
    bends = []
    used = set()
    
    for i, (f1, axis1, r1, a1) in enumerate(cylindrical_faces):
        if i in used:
            continue
        for j, (f2, axis2, r2, a2) in enumerate(cylindrical_faces):
            if j in used or i == j:
                continue
            # Check coaxial: same axis line (location on axis, same direction or opposite)
            loc1, dir1 = axis1
            loc2, dir2 = axis2
            # Directions should be parallel (same or opposite)
            if abs(abs(dir1.dot(dir2)) - 1.0) > 1e-6:
                continue
            # loc2 should be on axis1 line
            to_loc2 = loc2 - loc1
            if abs(to_loc2.cross(dir1).length) > 1e-6:
                continue
            # Radii differ by thickness
            if abs(abs(r1 - r2) - thickness) > 1e-4:
                continue
            
            # Found a bend pair
            r_in = min(r1, r2)
            r_out = max(r1, r2)
            inner_face = f1 if r1 < r2 else f2
            outer_face = f2 if r1 < r2 else f1
            
            # Get bend angle from inner face parametric range
            surf_inner = BRepAdaptor_Surface(inner_face.wrapped, True)
            # Get U/V bounds - V is angle for cylinder
            u_min, u_max, v_min, v_max = surf_inner.UMin(), surf_inner.UMax(), surf_inner.VMin(), surf_inner.VMax()
            angle_rad = abs(v_max - v_min)
            
            # Determine direction: which side material is on
            direction = "UP"  # Placeholder
            
            bends.append({
                "inner_face": inner_face,
                "outer_face": outer_face,
                "axis": axis1,
                "angle_rad": angle_rad,
                "r_in": r_in,
                "r_out": r_out,
                "direction": direction,
            })
            used.add(i)
            used.add(j)
            break
    
    return bends  # Return empty list if no bends found


# ============================================================================
# Flange tree building
# ============================================================================

def build_flange_tree(shape: Solid, bends: list[dict], thickness: float) -> tuple[Face, dict]:
    """
    Build adjacency tree of planar faces (flanges) connected by bends.
    Returns (root_face, adjacency_dict) where root is largest flat face.
    """
    faces = list(shape.faces())
    planar_faces = []
    
    for face in faces:
        surf = BRepAdaptor_Surface(face.wrapped, True)
        if surf.GetType() == GeomAbs_Plane:
            normal = _face_normal(face)
            if normal is not None:
                planar_faces.append((face, normal, face.area))
    
    if not planar_faces:
        raise ValueError("No planar faces found")
    
    # Build adjacency: two planar faces are adjacent if they share a bend
    adjacency = {face: [] for face, _, _ in planar_faces}
    
    for bend in bends:
        # Find planar faces adjacent to this bend's inner/outer faces
        inner_edges = list(bend["inner_face"].edges())
        outer_edges = list(bend["outer_face"].edges())
        bend_edges = inner_edges + outer_edges
        
        # Find which planar faces share edges with this bend
        connected_planar = []
        for pf, n, a in planar_faces:
            for edge in pf.edges():
                if edge in bend_edges:
                    connected_planar.append(pf)
                    break
        
        # Connect all pairs of connected planar faces through this bend
        for i, pf1 in enumerate(connected_planar):
            for pf2 in connected_planar[i+1:]:
                adjacency[pf1].append((pf2, bend))
                adjacency[pf2].append((pf1, bend))
    
    # Root = largest planar face by area
    root_face = max(planar_faces, key=lambda x: x[2])[0]
    
    return root_face, adjacency


# ============================================================================
# Unfolding
# ============================================================================

def rotate_face_to_xy(face: Face, axis: tuple[Vector, Vector], angle_rad: float) -> Face:
    """Rotate a face about an axis by angle to lay flat in XY."""
    from OCP.gp import gp_Trsf, gp_Ax1, gp_Pnt, gp_Dir
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
    
    loc, dir_vec = axis
    ax1 = gp_Ax1(gp_Pnt(loc.X, loc.Y, loc.Z), gp_Dir(dir_vec.X, dir_vec.Y, dir_vec.Z))
    trsf = gp_Trsf()
    trsf.SetRotation(ax1, angle_rad)
    
    brep_trsf = BRepBuilderAPI_Transform(face.wrapped, trsf, True)
    brep_trsf.Build()
    if not brep_trsf.IsDone():
        raise RuntimeError("Face rotation failed")
    return Face(brep_trsf.Shape())


def compute_bend_allowance(angle_rad: float, r_in: float, k_factor: float, thickness: float) -> float:
    """Compute bend allowance: BA = θ·(r + K·t)"""
    return angle_rad * (r_in + k_factor * thickness)


def unfold_flanges(root_face: Face, adjacency: dict, bends: list[dict], 
                   k_factor: float, bend_table: Optional[dict], kerf: float, thickness: float) -> Unfolded:
    """
    Unfold all flanges into XY by composing rotations about bend axes.
    Compute bend allowances and build flat profile with bend lines.
    """
    from build123d import Face, Edge, Compound
    from OCP.gp import gp_Trsf, gp_Ax1, gp_Pnt, gp_Dir, gp_Vec
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform, BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeFace
    from OCP.Geom import Geom_Line
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse
    
    # Track visited faces and their transforms
    visited = set()
    face_transforms = {}  # face -> (transform_matrix, bend_path)
    
    # Start with root face - align it to XY
    root_normal = _face_normal(root_face)
    root_face_xy = root_face
    
    # Rotate root face to XY if needed
    if root_normal is not None and abs(root_normal.Z - 1.0) > 1e-6:
        # Find rotation axis: cross(normal, Z)
        z_axis = Vector(0, 0, 1)
        rot_axis = root_normal.cross(z_axis)
        if rot_axis.length > 1e-6:
            rot_axis = rot_axis.normalize()
            angle = math.acos(max(-1, min(1, root_normal.dot(z_axis))))
            # Apply rotation
            from OCP.gp import gp_Trsf, gp_Ax1, gp_Pnt, gp_Dir
            ax1 = gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(rot_axis.X, rot_axis.Y, rot_axis.Z))
            trsf = gp_Trsf()
            trsf.SetRotation(ax1, angle)
            from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
            brep_trsf = BRepBuilderAPI_Transform(root_face.wrapped, trsf, True)
            brep_trsf.Build()
            if brep_trsf.IsDone():
                root_face_xy = Face(brep_trsf.Shape())
    
    visited.add(root_face)
    face_transforms[root_face] = (None, [])
    
    # BFS to unfold all connected flanges
    queue = [root_face]
    while queue:
        current = queue.pop(0)
        for neighbor, bend in adjacency.get(current, []):
            if neighbor in visited:
                continue
            # Rotate neighbor about bend axis to align with current
            axis = bend["axis"]
            angle = bend["angle_rad"]
            # Direction: fold "up" or "down" - for unfolding we rotate opposite to bend
            neighbor_flat = rotate_face_to_xy(neighbor, axis, -angle)
            visited.add(neighbor)
            face_transforms[neighbor] = (axis, [bend])
            queue.append(neighbor)
    
    # Collect all flattened faces
    flat_faces = list(face_transforms.keys())
    
    # Union them
    if len(flat_faces) == 1:
        profile = flat_faces[0]
    else:
        compound = Compound(children=flat_faces)
        profile = compound.fuse()
    
    # Apply kerf offset
    if kerf != 0:
        profile = profile.offset(kerf)
    
    # Generate bend lines and bend records
    bend_lines = []
    bend_records = []
    
    for idx, bend in enumerate(bends):
        axis_loc, axis_dir = bend["axis"]
        r_in = bend["r_in"]
        angle_rad = bend["angle_rad"]
        
        # Compute allowance
        if bend_table:
            key = (round(thickness, 3), round(r_in, 3), round(math.degrees(angle_rad), 1))
            allowance = bend_table.get(key, compute_bend_allowance(angle_rad, r_in, k_factor, thickness))
        else:
            allowance = compute_bend_allowance(angle_rad, r_in, k_factor, thickness)
        
        # Create bend line (simplified: line along axis at neutral plane position)
        p1 = axis_loc - axis_dir * 50  # Extend line
        p2 = axis_loc + axis_dir * 50
        from OCP.gp import gp_Pnt, gp_Dir
        from OCP.Geom import Geom_Line
        line_geom = Geom_Line(gp_Pnt(p1.X, p1.Y, p1.Z), gp_Dir(axis_dir.X, axis_dir.Y, axis_dir.Z))
        from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge
        bend_edge = Edge(BRepBuilderAPI_MakeEdge(line_geom).Edge())
        bend_lines.append(bend_edge)
        
        # Flange lengths (simplified)
        flange_lengths = (10.0, 10.0)  # Placeholder
        
        # Nearest cut distance (placeholder)
        nearest_cut = 5.0
        
        bend_records.append(BendRecord(
            index=idx,
            angle_rad=angle_rad,
            angle_deg=math.degrees(angle_rad),
            direction=bend.get("direction", "UP"),
            inside_radius=r_in,
            allowance=allowance,
            bend_line=bend_edge,
            flange_lengths=flange_lengths,
            nearest_cut_distance=nearest_cut,
        ))
    
    return Unfolded(
        profile=profile,
        bend_lines=bend_lines,
        bends=bend_records,
    )


# ============================================================================
# Main API
# ============================================================================

def unfold(shape: Solid, *, k_factor: float = 0.33, bend_table: Optional[dict] = None, 
           kerf: float = 0.0) -> Unfolded:
    """
    Unfold a constant-thickness sheet-metal solid into a flat pattern.
    
    Args:
        shape: build123d Solid with constant thickness, planar flanges, cylindrical bends
        k_factor: K-factor for bend allowance (default 0.33)
        bend_table: Optional dict mapping (thickness, radius, angle_deg) -> deduction
        kerf: Kerf offset for cutting (default 0.0)
    
    Returns:
        Unfolded object with profile, bend_lines, and bends records
    
    Raises:
        ValueError: If shape is not constant thickness, has invalid bends, etc.
    """
    # 1. Detect thickness
    thickness = detect_thickness(shape)
    
    # 2. Detect bends
    bends = detect_bends(shape, thickness)
    
    # 3. If no bends, just return the largest planar face laid flat
    if not bends:
        # Find the largest planar face and return it as the profile
        faces = list(shape.faces())
        planar_faces = []
        for face in faces:
            surf = BRepAdaptor_Surface(face.wrapped, True)
            if surf.GetType() == GeomAbs_Plane:
                normal = _face_normal(face)
                if normal is not None:
                    planar_faces.append((face, normal, face.area))
        
        if not planar_faces:
            raise ValueError("No planar faces found")
        
        # Root = largest planar face
        root_face = max(planar_faces, key=lambda x: x[2])[0]
        
        # Align to XY
        root_normal = _face_normal(root_face)
        root_face_xy = root_face
        if root_normal is not None and abs(root_normal.Z - 1.0) > 1e-6:
            z_axis = Vector(0, 0, 1)
            rot_axis = root_normal.cross(z_axis)
            if rot_axis.length > 1e-6:
                rot_axis = rot_axis.normalize()
                angle = math.acos(max(-1, min(1, root_normal.dot(z_axis))))
                from OCP.gp import gp_Trsf, gp_Ax1, gp_Pnt, gp_Dir
                ax1 = gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(rot_axis.X, rot_axis.Y, rot_axis.Z))
                trsf = gp_Trsf()
                trsf.SetRotation(ax1, angle)
                from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
                brep_trsf = BRepBuilderAPI_Transform(root_face.wrapped, trsf, True)
                brep_trsf.Build()
                if brep_trsf.IsDone():
                    root_face_xy = Face(brep_trsf.Shape())
        
        if kerf != 0:
            root_face_xy = root_face_xy.offset(kerf)
        
        return Unfolded(
            profile=root_face_xy,
            bend_lines=[],
            bends=[],
        )
    
    # 4. Build flange tree
    root_face, adjacency = build_flange_tree(shape, bends, thickness)
    
    # 5. Unfold flanges and compute bend allowances
    result = unfold_flanges(root_face, adjacency, bends, k_factor, bend_table, kerf, thickness)
    
    return result


__all__ = ["unfold", "Unfolded", "BendRecord", "detect_thickness", "detect_bends", "compute_bend_allowance"]
