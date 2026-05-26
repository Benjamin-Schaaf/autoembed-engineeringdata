"""Sample engineering simulation documents for the demo."""

from __future__ import annotations

from datetime import datetime, timezone


def _base_simulations() -> list[dict]:
    now = datetime.now(timezone.utc)
    return [
        {
            "simulation_id": "SIM-001",
            "name": "Turbine Blade CFD",
            "domain": "fluid_dynamics",
            "description": (
                "Computational fluid dynamics study of airflow around a turbine blade "
                "at 15,000 RPM. Evaluates boundary layer separation, wake turbulence, "
                "and pressure distribution on the suction side."
            ),
            "parameters": {
                "rpm": 15000,
                "inlet_velocity_m_s": 120,
                "mesh_cells": 4_200_000,
                "turbulence_model": "k-omega SST",
            },
            "status": "completed",
            "tags": ["cfd", "turbomachinery", "aerospace"],
            "created_at": now,
        },
        {
            "simulation_id": "SIM-002",
            "name": "Crashworthiness FEA",
            "domain": "structural",
            "description": (
                "Finite element analysis of frontal crash impact on an aluminum "
                "vehicle frame. Measures energy absorption, crumple zone deformation, "
                "and occupant compartment intrusion at 56 km/h."
            ),
            "parameters": {
                "impact_speed_kmh": 56,
                "material": "AA6061-T6",
                "solver": "explicit dynamics",
                "duration_ms": 150,
            },
            "status": "completed",
            "tags": ["fea", "automotive", "safety"],
            "created_at": now,
        },
        {
            "simulation_id": "SIM-003",
            "name": "Battery Thermal Runaway",
            "domain": "thermal",
            "description": (
                "Coupled thermal-electrochemical simulation of lithium-ion cell "
                "thermal runaway propagation in a 48-module pack. Tracks temperature "
                "gradients, vent gas release, and time-to-thermal-event."
            ),
            "parameters": {
                "cell_format": "21700",
                "ambient_c": 25,
                "trigger": "nail penetration",
                "modules": 48,
            },
            "status": "running",
            "tags": ["thermal", "battery", "ev"],
            "created_at": now,
        },
        {
            "simulation_id": "SIM-004",
            "name": "Monte Carlo Portfolio Risk",
            "domain": "finance",
            "description": (
                "Monte Carlo simulation of portfolio value-at-risk under correlated "
                "equity and credit shocks. Runs 500,000 paths with fat-tailed return "
                "distributions and stress scenarios for liquidity crunches."
            ),
            "parameters": {
                "paths": 500_000,
                "horizon_days": 10,
                "confidence": 0.99,
                "assets": 120,
            },
            "status": "completed",
            "tags": ["monte-carlo", "risk", "finance"],
            "created_at": now,
        },
        {
            "simulation_id": "SIM-005",
            "name": "Urban Wind Flow LES",
            "domain": "fluid_dynamics",
            "description": (
                "Large-eddy simulation of wind flow between high-rise buildings in "
                "a downtown canyon. Quantifies pedestrian-level gusts, vortex shedding, "
                "and microclimate effects for pedestrian comfort analysis."
            ),
            "parameters": {
                "wind_speed_m_s": 12,
                "building_count": 8,
                "resolution_m": 2,
                "duration_s": 600,
            },
            "status": "completed",
            "tags": ["les", "urban", "wind"],
            "created_at": now,
        },
        {
            "simulation_id": "SIM-006",
            "name": "Drug Diffusion in Tissue",
            "domain": "biomedical",
            "description": (
                "Agent-based diffusion model of drug delivery through porous tumor "
                "tissue with heterogeneous vasculature. Predicts concentration profiles "
                "over 72 hours for dosing optimization."
            ),
            "parameters": {
                "dose_mg": 50,
                "porosity": 0.62,
                "simulation_hours": 72,
                "agents": 250_000,
            },
            "status": "queued",
            "tags": ["biomedical", "agent-based", "pharma"],
            "created_at": now,
        },
    ]


def build_document(payload: dict, version: str) -> dict:
    """Wrap payload for v2 (nested under ``data``) or return flat doc for v1."""
    if version == "v2":
        return {"data": payload}
    return payload


def sample_simulations(version: str) -> list[dict]:
    """Return sample simulation documents for the requested schema version."""
    version = version.lower()
    if version not in {"v1", "v2"}:
        raise ValueError(f"Unsupported schema version: {version!r}")
    return [build_document(sim, version) for sim in _base_simulations()]


def new_simulation(version: str, simulation_id: str | None = None) -> dict:
    """Create a single new simulation document suitable for insert demos."""
    payload = {
        "simulation_id": simulation_id or "SIM-NEW-001",
        "name": "Hypersonic Re-entry Heat Shield",
        "domain": "aerospace",
        "description": (
            "Ablation and radiative heating simulation for a ceramic heat shield "
            "during hypersonic re-entry at Mach 25. Models surface recession, "
            "shock-layer radiation, and thermal protection system performance."
        ),
        "parameters": {
            "mach": 25,
            "altitude_km": 80,
            "material": "PICA-X",
            "duration_s": 420,
        },
        "status": "completed",
        "tags": ["hypersonic", "thermal", "aerospace"],
        "created_at": datetime.now(timezone.utc),
    }
    return build_document(payload, version)
