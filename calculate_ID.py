import toml

def calculate_weighted_sum(components):
    return sum(value['value'] * value['weight'] for value in components.values())

def calculate_intelligence_density(toml_path="model_specifications.toml"):
    # Load specifications from the TOML file
    config = toml.load(toml_path)

    # Calculate Intelligence Measure (I)
    intelligence_components = config['IntelligenceComponents']
    intelligence_measure = calculate_weighted_sum(intelligence_components)

    # Calculate Resource Consumption (R)
    resource_components = config['ResourceComponents']
    resource_consumption = calculate_weighted_sum(resource_components)

    # Compute Intelligence Density (ID)
    intelligence_density = intelligence_measure / resource_consumption if resource_consumption != 0 else None

    return {
        "Intelligence Measure": intelligence_measure,
        "Resource Consumption": resource_consumption,
        "Intelligence Density": intelligence_density
    }

# Run the calculation and display results
results = calculate_intelligence_density("model_specifications.toml")
for key, value in results.items():
    print(f"{key}: {value:.4f}")
