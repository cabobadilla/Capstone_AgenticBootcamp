"""
Student Model persistence — load/save JSON files per student_id × pack_id.

File path: data/students/{student_id}_{pack_id}.json
Atomic writes (write to .tmp then rename) prevent corruption if the process dies mid-write.
Human-readable JSON with indentation (spec v2 NF-04).
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path

from loguru import logger

from ai_tutor.config import settings
from ai_tutor.models import DomainStats, Pack, StudentModel


def _student_path(student_id: str, pack_id: str) -> Path:
    return settings.student_models_dir / f"{student_id}_{pack_id}.json"


def load_student_model(student_id: str, pack_id: str, pack: Pack) -> StudentModel:
    """
    Load an existing student model from disk, or create a fresh one if none exists.

    When creating a new model, pre-populates the domain keys from the Pack so
    the dashboard can show all domains even before any questions are answered.
    """
    path = _student_path(student_id, pack_id)
    settings.student_models_dir.mkdir(parents=True, exist_ok=True)

    if path.exists():
        try:
            data = json.loads(path.read_text())
            model = StudentModel(**data)
            logger.debug(f"Loaded student model: {student_id} × {pack_id} ({len(model.session_history)} events)")
            return model
        except Exception as e:
            logger.warning(f"Corrupt student model at {path}, creating fresh: {e}")

    # Create a fresh model with all pack domains pre-populated at 0.0 mastery
    domains = {
        d.id: DomainStats(weight=d.weight, aggregate_mastery=0.0)
        for d in pack.domains
    }
    model = StudentModel(
        student_id=student_id,
        pack_id=pack_id,
        domains=domains,
    )
    save_student_model(model)
    logger.info(f"Created new student model: {student_id} × {pack_id}")
    return model


def save_student_model(model: StudentModel) -> None:
    """
    Atomically save the student model to disk.

    Uses write-to-temp + rename so a crash mid-write doesn't corrupt the file.
    """
    path = _student_path(model.student_id, model.pack_id)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Serialize with datetime objects converted to ISO strings
    data = json.loads(model.model_dump_json())

    # Write to a temp file in the same directory, then rename (atomic on POSIX)
    with tempfile.NamedTemporaryFile(
        mode="w",
        dir=path.parent,
        suffix=".tmp",
        delete=False,
    ) as tmp:
        json.dump(data, tmp, indent=2, default=str)
        tmp_path = Path(tmp.name)

    tmp_path.replace(path)
    logger.debug(f"Saved student model: {model.student_id} × {model.pack_id}")


def reset_student_model(student_id: str, pack_id: str) -> None:
    """Delete the student model file (used by scripts/reset_student.py)."""
    path = _student_path(student_id, pack_id)
    if path.exists():
        path.unlink()
        logger.info(f"Reset student model: {student_id} × {pack_id}")
