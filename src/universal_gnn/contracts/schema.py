"""Version checks shared by files and extension protocols."""

CONTRACT_VERSIONS = {"config": 1, "dataset": 1, "graph": 1, "gnn": 1}


def validate_version(value, kind):
    if not isinstance(value, int) or isinstance(value, bool) or value != CONTRACT_VERSIONS[kind]:
        raise ValueError(f"Unsupported {kind} schema version {value!r}")


def validate_config(config):
    if "schema_version" in config:
        validate_version(config["schema_version"], "config")
    if "graph" in config and not isinstance(config["graph"], dict):
        raise ValueError("Configuration graph must be a mapping")
