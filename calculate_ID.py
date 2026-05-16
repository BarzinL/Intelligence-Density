import argparse
import sys
import toml


def calculate_weighted_sum(components: dict) -> float:
    """Return the weighted sum of components, auto-normalizing weights to sum to 1."""
    total_weight = sum(v["weight"] for v in components.values())
    if total_weight == 0:
        raise ValueError("Component weights must not all be zero.")
    if abs(total_weight - 1.0) > 1e-6:
        print(
            f"  Warning: weights sum to {total_weight:.4f}, not 1.0 — auto-normalizing.",
            file=sys.stderr,
        )
    return sum(v["value"] * (v["weight"] / total_weight) for v in components.values())


def validate_components(components: dict, section: str) -> None:
    """Raise ValueError if any component value or weight is out of range."""
    for name, spec in components.items():
        if not (0.0 <= spec["value"] <= 1.0):
            raise ValueError(
                f"[{section}] '{name}' value {spec['value']} is outside [0, 1]."
            )
        if spec["weight"] < 0:
            raise ValueError(
                f"[{section}] '{name}' weight {spec['weight']} must be non-negative."
            )


def calculate_intelligence_density(toml_path: str = "model_specifications.toml") -> dict:
    """Load a model spec TOML and return Intelligence Measure, Resource Consumption, and ID."""
    try:
        config = toml.load(toml_path)
    except FileNotFoundError:
        raise FileNotFoundError(f"Model spec file not found: {toml_path}")
    except toml.TomlDecodeError as e:
        raise ValueError(f"Failed to parse {toml_path}: {e}")

    for section in ("IntelligenceComponents", "ResourceComponents"):
        if section not in config:
            raise ValueError(f"Missing required section [{section}] in {toml_path}")

    intelligence_components = config["IntelligenceComponents"]
    resource_components = config["ResourceComponents"]

    validate_components(intelligence_components, "IntelligenceComponents")
    validate_components(resource_components, "ResourceComponents")

    intelligence_measure = calculate_weighted_sum(intelligence_components)
    resource_consumption = calculate_weighted_sum(resource_components)

    if resource_consumption == 0:
        raise ValueError("Resource Consumption evaluated to 0 — cannot compute ID.")

    return {
        "Intelligence Measure": intelligence_measure,
        "Resource Consumption": resource_consumption,
        "Intelligence Density": intelligence_measure / resource_consumption,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Calculate Intelligence Density (ID) for one or more AI model specifications."
    )
    parser.add_argument(
        "model_files",
        nargs="+",
        metavar="FILE",
        help="Path(s) to model specification TOML file(s).",
    )
    parser.add_argument(
        "--rank",
        action="store_true",
        help="When multiple files are given, rank them by Intelligence Density.",
    )
    args = parser.parse_args()

    results = []
    for path in args.model_files:
        try:
            metrics = calculate_intelligence_density(path)
            results.append((path, metrics))
        except (FileNotFoundError, ValueError) as e:
            print(f"Error ({path}): {e}", file=sys.stderr)

    if not results:
        sys.exit(1)

    if args.rank and len(results) > 1:
        results.sort(key=lambda x: x[1]["Intelligence Density"], reverse=True)

    for i, (path, metrics) in enumerate(results):
        if len(results) > 1:
            rank_str = f"#{i + 1} " if args.rank else ""
            print(f"\n{rank_str}{path}")
        for key, value in metrics.items():
            print(f"  {key}: {value:.4f}")


if __name__ == "__main__":
    main()
