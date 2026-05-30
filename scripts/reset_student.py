"""Reset a student model — useful during development and testing."""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_tutor.student_model.store import reset_student_model
from ai_tutor.config import settings

parser = argparse.ArgumentParser()
parser.add_argument("--student", default=settings.default_student_id)
parser.add_argument("--pack", default=settings.default_pack_id)
args = parser.parse_args()
reset_student_model(args.student, args.pack)
print(f"✓ Reset student model: {args.student} × {args.pack}")
