import os

import yamale


class LogConfig:
    log_config: dict

    def __init__(self):
        self.log_config = self._load_log_config()

    @staticmethod
    def _load_log_config() -> dict:
        log_config = yamale.make_data(os.environ.get("LOG_CONFIG"))[0][0]
        log_config["loggers"]["uvicorn"]["level"] = os.environ.get("LOG_LEVEL", "INFO")
        log_config["root"]["level"] = os.environ.get("LOG_LEVEL", "INFO")
        return log_config
