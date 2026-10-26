"""
Flatten planar faces into XY plane - utilities for unfold.
"""

from dataclasses import dataclass
from typing import Optional

from build123d import Face, Vector
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Plane
from OCP.gp import gp_Pln, gp_Dir, gp_Pnt


@dataclass
class PlanarFaceInfo:
    """Information about a planar face."""
    face: Face
    normal: Vector
    origin: Vector
    area: float


def is_planar_face(face: Face) -> bool:
    """Check if a face is planar."""
    surf = BRepAdaptor_Surface(face.wrapped, True)
    return surf.GetType() == GeomAbs_Plane


def get_planar_face_info(face: Face) -> Optional[PlanarFaceInfo]:
    """Extract plane info from a planar face."""
    if not is_planar_face(face):
        return None
    surf = BRepAdaptor_Surface(face.wrapped, True)
    pln = surf.Plane()
    normal = Vector(pln.Axis().Direction().X(), pln.Axis().Direction().Y(), pln.Axis().Direction().Z())
    origin = Vector(pln.Location().X(), pln.Location().Y(), pln.Location().Z())
    area = face.area
    return PlanarFaceInfo(face=face, normal=normal, origin=origin, area=area)


def flatten_face(face: Face) -> Face:
    """Project a planar face onto XY plane."""
    info = get_planar_face_info(face)
    if info is None:
        raise ValueError("Face is not planar")
    # Translate to origin, rotate to XY
    # For now, just return the face - full impl in unfold
    return face


def union_faces(faces: list[Face]) -> Face:
    """Fuse multiple faces into one."""
    from build123d import Compound
    if not faces:
        raise ValueError("No faces to union")
    if len(faces) == 1:
        return faces[0]
    compound = Compound(children=faces)
    return compound.fuse()


def offset_profile(face: Face, offset: float) -> Face:
    """Offset a face profile by distance."""
    return face.offset(offset)

