from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from lahso.bar_chart_plot import comparison
from lahso.config import Config
from lahso.paths import (
    Q_TABLES_DIR,
    RAW_DISRUPTIONS_DIR,
    TRAINING_METRICS_DIR,
    UPLOADS_DIR,
    ensure_directories,
    project_relative,
)
from lahso.web.serialization import dataframe_records
from lahso.web.state import LAHSOSession

CSV_SUFFIXES = frozenset({".csv"})
PKL_SUFFIXES = frozenset({".pkl"})

DATASET_UPLOAD_FIELDS = {
    "network": CSV_SUFFIXES,
    "network_barge": CSV_SUFFIXES,
    "network_train": CSV_SUFFIXES,
    "network_truck": CSV_SUFFIXES,
    "fixed_schedule": CSV_SUFFIXES,
    "truck_schedule": CSV_SUFFIXES,
    "demand": CSV_SUFFIXES,
    "mode_costs": CSV_SUFFIXES,
}


def get_default_config_payload() -> dict[str, Any]:
    config = Config()
    return {
        "success": True,
        "config": {
            "storage_cost": config.storage_cost,
            "delay_penalty": config.delay_penalty,
            "undelivered_penalty": config.undelivered_penalty,
            "learning_rate": 0.5,
            "exploratory_rate": 0.95,
            "num_simulations": 50000,
            "simulation_duration": 42,
            "impl_num_simulations": 20,
            "impl_duration": 35,
        },
        "default_files": {
            "network": project_relative(config.network_path),
            "network_barge": project_relative(config.network_barge_path),
            "network_train": project_relative(config.network_train_path),
            "network_truck": project_relative(config.network_truck_path),
            "fixed_schedule": project_relative(config.fixed_service_schedule_path),
            "truck_schedule": project_relative(config.truck_schedule_path),
            "demand": project_relative(config.demand_default_path),
            "mode_costs": project_relative(config.mode_costs_path),
            "service_disruptions": project_relative(config.s_disruption_path),
            "demand_disruptions": project_relative(config.d_disruption_path),
            "q_table": project_relative(config.q_table_path),
        },
    }


def validate_dataset(
    payload: Mapping[str, Any],
    lahso_session: LAHSOSession,
    files: Mapping[str, FileStorage] | None = None,
) -> dict[str, Any]:
    from lahso.service_to_path import service_to_path

    compute_kbest = _as_bool(payload.get("compute_kbest"), default=True)
    uploads = _save_uploads(lahso_session, files, DATASET_UPLOAD_FIELDS)

    config = Config(
        print_event_enabled=False,
        demand_type="kbest" if compute_kbest else "default",
        storage_cost=int(payload.get("storage_cost", 1)),
        delay_penalty=int(payload.get("delay_penalty", 1)),
        undelivered_penalty=int(payload.get("undelivered_penalty", 100)),
        network_path=uploads.get("network"),
        network_barge_path=uploads.get("network_barge"),
        network_train_path=uploads.get("network_train"),
        network_truck_path=uploads.get("network_truck"),
        fixed_service_schedule_path=uploads.get("fixed_schedule"),
        truck_schedule_path=uploads.get("truck_schedule"),
        demand_default_path=uploads.get("demand"),
        mode_costs_path=uploads.get("mode_costs"),
    )
    _configure_session_generated_dataset_paths(config, lahso_session)

    service_to_path(config)
    if compute_kbest:
        from lahso.kbest import kbest

        kbest(config)

    lahso_session.config = config

    return {
        "success": True,
        "message": "Dataset validated successfully",
        "kbest_generated": compute_kbest,
    }


def configure_training(
    payload: Mapping[str, Any],
    lahso_session: LAHSOSession,
    files: Mapping[str, FileStorage] | None = None,
) -> dict[str, Any]:
    from lahso.model_input import ModelInput

    service_disruption_upload = _save_upload(
        lahso_session,
        files,
        "service_disruptions",
        CSV_SUFFIXES,
    )
    demand_disruption_upload = _save_upload(
        lahso_session,
        files,
        "demand_disruptions",
        CSV_SUFFIXES,
    )
    if service_disruption_upload is not None:
        lahso_session.config.s_disruption_path = service_disruption_upload
    if demand_disruption_upload is not None:
        lahso_session.config.d_disruption_path = demand_disruption_upload

    lahso_session.config.alpha = float(payload.get("learning_rate", 0.5))
    lahso_session.config.epsilon = float(payload.get("exploratory_rate", 0.95))
    lahso_session.config.number_of_simulation = int(
        payload.get("num_simulations", 50000)
    )
    lahso_session.config.simulation_duration = (
        int(payload.get("simulation_duration", 42)) * 1440
    )
    lahso_session.config.extract_q_table = 1
    continue_training = _as_bool(payload.get("continue_training"), default=False)
    lahso_session.config.start_from_0 = not continue_training

    if continue_training:
        last_q_table_upload = _save_upload(
            lahso_session,
            files,
            "last_q_table",
            PKL_SUFFIXES,
        )
        last_total_cost_upload = _save_upload(
            lahso_session,
            files,
            "last_total_cost",
            PKL_SUFFIXES,
        )
        last_reward_upload = _save_upload(
            lahso_session,
            files,
            "last_reward",
            PKL_SUFFIXES,
        )
        if last_q_table_upload is not None:
            lahso_session.config.q_table_path = last_q_table_upload
        if last_total_cost_upload is not None:
            lahso_session.config.tc_path = last_total_cost_upload
        if last_reward_upload is not None:
            lahso_session.config.tr_path = last_reward_upload
    else:
        lahso_session.config.q_table_path = Q_TABLES_DIR / "default_q_table_output.pkl"
        lahso_session.config.tc_path = (
            TRAINING_METRICS_DIR / "default_total_cost_output.pkl"
        )
        lahso_session.config.tr_path = (
            TRAINING_METRICS_DIR / "default_total_reward_output.pkl"
        )

    lahso_session.total_episodes = lahso_session.config.number_of_simulation
    lahso_session.model_input = ModelInput(lahso_session.config)

    return {
        "success": True,
        "message": "Training configuration updated",
        "total_episodes": lahso_session.total_episodes,
    }


def configure_implementation(
    payload: Mapping[str, Any],
    lahso_session: LAHSOSession,
    files: Mapping[str, FileStorage] | None = None,
) -> dict[str, Any]:
    from lahso.model_input import ModelInput

    service_disruption_upload = _save_upload(
        lahso_session,
        files,
        "service_disruptions",
        CSV_SUFFIXES,
    )
    demand_disruption_upload = _save_upload(
        lahso_session,
        files,
        "demand_disruptions",
        CSV_SUFFIXES,
    )
    q_table_upload = _save_upload(lahso_session, files, "q_table", PKL_SUFFIXES)

    config = Config(
        s_disruption_path=(
            service_disruption_upload
            or RAW_DISRUPTIONS_DIR / "No_Service_Disruption_Profile.csv"
        ),
        d_disruption_path=(
            demand_disruption_upload
            or RAW_DISRUPTIONS_DIR / "No_Request_Disruption_Profile.csv"
        ),
        number_of_simulation=int(payload.get("num_simulations", 20)),
        simulation_duration=int(payload.get("simulation_duration", 35)) * 1440,
        start_from_0=True,
        q_table_path=q_table_upload or Q_TABLES_DIR / "default_q_table_output.pkl",
        policy_name=payload.get("policy", "gp"),
        extract_shipment_output=True,
    )

    _copy_dataset_config(lahso_session.config, config)

    lahso_session.config = config
    lahso_session.model_input = ModelInput(config)

    return {
        "success": True,
        "message": "Implementation configuration updated",
    }


def compare_result_files(payload: Mapping[str, Any]) -> dict[str, Any]:
    file1_path = payload.get("file1_path")
    file2_path = payload.get("file2_path")

    if not file1_path or not file2_path:
        return {"success": False, "error": "Both files required"}

    label1 = payload.get("label1", "Policy 1")
    label2 = payload.get("label2", "Policy 2")
    comparison_data = comparison(file1_path, file2_path, label1, label2)

    return {
        "success": True,
        "comparison_data": dataframe_records(comparison_data),
        "message": "Comparison completed successfully",
    }


def compare_result_uploads(
    form: Mapping[str, Any],
    files: Mapping[str, FileStorage],
) -> dict[str, Any]:
    file1 = files.get("file1")
    file2 = files.get("file2")

    if not _is_csv_upload(file1) or not _is_csv_upload(file2):
        return {"success": False, "error": "Two CSV uploads are required"}

    label1 = str(form.get("label1") or "Policy 1")
    label2 = str(form.get("label2") or "Policy 2")

    file1.stream.seek(0)
    file2.stream.seek(0)
    comparison_data = comparison(file1.stream, file2.stream, label1, label2)

    return {
        "success": True,
        "comparison_data": dataframe_records(comparison_data),
        "message": "Comparison completed successfully",
    }


def _is_csv_upload(file: FileStorage | None) -> bool:
    if file is None or not file.filename:
        return False
    return file.filename.lower().endswith(".csv")


def _save_uploads(
    lahso_session: LAHSOSession,
    files: Mapping[str, FileStorage] | None,
    field_suffixes: Mapping[str, frozenset[str]],
) -> dict[str, Path]:
    uploads: dict[str, Path] = {}
    for field_name, suffixes in field_suffixes.items():
        uploaded_path = _save_upload(lahso_session, files, field_name, suffixes)
        if uploaded_path is not None:
            uploads[field_name] = uploaded_path
    return uploads


def _save_upload(
    lahso_session: LAHSOSession,
    files: Mapping[str, FileStorage] | None,
    field_name: str,
    allowed_suffixes: frozenset[str],
) -> Path | None:
    upload = files.get(field_name) if files else None
    if upload is None or not upload.filename:
        return None

    suffix = Path(upload.filename).suffix.lower()
    if suffix not in allowed_suffixes:
        readable_field = field_name.replace("_", " ")
        allowed = ", ".join(sorted(allowed_suffixes))
        msg = f"{readable_field} must use one of these extensions: {allowed}"
        raise ValueError(msg)

    destination_dir = _session_upload_dir(lahso_session) / field_name
    ensure_directories(destination_dir)
    filename = secure_filename(upload.filename) or f"{field_name}{suffix}"
    destination = destination_dir / filename
    upload.save(destination)
    return destination


def _session_upload_dir(lahso_session: LAHSOSession) -> Path:
    session_slug = secure_filename(lahso_session.session_id) or "session"
    return UPLOADS_DIR / session_slug


def _configure_session_generated_dataset_paths(
    config: Config,
    lahso_session: LAHSOSession,
) -> None:
    generated_dir = _session_upload_dir(lahso_session) / "generated"
    ensure_directories(generated_dir)
    config.possible_paths_path = generated_dir / "Possible_Paths.csv"
    config.demand_kbest_path = (
        generated_dir
        / f"{config.demand_default_path.stem}_kbest{config.demand_default_path.suffix}"
    )


def _as_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _copy_dataset_config(source: Config, target: Config) -> None:
    dataset_fields = (
        "network_path",
        "network_barge_path",
        "network_train_path",
        "network_truck_path",
        "possible_paths_path",
        "fixed_service_schedule_path",
        "truck_schedule_path",
        "demand_default_path",
        "demand_planned_path",
        "demand_kbest_path",
        "mode_costs_path",
        "storage_cost",
        "delay_penalty",
        "undelivered_penalty",
        "demand_type",
    )
    for field_name in dataset_fields:
        value = getattr(source, field_name)
        if value is not None:
            setattr(target, field_name, value)
