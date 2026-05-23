import pandas as pd

from dora_analyzer.calculate_metrics import (
    calculate_adapted_cfr,
    calculate_deployment_frequency,
    calculate_lead_time_metrics,
)


def test_deployment_frequency_calculation() -> None:
    deployments_df = pd.DataFrame(
        {
            "tag_name": ["v1.0.0", "v1.1.0", "v1.2.0"],
            "published_at": ["2024-01-02T00:00:00Z", "2024-01-15T00:00:00Z", "2024-02-01T00:00:00Z"],
        }
    )
    result = calculate_deployment_frequency(deployments_df, "M")
    january = result[result["period"] == "2024-01"]["metric_value"].iloc[0]
    february = result[result["period"] == "2024-02"]["metric_value"].iloc[0]
    assert january == 2
    assert february == 1


def test_lead_time_calculation() -> None:
    commits_df = pd.DataFrame(
        {
            "deployment_date": ["2024-01-10T00:00:00Z", "2024-01-10T00:00:00Z"],
            "lead_time_days": [2.0, 4.0],
        }
    )
    result = calculate_lead_time_metrics(commits_df, "M")
    mean_value = result[result["metric_name"] == "lead_time_days_mean"]["metric_value"].iloc[0]
    assert mean_value == 3.0


def test_adapted_cfr_calculation() -> None:
    deployments_df = pd.DataFrame(
        {
            "tag_name": ["v1.0.0", "v1.1.0"],
            "published_at": ["2024-01-02T00:00:00Z", "2024-01-15T00:00:00Z"],
        }
    )
    recovery_df = pd.DataFrame(
        {
            "recovery_deployment_tag": ["v1.1.0"],
            "recovery_deployment_date": ["2024-01-15T00:00:00Z"],
            "recovery_time_days": [5.0],
        }
    )
    result = calculate_adapted_cfr(deployments_df, recovery_df, "M")
    rate = result["metric_value"].iloc[0]
    assert rate == 0.5
