"""Sampled positional workspace on a common base-frame lattice, in metres.

Arrays use [hand, x, y, z], with hand order left, right. Origin is the lower
corner of cell (0,0,0), not its center. Occupancy is empirical FK coverage.
"""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt


@dataclass
class WorkspaceGrid:
    origin_m: np.ndarray
    spacing_m: float
    occupancy: np.ndarray
    distance_m: np.ndarray

    def __post_init__(self):
        self.origin_m = np.asarray(self.origin_m, dtype=np.float64)
        if self.origin_m.shape != (3,) or not np.isfinite(self.origin_m).all():
            raise ValueError("Grid origin must be three finite base-frame coordinates")
        if not np.isfinite(self.spacing_m) or self.spacing_m <= 0:
            raise ValueError("Voxel spacing must be positive finite metres")
        if (self.occupancy.ndim != 4 or self.occupancy.shape[0] != 2
                or min(self.occupancy.shape[1:]) < 3 or self.occupancy.dtype != bool):
            raise ValueError("Occupancy must be boolean [2, X, Y, Z], with dimensions >= 3")
        if self.distance_m.shape != self.occupancy.shape or not np.isfinite(self.distance_m).all():
            raise ValueError("Distances must be finite and match occupancy dimensions")

    @property
    def shape(self):
        return np.asarray(self.occupancy.shape[1:], dtype=np.int64)

    def indices(self, points_m):
        """[N,3] base points → int64 indices and [N] validity; invalid rows are -1.

        Cells are half-open: lower corners included, upper corners excluded.
        This domain extends half a cell beyond the interpolation domain.
        """
        points = np.asarray(points_m, dtype=np.float64)
        if points.ndim != 2 or points.shape[1] != 3:
            raise ValueError("Expected base-frame points with shape [N,3]")
        upper = self.origin_m + self.shape * self.spacing_m
        valid = np.isfinite(points).all(axis=1) & (points >= self.origin_m).all(axis=1) & (points < upper).all(axis=1)
        indices = np.full(points.shape, -1, dtype=np.int64)
        indices[valid] = np.floor((points[valid] - self.origin_m) / self.spacing_m).astype(np.int64)
        # Floating arithmetic at the outer face must never index beyond the array.
        valid &= ((indices >= 0) & (indices < self.shape)).all(axis=1)
        indices[~valid] = -1
        return indices, valid

    def centers(self, indices):
        """Integer [N,3] indices → cell centers in base-frame metres."""
        indices = np.asarray(indices)
        if (indices.ndim != 2 or indices.shape[1] != 3
                or not np.issubdtype(indices.dtype, np.integer)
                or np.any(indices < 0) or np.any(indices >= self.shape)):
            raise ValueError("Expected in-bounds integer voxel indices [N,3]")
        return self.origin_m + (indices + 0.5) * self.spacing_m

    def contains(self, points_m):
        """Return [N,2] sampled occupancy and [N] domain validity."""
        indices, valid = self.indices(points_m)
        inside = np.zeros((len(indices), 2), dtype=bool)
        inside[valid] = self.occupancy[(slice(None), *indices[valid].T)].T
        return inside, valid

    def query(self, points_m):
        """Differentiable trilinear query of a floating torch Tensor [N,3].

        Returns distances [N,2] in metres and validity [N]. Invalid inputs
        (nonfinite or beyond outermost cell centers) yield NaN, never a padded
        zero that could be confused with the workspace boundary.
        """
        import torch
        from torch.nn.functional import grid_sample

        if (not isinstance(points_m, torch.Tensor) or points_m.ndim != 2
                or points_m.shape[1] != 3 or points_m.dtype not in (torch.float32, torch.float64)):
            raise ValueError("Expected float32/float64 torch base-frame points [N,3]")
        shape = torch.as_tensor(self.shape, dtype=points_m.dtype, device=points_m.device)
        # Round the saved float64 center coordinates once, just as centers() does.
        # Computing these in float32 can otherwise exclude the last valid center.
        lower = torch.as_tensor(self.origin_m + 0.5 * self.spacing_m, dtype=points_m.dtype, device=points_m.device)
        upper = torch.as_tensor(self.origin_m + (self.shape - 0.5) * self.spacing_m, dtype=points_m.dtype, device=points_m.device)
        valid = torch.isfinite(points_m).all(dim=1) & (points_m >= lower).all(dim=1) & (points_m <= upper).all(dim=1)
        safe_points = torch.where(valid[:, None], points_m, lower)
        normalized = 2 * (safe_points - lower) / ((shape - 1) * self.spacing_m) - 1
        # PyTorch spatial storage is [D=Z,H=Y,W=X], while query coordinates are XYZ.
        tensor = torch.as_tensor(self.distance_m, dtype=points_m.dtype, device=points_m.device)
        tensor = tensor.permute(0, 3, 2, 1).unsqueeze(0)
        values = grid_sample(tensor, normalized.reshape(1, -1, 1, 1, 3),
                             mode="bilinear", padding_mode="border", align_corners=True)
        values = values[0, :, :, 0, 0].T
        return torch.where(valid[:, None], values, torch.nan), valid

    def save(self, path):
        with Path(path).open("xb") as stream:
            np.savez_compressed(stream, origin_m=self.origin_m, spacing_m=self.spacing_m,
                                occupancy=self.occupancy, distance_m=self.distance_m,
                                axis_order="hand,x,y,z", hand_order=["left", "right"])

    @classmethod
    def load(cls, path):
        with np.load(path, allow_pickle=False) as data:
            if str(data["axis_order"]) != "hand,x,y,z" or data["hand_order"].tolist() != ["left", "right"]:
                raise ValueError("Unsupported workspace axis/hand order")
            return cls(data["origin_m"], float(data["spacing_m"]), data["occupancy"], data["distance_m"])


def build_grid(point_clouds, spacing_m=0.02, padding_cells=2):
    """Two finite [N,3] FK clouds → padded occupancy and center-distance tensors.

    A sample marks only its containing voxel. No morphological filling is used.
    The EDT difference approximates the boundary of sampled cells, not the true
    robot workspace. Negative distances indicate occupied cells.
    """
    if not np.isfinite(spacing_m) or spacing_m <= 0:
        raise ValueError("Voxel spacing must be positive finite metres")
    if type(padding_cells) is not int or padding_cells < 1:
        raise ValueError("At least one empty border cell is required")
    clouds = [np.asarray(p, dtype=np.float64) for p in point_clouds]
    if len(clouds) != 2 or any(p.ndim != 2 or p.shape[1] != 3 or len(p) == 0 or not np.isfinite(p).all() for p in clouds):
        raise ValueError("Expected nonempty finite left/right FK clouds [N,3]")
    lower = np.floor(np.min([p.min(axis=0) for p in clouds], axis=0) / spacing_m) - padding_cells
    upper = np.floor(np.max([p.max(axis=0) for p in clouds], axis=0) / spacing_m) + padding_cells + 1
    shape = (upper - lower).astype(np.int64)
    origin = lower * spacing_m
    occupancy = np.zeros((2, *shape), dtype=bool)
    for hand, points in enumerate(clouds):
        indices = np.floor((points - origin) / spacing_m).astype(np.int64)
        occupancy[(hand, *indices.T)] = True
    distance = np.stack([distance_transform_edt(~o, sampling=spacing_m)
                         - distance_transform_edt(o, sampling=spacing_m) for o in occupancy])
    return WorkspaceGrid(origin, spacing_m, occupancy, distance)
