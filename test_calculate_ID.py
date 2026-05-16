import pytest
import tempfile
import os
import toml

from calculate_ID import calculate_weighted_sum, calculate_intelligence_density, validate_components


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_toml(tmp_path, intelligence, resources):
    """Write a minimal TOML file and return its path."""
    config = {
        "IntelligenceComponents": intelligence,
        "ResourceComponents": resources,
    }
    path = tmp_path / "spec.toml"
    with open(path, "w") as f:
        toml.dump(config, f)
    return str(path)


SIMPLE_INTELLIGENCE = {
    "performance":    {"value": 0.9, "weight": 0.4},
    "generalization": {"value": 0.8, "weight": 0.3},
    "learning":       {"value": 0.7, "weight": 0.2},
    "interpretability": {"value": 0.6, "weight": 0.1},
}

SIMPLE_RESOURCES = {
    "model_size":   {"value": 0.5, "weight": 0.5},
    "complexity":   {"value": 0.6, "weight": 0.3},
    "energy":       {"value": 0.7, "weight": 0.2},
}


# ---------------------------------------------------------------------------
# calculate_weighted_sum
# ---------------------------------------------------------------------------

class TestCalculateWeightedSum:
    def test_known_result(self):
        # (0.4*0.9) + (0.3*0.8) + (0.2*0.7) + (0.1*0.6) = 0.8
        result = calculate_weighted_sum(SIMPLE_INTELLIGENCE)
        assert abs(result - 0.8) < 1e-9

    def test_single_component(self):
        components = {"only": {"value": 0.75, "weight": 1.0}}
        assert calculate_weighted_sum(components) == pytest.approx(0.75)

    def test_auto_normalizes_weights(self, capsys):
        # Weights sum to 2.0 instead of 1.0 — result should still equal the
        # normalized-weight version.
        doubled = {k: {"value": v["value"], "weight": v["weight"] * 2}
                   for k, v in SIMPLE_INTELLIGENCE.items()}
        result = calculate_weighted_sum(doubled)
        assert abs(result - 0.8) < 1e-9

    def test_auto_normalize_prints_warning(self, capsys):
        doubled = {k: {"value": v["value"], "weight": v["weight"] * 2}
                   for k, v in SIMPLE_INTELLIGENCE.items()}
        calculate_weighted_sum(doubled)
        captured = capsys.readouterr()
        assert "Warning" in captured.err
        assert "auto-normalizing" in captured.err

    def test_no_warning_when_weights_sum_to_one(self, capsys):
        calculate_weighted_sum(SIMPLE_INTELLIGENCE)
        captured = capsys.readouterr()
        assert captured.err == ""

    def test_zero_total_weight_raises(self):
        components = {"a": {"value": 0.5, "weight": 0.0}}
        with pytest.raises(ValueError, match="weights must not all be zero"):
            calculate_weighted_sum(components)


# ---------------------------------------------------------------------------
# validate_components
# ---------------------------------------------------------------------------

class TestValidateComponents:
    def test_valid_passes(self):
        validate_components(SIMPLE_INTELLIGENCE, "IntelligenceComponents")  # no error

    def test_value_above_one_raises(self):
        bad = {"x": {"value": 1.1, "weight": 0.5}}
        with pytest.raises(ValueError, match="outside \\[0, 1\\]"):
            validate_components(bad, "Test")

    def test_value_below_zero_raises(self):
        bad = {"x": {"value": -0.1, "weight": 0.5}}
        with pytest.raises(ValueError, match="outside \\[0, 1\\]"):
            validate_components(bad, "Test")

    def test_negative_weight_raises(self):
        bad = {"x": {"value": 0.5, "weight": -0.1}}
        with pytest.raises(ValueError, match="must be non-negative"):
            validate_components(bad, "Test")

    def test_boundary_values_pass(self):
        components = {
            "zero": {"value": 0.0, "weight": 0.5},
            "one":  {"value": 1.0, "weight": 0.5},
        }
        validate_components(components, "Test")  # no error


# ---------------------------------------------------------------------------
# calculate_intelligence_density
# ---------------------------------------------------------------------------

class TestCalculateIntelligenceDensity:
    def test_known_result(self, tmp_path):
        path = make_toml(tmp_path, SIMPLE_INTELLIGENCE, SIMPLE_RESOURCES)
        results = calculate_intelligence_density(path)
        # I = 0.8, R = (0.5*0.5 + 0.3*0.6 + 0.2*0.7) = 0.57
        assert abs(results["Intelligence Measure"] - 0.8) < 1e-9
        assert abs(results["Resource Consumption"] - 0.57) < 1e-9
        assert abs(results["Intelligence Density"] - (0.8 / 0.57)) < 1e-6

    def test_id_increases_with_intelligence(self, tmp_path):
        base_dir = tmp_path / "base"
        high_dir = tmp_path / "high"
        base_dir.mkdir()
        high_dir.mkdir()
        base_path = make_toml(base_dir, SIMPLE_INTELLIGENCE, SIMPLE_RESOURCES)
        high_intel = {k: {"value": min(v["value"] + 0.1, 1.0), "weight": v["weight"]}
                      for k, v in SIMPLE_INTELLIGENCE.items()}
        high_path = make_toml(high_dir, high_intel, SIMPLE_RESOURCES)

        base = calculate_intelligence_density(base_path)
        high = calculate_intelligence_density(high_path)
        assert high["Intelligence Density"] > base["Intelligence Density"]

    def test_id_decreases_with_more_resources(self, tmp_path):
        base_dir = tmp_path / "base"
        heavy_dir = tmp_path / "heavy"
        base_dir.mkdir()
        heavy_dir.mkdir()
        base_path = make_toml(base_dir, SIMPLE_INTELLIGENCE, SIMPLE_RESOURCES)
        heavy_res = {k: {"value": min(v["value"] + 0.2, 1.0), "weight": v["weight"]}
                     for k, v in SIMPLE_RESOURCES.items()}
        heavy_path = make_toml(heavy_dir, SIMPLE_INTELLIGENCE, heavy_res)

        base = calculate_intelligence_density(base_path)
        heavy = calculate_intelligence_density(heavy_path)
        assert heavy["Intelligence Density"] < base["Intelligence Density"]

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError, match="not found"):
            calculate_intelligence_density("nonexistent.toml")

    def test_missing_intelligence_section(self, tmp_path):
        path = tmp_path / "bad.toml"
        with open(path, "w") as f:
            toml.dump({"ResourceComponents": SIMPLE_RESOURCES}, f)
        with pytest.raises(ValueError, match="Missing required section"):
            calculate_intelligence_density(str(path))

    def test_missing_resource_section(self, tmp_path):
        path = tmp_path / "bad.toml"
        with open(path, "w") as f:
            toml.dump({"IntelligenceComponents": SIMPLE_INTELLIGENCE}, f)
        with pytest.raises(ValueError, match="Missing required section"):
            calculate_intelligence_density(str(path))

    def test_malformed_toml(self, tmp_path):
        path = tmp_path / "bad.toml"
        path.write_text("this is not = valid toml ][")
        with pytest.raises(ValueError, match="Failed to parse"):
            calculate_intelligence_density(str(path))

    def test_provided_spec_file_runs(self):
        results = calculate_intelligence_density("model_specifications.toml")
        assert results["Intelligence Density"] > 0
        assert results["Intelligence Measure"] > 0
        assert results["Resource Consumption"] > 0

    def test_returns_all_keys(self, tmp_path):
        path = make_toml(tmp_path, SIMPLE_INTELLIGENCE, SIMPLE_RESOURCES)
        results = calculate_intelligence_density(path)
        assert set(results.keys()) == {"Intelligence Measure", "Resource Consumption", "Intelligence Density"}
