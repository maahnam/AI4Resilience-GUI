from __future__ import annotations

import textwrap
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", category=DeprecationWarning)

import pandas as pd
import pytest

from lahso.config import Config
from lahso.model_input import ModelInput
from lahso.paths import (
    PROCESSED_KBEST_DIR,
    PROCESSED_PATHS_DIR,
    Q_TABLES_DIR,
    RAW_COSTS_DIR,
    RAW_DEMAND_DIR,
    RAW_DISRUPTIONS_DIR,
    RAW_NETWORK_DIR,
    RAW_SCHEDULES_DIR,
    SIMULATION_OUTPUTS_DIR,
    TRAINING_METRICS_DIR,
)
from lahso.service_to_path import service_to_path


def _write_csv(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).strip() + "\n", encoding="utf-8")


@pytest.fixture
def minimal_config(tmp_path: Path) -> Config:
    data_root = tmp_path / "data"
    raw_root = data_root / "raw"
    processed_root = data_root / "processed"
    artifacts_root = tmp_path / "artifacts"

    network_dir = raw_root / "network"
    schedules_dir = raw_root / "schedules"
    demand_dir = raw_root / "demand"
    disruptions_dir = raw_root / "disruptions"
    costs_dir = raw_root / "costs"
    possible_paths_path = processed_root / "possible_paths" / "Possible_Paths.csv"

    _write_csv(
        network_dir / "Network.csv",
        """
        N,Alpha,Beta
        Alpha,0,10
        Beta,10,0
        """,
    )
    for filename in ("Network_Barge.csv", "Network_Train.csv", "Network_Truck.csv"):
        _write_csv(
            network_dir / filename,
            """
            N,Alpha,Beta
            Alpha,0,10
            Beta,10,0
            """,
        )

    _write_csv(
        schedules_dir / "Fixed Vehicle Schedule.csv",
        """
        Service_ID,Mode,Origin,Destination,Departure,Arrival,Travel Time,Capacity,Speed,Travel Cost
        Barge01,Barge,Alpha,Beta,1,2,1,100,10,5
        """,
    )
    _write_csv(
        schedules_dir / "Truck Schedule.csv",
        """
        Service_ID,Origin,Destination,Departure,Arrival,Travel Time,Capacity,Speed,Travel Cost
        Truck01,Alpha,Beta,99999,99999,0.5,99999,50,6
        """,
    )
    _write_csv(
        costs_dir / "Mode Costs.csv",
        """
        Unnamed: 0,Barge,Train,Truck
        travel_cost1,1.0,1.5,2.0
        travel_cost2,0.1,0.2,0.3
        handling_cost,3.0,4.0,5.0
        """,
    )
    _write_csv(
        demand_dir / "shipment_requests_200_3w_default.csv",
        """
        Demand_ID,Origin,Destination,Release Time,Due Time,Volume,Announce Time,Solution_List
        Request1,Alpha,Beta,0,24,1,0,0
        """,
    )
    _write_csv(
        disruptions_dir / "No_Service_Disruption_Profile.csv",
        """
        Profile,Description,Probability,Sevirity,Location,Impact Type,LB Duration,UB Duration,LB Capacity,UB Capacity,Occurrence per Year,Lambda
        Profile1,None,Low,Low,Beta,Delay,0,0,0,0,0%,0.0
        """,
    )
    _write_csv(
        disruptions_dir / "No_Request_Disruption_Profile.csv",
        """
        Profile,Description,Probability,Sevirity,Location,Impact Type,LB Time,UB Time,LB Volume,UB Volume,Occurrence per Year,Lambda
        Profile6,None,Low,Low,Shipment,Volume,0,0,0,0,0%,0.0
        """,
    )

    config = Config(
        start_from_0=True,
        network_path=network_dir / "Network.csv",
        network_barge_path=network_dir / "Network_Barge.csv",
        network_train_path=network_dir / "Network_Train.csv",
        network_truck_path=network_dir / "Network_Truck.csv",
        fixed_service_schedule_path=schedules_dir / "Fixed Vehicle Schedule.csv",
        truck_schedule_path=schedules_dir / "Truck Schedule.csv",
        demand_default_path=demand_dir / "shipment_requests_200_3w_default.csv",
        demand_type="default",
        mode_costs_path=costs_dir / "Mode Costs.csv",
        s_disruption_path=disruptions_dir / "No_Service_Disruption_Profile.csv",
        d_disruption_path=disruptions_dir / "No_Request_Disruption_Profile.csv",
        possible_paths_path=possible_paths_path,
        q_table_path=artifacts_root / "models" / "q_tables" / "fixture_q_table.pkl",
        output_path=artifacts_root / "runs" / "simulation_outputs" / "fixture_output.csv",
    )
    config.tc_path = artifacts_root / "metrics" / "training" / "fixture_total_cost.pkl"
    config.tr_path = artifacts_root / "metrics" / "training" / "fixture_total_reward.pkl"
    config.training_output_path = (
        artifacts_root / "metrics" / "training" / "fixture_training_output.csv"
    )
    return config


def test_config_defaults_use_reorganized_layout() -> None:
    config = Config()

    assert config.network_path == RAW_NETWORK_DIR / "Network.csv"
    assert config.fixed_service_schedule_path == (
        RAW_SCHEDULES_DIR / "Fixed Vehicle Schedule.csv"
    )
    assert config.mode_costs_path == RAW_COSTS_DIR / "Mode Costs.csv"
    assert config.demand_default_path == (
        RAW_DEMAND_DIR / "shipment_requests_200_3w_default.csv"
    )
    assert config.s_disruption_path == (
        RAW_DISRUPTIONS_DIR / "Service_Disruption_Profile_Def.csv"
    )
    assert config.possible_paths_path == PROCESSED_PATHS_DIR / "Possible_Paths.csv"
    assert config.demand_kbest_path == (
        PROCESSED_KBEST_DIR / "shipment_requests_200_3w_default_kbest.csv"
    )
    assert config.q_table_path == Q_TABLES_DIR / config.q_name
    assert config.tc_path == TRAINING_METRICS_DIR / config.tc_name
    assert config.output_path.parent == SIMULATION_OUTPUTS_DIR


def test_service_to_path_writes_processed_paths(minimal_config: Config) -> None:
    service_to_path(minimal_config)

    assert minimal_config.possible_paths_path.exists()
    path_df = pd.read_csv(minimal_config.possible_paths_path)

    assert not path_df.empty
    assert {"origin", "destination", "service_ids", "total_cost"}.issubset(
        path_df.columns
    )
    assert ((path_df["origin"] == "Alpha") & (path_df["destination"] == "Beta")).any()


def test_model_input_loads_from_reorganized_paths(minimal_config: Config) -> None:
    service_to_path(minimal_config)

    model_input = ModelInput(minimal_config)

    assert model_input.node_list == ["Alpha", "Beta"]
    assert len(model_input.request_list) == 1
    assert model_input.request.iloc[0]["Demand_ID"] == "Request1"
    assert model_input.possible_paths_ref["origin"].iloc[0] == "Alpha"
    assert minimal_config.q_table_path.name == "fixture_q_table.pkl"
