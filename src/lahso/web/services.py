from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from lahso.bar_chart_plot import comparison
from lahso.config import Config
from lahso.kbest import kbest
from lahso.model_input import ModelInput
from lahso.paths import (
    Q_TABLES_DIR,
    RAW_DISRUPTIONS_DIR,
    TRAINING_METRICS_DIR,
    project_relative,
)
from lahso.service_to_path import service_to_path
from lahso.web.state import LAHSOSession


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
) -> dict[str, Any]:
    compute_kbest = bool(payload.get("compute_kbest", True))
    config = Config(
        print_event_enabled=False,
        demand_type="kbest" if compute_kbest else "default",
        storage_cost=int(payload.get("storage_cost", 1)),
        delay_penalty=int(payload.get("delay_penalty", 1)),
        undelivered_penalty=int(payload.get("undelivered_penalty", 100)),
    )

    service_to_path(config)
    if compute_kbest:
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
) -> dict[str, Any]:
    default_config = Config()
    lahso_session.config.s_disruption_path = default_config.s_disruption_path
    lahso_session.config.d_disruption_path = default_config.d_disruption_path
    lahso_session.config.alpha = float(payload.get("learning_rate", 0.5))
    lahso_session.config.epsilon = float(payload.get("exploratory_rate", 0.95))
    lahso_session.config.number_of_simulation = int(
        payload.get("num_simulations", 50000)
    )
    lahso_session.config.simulation_duration = (
        int(payload.get("simulation_duration", 42)) * 1440
    )
    lahso_session.config.extract_q_table = 1
    lahso_session.config.start_from_0 = not payload.get("continue_training", False)
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
) -> dict[str, Any]:
    config = Config(
        s_disruption_path=RAW_DISRUPTIONS_DIR / "No_Service_Disruption_Profile.csv",
        d_disruption_path=RAW_DISRUPTIONS_DIR / "No_Request_Disruption_Profile.csv",
        number_of_simulation=int(payload.get("num_simulations", 20)),
        simulation_duration=int(payload.get("simulation_duration", 35)) * 1440,
        start_from_0=True,
        q_table_path=Q_TABLES_DIR / "default_q_table_output.pkl",
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
        "comparison_data": comparison_data.to_dict("records"),
        "message": "Comparison completed successfully",
    }


def _copy_dataset_config(source: Config, target: Config) -> None:
    dataset_fields = (
        "network_path",
        "network_barge_path",
        "network_train_path",
        "network_truck_path",
        "fixed_service_schedule_path",
        "truck_schedule_path",
        "demand_default_path",
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
