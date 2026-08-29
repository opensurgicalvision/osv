"""OpenSurgicalVision (OSV)

Open source benchmark, datasets and baseline models for laparoscopic computer vision
and surgical scene understanding.

RESEARCH USE ONLY — NOT FOR CLINICAL USE.
"""

__version__ = "0.1.0"
__author__ = "OpenSurgicalVision Contributors"
__license__ = "Apache-2.0"

from osv import (
    annotate,
    augment,
    datasets,
    deid,
    deploy,
    eval,
    models,
    robustness,
    serve,
    train,
)

__all__ = [
    "__version__",
    "annotate",
    "augment",
    "datasets",
    "deid",
    "deploy",
    "eval",
    "models",
    "robustness",
    "serve",
    "train",
]
