"""Explicit joint/EE targets and masked loss; stock policies do not infer our masks."""

import numpy as np


def ee_validity(joint_valid):
    """[... ,18] -> [...,2,8]; TCP pose needs all seven arm joints, opening its leader.

    The two neck controls do not participate in either arm's base-frame FK.
    """
    if joint_valid.shape[-1] != 18:
        raise ValueError('Expected the documented 7+7+2+2 Alex action contract')
    result = np.zeros((*joint_valid.shape[:-1], 2, 8), bool)
    for hand in range(2):
        result[..., hand, :7] = joint_valid[..., 7 * hand:7 * (hand + 1)].all(axis=-1)[..., None]
        result[..., hand, 7] = joint_valid[..., 16 + hand]
    return result


class ActionTrainingDataset:
    """Wrap a standard reader, explicitly selecting targets and aligned temporal masks.

    Use the returned action_valid in the policy's elementwise loss, via masked_mse
    or equivalent. Passing this to an unmodified policy loss is insufficient.
    Stats and normalization follow the selected feature, not always `action`.
    """

    def __init__(self, root, *, target='joint', offsets=None, normalize=True):
        from lerobot.datasets.lerobot_dataset import LeRobotDataset
        from pathlib import Path

        if target not in ('joint', 'ee'):
            raise ValueError('target must be joint or ee')
        self.key = 'action' if target == 'joint' else 'action.ee'
        delta = None if offsets is None else {self.key: offsets, 'quality.action_valid': offsets}
        self.dataset = LeRobotDataset('local/robot', root=Path(root), video_backend='pyav', delta_timestamps=delta)
        self.normalize = normalize

    def __len__(self):
        return len(self.dataset)

    def __getitem__(self, index):
        import torch

        row = self.dataset[index]
        target = row[self.key]
        valid = row['quality.action_valid'].numpy()
        if self.key == 'action.ee':
            valid = ee_validity(valid)
        valid = torch.as_tensor(valid) & torch.isfinite(target)
        padding = row.get(f'{self.key}_is_pad')
        if padding is not None:
            valid &= ~padding.reshape(*padding.shape, *([1] * (valid.ndim - padding.ndim)))
        if self.normalize:
            stats = self.dataset.meta.stats[self.key]
            mean = torch.as_tensor(stats['mean'], dtype=target.dtype)
            std = torch.as_tensor(stats['std'], dtype=target.dtype).clamp_min(1e-6)
            target = (torch.where(valid, target, mean) - mean) / std
        target = torch.where(valid, target, torch.zeros_like(target))
        if self.key == 'action.ee':
            target, valid = target.flatten(-2), valid.flatten(-2)
        row['action'], row['action_valid'] = target, valid
        return row


def masked_mse(prediction, target, valid):
    """Exclude invalid/padded components before arithmetic, including their gradients."""
    import torch

    valid = valid.bool() & torch.isfinite(target)
    safe_prediction = torch.where(valid, prediction, torch.zeros_like(prediction))
    safe_target = torch.where(valid, target, torch.zeros_like(target))
    return ((safe_prediction - safe_target) ** 2).sum() / valid.sum().clamp_min(1)
