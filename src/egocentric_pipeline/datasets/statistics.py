"""Mask-aware numeric statistics with the pinned writer's standard metadata layout."""

from contextlib import contextmanager

import numpy as np
import pyarrow.parquet as pq

from egocentric_pipeline.datasets.training import ee_validity


def numeric_stats(values, valid=None):
    """Reduce time only, preserving feature axes. Empty components use neutral stats.

    LeRobot requires scalar count: it records row count, not per-component valid
    counts. Consequently global statistics are recomputed from rows after append;
    upstream weighted aggregation of masked episode summaries is not exact.
    """
    values = np.asarray(values)
    shape = values.shape[1:] or (1,)
    flat = values.reshape(len(values), -1)
    mask = np.isfinite(flat)
    if valid is not None:
        mask &= np.broadcast_to(valid, values.shape).reshape(flat.shape)
    names = ('min', 'max', 'mean', 'std', 'q01', 'q10', 'q50', 'q90', 'q99')
    result = {key: np.zeros(flat.shape[1], np.float64) for key in names}
    for column in range(flat.shape[1]):
        data = flat[mask[:, column], column].astype(np.float64)
        if len(data):
            stats = [data.min(), data.max(), data.mean(), data.std(), *np.quantile(data, [.01, .1, .5, .9, .99])]
            for key, value in zip(names, stats):
                result[key][column] = value
        else:
            result['std'][column] = 1.
    return {**{k: v.reshape(shape) for k, v in result.items()}, 'count': np.array([len(values)])}


def numeric_episode_stats(data, features):
    result = {}
    for key, feature in features.items():
        if feature['dtype'] in ('image', 'video', 'language', 'string'):
            continue
        valid = None
        if key == 'action':
            valid = data['quality.action_valid']
        elif key == 'action.ee':
            valid = ee_validity(data['quality.action_valid'])
        elif key.startswith('observation.hands.') and not key.endswith('source_status'):
            valid = (data['observation.hands.source_status'] > 0)[..., None]
        result[key] = numeric_stats(data[key], valid)
    return result


@contextmanager
def masked_writer_statistics():
    """Scoped compatibility adapter; export runs single-threaded in its own process.

    The pinned public save_episode API has no stats hook. Delegate RGB statistics
    unchanged and replace only numeric reductions; always restore upstream state.
    """
    from lerobot.datasets import dataset_writer

    original = dataset_writer.compute_episode_stats

    def compute(data, features):
        visual = {k: v for k, v in features.items() if v['dtype'] in ('image', 'video')}
        result = original({k: data[k] for k in visual}, visual)
        result.update(numeric_episode_stats(data, features))
        return result

    dataset_writer.compute_episode_stats = compute
    try:
        yield
    finally:
        dataset_writer.compute_episode_stats = original


def refresh_numeric_statistics(root, features):
    """Recompute exact pilot statistics across shards; never average masked means."""
    from lerobot.datasets.io_utils import load_stats, write_stats

    keys = [k for k, v in features.items() if v['dtype'] not in ('video', 'image', 'language', 'string')]
    tables = [pq.read_table(p, columns=keys).to_pydict() for p in sorted(root.glob('data/*/*.parquet'))]
    arrays = {k: np.concatenate([np.asarray(t[k], dtype=features[k]['dtype']).reshape(-1, *features[k]['shape'])
                                for t in tables]) for k in keys}
    stats = load_stats(root)
    stats.update(numeric_episode_stats(arrays, features))
    write_stats(stats, root)
