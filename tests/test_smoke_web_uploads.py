from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

import pytest
from werkzeug.datastructures import FileStorage, MultiDict

from lahso.web import services
from lahso.web.state import LAHSOSession


class DummyModelInput:
    def __init__(self, config: Any) -> None:
        self.config = config


def test_dataset_uploads_are_saved_to_session_config(monkeypatch, tmp_path: Path):
    captured_config = None

    def fake_service_to_path(config):
        nonlocal captured_config
        captured_config = config

    import lahso.service_to_path as service_to_path_module

    monkeypatch.setattr(services, "UPLOADS_DIR", tmp_path)
    monkeypatch.setattr(service_to_path_module, "service_to_path", fake_service_to_path)

    lahso_session = LAHSOSession("dataset-upload-session")
    result = services.validate_dataset(
        MultiDict(
            [
                ("compute_kbest", "false"),
                ("storage_cost", "3"),
                ("delay_penalty", "4"),
                ("undelivered_penalty", "120"),
            ]
        ),
        lahso_session,
        MultiDict(
            [
                ("network", _upload("network.csv", b"N\nDelta\nVenlo\n")),
                ("demand", _upload("custom_demand.csv", b"Demand_ID\nD1\n")),
            ]
        ),
    )

    assert result["success"] is True
    assert captured_config is lahso_session.config
    assert lahso_session.config.network_path == (
        tmp_path / "dataset-upload-session" / "network" / "network.csv"
    )
    assert lahso_session.config.demand_default_path == (
        tmp_path / "dataset-upload-session" / "demand" / "custom_demand.csv"
    )
    assert lahso_session.config.possible_paths_path == (
        tmp_path / "dataset-upload-session" / "generated" / "Possible_Paths.csv"
    )
    assert lahso_session.config.demand_kbest_path == (
        tmp_path / "dataset-upload-session" / "generated" / "custom_demand_kbest.csv"
    )
    assert lahso_session.config.demand_type == "default"
    assert lahso_session.config.storage_cost == 3


def test_training_settings_uploads_replace_default_artifact_paths(
    monkeypatch,
    tmp_path: Path,
):
    import lahso.model_input as model_input_module

    monkeypatch.setattr(services, "UPLOADS_DIR", tmp_path)
    monkeypatch.setattr(model_input_module, "ModelInput", DummyModelInput)

    lahso_session = LAHSOSession("training-upload-session")
    result = services.configure_training(
        MultiDict(
            [
                ("service_disruptions", ""),
                ("learning_rate", "0.25"),
                ("exploratory_rate", "0.75"),
                ("num_simulations", "12"),
                ("simulation_duration", "8"),
                ("continue_training", "true"),
            ]
        ),
        lahso_session,
        MultiDict(
            [
                ("service_disruptions", _upload("service.csv", b"Profile\nProfile1\n")),
                ("demand_disruptions", _upload("demand.csv", b"Profile\nProfile1\n")),
                ("last_q_table", _upload("q_table.pkl", b"pickle")),
                ("last_total_cost", _upload("total_cost.pkl", b"pickle")),
                ("last_reward", _upload("reward.pkl", b"pickle")),
            ]
        ),
    )

    assert result["success"] is True
    assert lahso_session.config.s_disruption_path == (
        tmp_path / "training-upload-session" / "service_disruptions" / "service.csv"
    )
    assert lahso_session.config.d_disruption_path == (
        tmp_path / "training-upload-session" / "demand_disruptions" / "demand.csv"
    )
    assert lahso_session.config.q_table_path == (
        tmp_path / "training-upload-session" / "last_q_table" / "q_table.pkl"
    )
    assert lahso_session.config.tc_path == (
        tmp_path / "training-upload-session" / "last_total_cost" / "total_cost.pkl"
    )
    assert lahso_session.config.tr_path == (
        tmp_path / "training-upload-session" / "last_reward" / "reward.pkl"
    )
    assert lahso_session.config.start_from_0 is False
    assert lahso_session.config.alpha == 0.25
    assert lahso_session.total_episodes == 12
    assert isinstance(lahso_session.model_input, DummyModelInput)


def test_implementation_uploads_keep_dataset_paths(monkeypatch, tmp_path: Path):
    import lahso.model_input as model_input_module

    monkeypatch.setattr(services, "UPLOADS_DIR", tmp_path)
    monkeypatch.setattr(model_input_module, "ModelInput", DummyModelInput)

    lahso_session = LAHSOSession("implementation-upload-session")
    lahso_session.config.possible_paths_path = tmp_path / "possible_paths.csv"
    lahso_session.config.demand_default_path = tmp_path / "custom_demand.csv"
    lahso_session.config.demand_kbest_path = tmp_path / "custom_demand_kbest.csv"

    result = services.configure_implementation(
        MultiDict(
            [
                ("policy", "aw"),
                ("num_simulations", "2"),
                ("simulation_duration", "3"),
            ]
        ),
        lahso_session,
        MultiDict(
            [
                ("service_disruptions", _upload("service.csv", b"Profile\nProfile1\n")),
                ("demand_disruptions", _upload("demand.csv", b"Profile\nProfile1\n")),
                ("q_table", _upload("q_table.pkl", b"pickle")),
            ]
        ),
    )

    assert result["success"] is True
    assert lahso_session.config.policy_name == "aw"
    assert lahso_session.config.s_disruption_path == (
        tmp_path
        / "implementation-upload-session"
        / "service_disruptions"
        / "service.csv"
    )
    assert lahso_session.config.d_disruption_path == (
        tmp_path
        / "implementation-upload-session"
        / "demand_disruptions"
        / "demand.csv"
    )
    assert lahso_session.config.q_table_path == (
        tmp_path / "implementation-upload-session" / "q_table" / "q_table.pkl"
    )
    assert lahso_session.config.possible_paths_path == tmp_path / "possible_paths.csv"
    assert lahso_session.config.demand_default_path == tmp_path / "custom_demand.csv"
    assert lahso_session.config.demand_kbest_path == (
        tmp_path / "custom_demand_kbest.csv"
    )
    assert isinstance(lahso_session.model_input, DummyModelInput)


def test_upload_validation_rejects_wrong_extension(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(services, "UPLOADS_DIR", tmp_path)

    with pytest.raises(ValueError) as exc_info:
        services.configure_implementation(
            MultiDict([("policy", "gp")]),
            LAHSOSession("bad-upload-session"),
            MultiDict([("q_table", _upload("q_table.csv", b"not a pickle"))]),
        )

    assert str(exc_info.value) == "q table must use one of these extensions: .pkl"


def _upload(filename: str, body: bytes) -> FileStorage:
    return FileStorage(stream=BytesIO(body), filename=filename)
