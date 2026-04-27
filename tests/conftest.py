from __future__ import annotations

import sys
import warnings
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


warnings.filterwarnings(
    "ignore",
    message=r"datetime\.datetime\.utcfromtimestamp\(\) is deprecated.*",
    category=DeprecationWarning,
)
