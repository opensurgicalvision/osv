"""Tests for CholecSeg8kSegmentation's zip access (osv/datasets/segmentation.py).

The bug this file exists for: a ZipFile opened once in the parent process
(e.g. by `class_pixel_counts()`, called before the DataLoader exists) gets
inherited by every worker `fork()` spawns. `fork()` duplicates the file
descriptor, not a private read position -- POSIX shares the underlying open
file description's offset across it -- so concurrent workers race
seek()+read() on one shared position and end up reading each other's byte
ranges. That surfaced as `zipfile.BadZipFile: Bad CRC-32` on an effectively
random archive member during a real GPU training run, not as a clean
exception at open time, which is what made it worth pinning down here.
"""

from __future__ import annotations

import io
import os
import zipfile
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from osv.datasets.segmentation import CholecSeg8kSegmentation


def _png_bytes(fill: int, size: tuple[int, int] = (4, 4), rgb: bool = False) -> bytes:
    shape = (size[1], size[0], 3) if rgb else (size[1], size[0])
    arr = np.full(shape, fill, dtype=np.uint8)
    buf = io.BytesIO()
    Image.fromarray(arr, mode="RGB" if rgb else "L").save(buf, format="PNG")
    return buf.getvalue()


def _make_archive(path: Path, n_frames: int) -> None:
    """A tiny archive with `n_frames` distinguishable entries.

    Each frame's raw image and watershed mask are filled with a value equal
    to the frame's index, so misdirected reads (the exact failure mode of
    the fork bug) show up as a mismatch between the requested index and the
    pixel value actually returned -- not just an exception.
    """
    with zipfile.ZipFile(path, "w") as zf:
        for i in range(n_frames):
            base = f"CholecSeg8k/video01/video01_{i:05d}/frame_{i:05d}"
            zf.writestr(f"{base}_endo.png", _png_bytes(i % 251, rgb=True))
            zf.writestr(f"{base}_endo_mask.png", _png_bytes(0))
            zf.writestr(f"{base}_endo_color_mask.png", _png_bytes(0))
            zf.writestr(f"{base}_endo_watershed_mask.png", _png_bytes(i % 251))


def _bare_dataset(zip_path: Path) -> CholecSeg8kSegmentation:
    """A dataset instance for exercising `_read`/`raw_pair` directly.

    Bypasses `__init__` (which needs a full instances.json + an approved
    manifest) since this is testing zip-handle lifecycle, not the pipeline
    those wire up.
    """
    ds = object.__new__(CholecSeg8kSegmentation)
    ds.source = zip_path
    ds._zip = None
    ds._zip_pid = None
    ds._lut = np.arange(256, dtype=np.uint8)  # identity: watershed value == label
    return ds


# --- the pid-reopen mechanism, platform-independent --------------------------


def test_first_read_opens_a_handle_and_records_this_process(tmp_path: Path):
    zip_path = tmp_path / "a.zip"
    _make_archive(zip_path, 3)
    ds = _bare_dataset(zip_path)

    ds._read("CholecSeg8k/video01/video01_00000/frame_00000_endo.png")

    assert ds._zip is not None
    assert ds._zip_pid == os.getpid()


def test_reads_within_the_same_process_reuse_one_handle(tmp_path: Path):
    zip_path = tmp_path / "a.zip"
    _make_archive(zip_path, 3)
    ds = _bare_dataset(zip_path)

    ds._read("CholecSeg8k/video01/video01_00000/frame_00000_endo.png")
    handle = ds._zip
    ds._read("CholecSeg8k/video01/video01_00001/frame_00001_endo.png")

    assert ds._zip is handle, "a second read in the same process must not reopen"


def test_a_different_pid_forces_a_fresh_handle_and_closes_the_old_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    # Simulates exactly the bug scenario: `_zip` was already set (as if opened
    # by the parent process before a fork), then a "worker" with a different
    # pid calls _read(). It must get its own handle, not inherit the stale one.
    zip_path = tmp_path / "a.zip"
    _make_archive(zip_path, 3)
    ds = _bare_dataset(zip_path)

    monkeypatch.setattr(os, "getpid", lambda: 111)
    ds._read("CholecSeg8k/video01/video01_00000/frame_00000_endo.png")
    parent_handle = ds._zip
    assert parent_handle.fp is not None

    monkeypatch.setattr(os, "getpid", lambda: 222)
    ds._read("CholecSeg8k/video01/video01_00001/frame_00001_endo.png")

    assert ds._zip is not parent_handle
    assert ds._zip_pid == 222
    assert parent_handle.fp is None, "the pid-111 handle should have been closed"


def test_raw_pair_returns_the_frame_that_was_actually_asked_for(tmp_path: Path):
    # Without the fix, this is exactly the shape of corruption the fork race
    # produces: a caller asks for frame k and silently gets bytes belonging to
    # a different member. Here we just pin the honest, single-process case.
    zip_path = tmp_path / "a.zip"
    n = 10
    _make_archive(zip_path, n)
    ds = _bare_dataset(zip_path)
    ds.images = [
        {"file_name": f"CholecSeg8k/video01/video01_{i:05d}/frame_{i:05d}_endo.png"}
        for i in range(n)
    ]

    for i in range(n):
        rgb, label = ds.raw_pair(i)
        assert int(rgb[0, 0, 0]) == i % 251
        assert int(label[0, 0]) == i % 251


# --- the real regression: concurrent workers after an inherited handle -------


@pytest.mark.skipif(not hasattr(os, "fork"), reason="fork() race is POSIX-only; this is the Linux GPU-pod path")
def test_concurrent_forked_readers_do_not_corrupt_each_others_reads(tmp_path: Path):
    """End-to-end regression for the training-run crash.

    Opens the zip once in this process (mirroring class_pixel_counts() running
    before the DataLoader forks its workers), then forks several children that
    hammer many entries concurrently. Every child must read back exactly the
    frame it asked for. Before the fix, forked children inherited the
    already-open handle and raced on its shared file offset.
    """
    zip_path = tmp_path / "a.zip"
    n = 40
    _make_archive(zip_path, n)
    ds = _bare_dataset(zip_path)

    # Force the handle open in THIS process before forking, exactly like
    # class_pixel_counts() does relative to DataLoader worker creation.
    ds._read("CholecSeg8k/video01/video01_00000/frame_00000_endo.png")
    assert ds._zip is not None

    n_children = 4
    read_pipes = [os.pipe() for _ in range(n_children)]

    for child_idx, (r_fd, w_fd) in enumerate(read_pipes):
        pid = os.fork()
        if pid == 0:  # child
            os.close(r_fd)
            ok = True
            try:
                for _ in range(50):
                    i = (child_idx * 37 + _ * 7) % n
                    frame = f"CholecSeg8k/video01/video01_{i:05d}/frame_{i:05d}_endo.png"
                    arr = ds._read(frame)
                    if int(arr[0, 0, 0]) != i % 251:
                        ok = False
                        break
            except Exception:
                ok = False
            os.write(w_fd, b"1" if ok else b"0")
            os._exit(0)
        else:
            os.close(w_fd)

    results = []
    for r_fd, _ in read_pipes:
        results.append(os.read(r_fd, 1))
        os.close(r_fd)
    for _ in read_pipes:
        os.wait()

    assert results == [b"1"] * n_children, (
        "a forked worker read back the wrong frame -- the shared, "
        "inherited zip handle raced across processes"
    )
