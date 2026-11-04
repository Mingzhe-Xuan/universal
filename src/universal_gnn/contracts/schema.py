"""Version checks shared by files and extension protocols."""

CONTRACT_VERSIONS = {"config": 1, "dataset": 1, "graph": 1, "gnn": 1}


def validate_version(value, kind):
    if not isinstance(value, int) or isinstance(value, bool) or value != CONTRACT_VERSIONS[kind]:
        raise ValueError(f"Unsupported {kind} schema version {value!r}")


def validate_config(config):
    backbone = config.get("backbone")
    if isinstance(backbone, dict) and "initialization" in backbone:
        from universal_gnn.backbones.official.profiles import PROFILES
        from universal_gnn.backbones.initialization import validate_initialization

        if backbone.get("implementation", "official" if backbone.get("name") in PROFILES else "legacy") == "official":
            validate_initialization(backbone["initialization"])
            if (backbone["initialization"] == "scratch" and isinstance(config.get("prediction"), dict) and
                    config["prediction"].get("head_mode") == "native"):
                raise ValueError("Scratch initialization requires prediction.head_mode=reset")
    if "schema_version" in config:
        validate_version(config["schema_version"], "config")
    if "graph" in config and not isinstance(config["graph"], dict):
        raise ValueError("Configuration graph must be a mapping")
    if isinstance(config.get("task"), dict) and "supervised_outputs" in config["task"]:
        from universal_gnn.tasks.supervision import supervised_outputs

        supervised_outputs(config)
    if "prediction" in config or "optimization" in config:
        from universal_gnn.readouts.configuration import validate_component_config

        validate_component_config(config)
