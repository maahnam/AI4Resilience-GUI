from __future__ import annotations

from pathlib import Path


PACKAGE_DIR = Path(__file__).resolve().parent
SRC_DIR = PACKAGE_DIR.parent
PROJECT_ROOT = SRC_DIR.parent

DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
RAW_NETWORK_DIR = RAW_DATA_DIR / "network"
RAW_SCHEDULES_DIR = RAW_DATA_DIR / "schedules"
RAW_DEMAND_DIR = RAW_DATA_DIR / "demand"
RAW_DISRUPTIONS_DIR = RAW_DATA_DIR / "disruptions"
RAW_COSTS_DIR = RAW_DATA_DIR / "costs"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
PROCESSED_PATHS_DIR = PROCESSED_DATA_DIR / "possible_paths"
PROCESSED_KBEST_DIR = PROCESSED_DATA_DIR / "kbest"

ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
MODEL_ARTIFACTS_DIR = ARTIFACTS_DIR / "models"
Q_TABLES_DIR = MODEL_ARTIFACTS_DIR / "q_tables"
TRAINING_METRICS_DIR = ARTIFACTS_DIR / "metrics" / "training"
RUNS_DIR = ARTIFACTS_DIR / "runs"
SIMULATION_OUTPUTS_DIR = RUNS_DIR / "simulation_outputs"
SHIPMENT_LOGS_DIR = RUNS_DIR / "shipment_logs"
SERVICE_LOGS_DIR = RUNS_DIR / "service_logs"

DOCS_DIR = PROJECT_ROOT / "docs"
ARCHITECTURE_DOCS_DIR = DOCS_DIR / "architecture"
DATASET_DOCS_DIR = DOCS_DIR / "datasets"
NOTEBOOKS_DIR = PROJECT_ROOT / "notebooks"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"

WEB_TEMPLATES_DIR = PROJECT_ROOT / "templates"
CONFIG_DIR = PROJECT_ROOT / "config"
DEFAULT_GUROBI_LICENSE_FILE = CONFIG_DIR / "gurobi.lic"


def ensure_directories(*paths: Path) -> None:
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)


def project_relative(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)
