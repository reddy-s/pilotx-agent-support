import logging
import os

import yamale

from ..utils import EnvironmentVariableNotFound

logger = logging.getLogger(__name__)


class ServiceConfig:

    _instance = None
    config: dict
    firebase: dict
    appName: str

    @classmethod
    def get_or_create_instance(cls):
        """
        Provides a mechanism to retrieve an existing instance of the `ServiceConfig`
        class or create a new one if none exists. Implements a singleton pattern
        to ensure only one instance of this class is created during the application
        lifecycle.

        :raises None: No exceptions are raised explicitly by this method.
        :returns: The single instance of the `ServiceConfig` class.
        :rtype: ServiceConfig
        """
        if cls._instance is None:
            logger.debug("Creating new instance of ")
            cls._instance = ServiceConfig()
        logger.debug("Returning existing instance of ServiceConfig")
        return cls._instance

    def __init__(self):
        try:
            logger.info(
                f"Reading Config Schema from env variable 'CONFIG_SCHEMA_PATH' which is set to: {os.environ.get('CONFIG_SCHEMA_PATH')}"
            )
            logger.info(
                f"Reading Config from env variable 'CONFIG_PATH' which is set to: {os.environ.get('CONFIG_PATH')}"
            )
            logger.info("Reading config and validating schema...")
            self.path = self._check_if_config_exists()
            schema = yamale.make_schema(os.environ.get("CONFIG_SCHEMA_PATH"))
            self.config = yamale.make_data(self.path)
            yamale.validate(schema, self.config)
            logger.info("Schema validation success! 👍")
            self._set_default_config_class_attributes(self.config[0][0].get("service"))
        except ValueError as e:
            logger.error(f"Schema Validation failed!\n{str(e)}")
            exit(1)
        except Exception as ge:
            logger.error(f"Error occurred during schema validation\n{str(ge)}")
            exit(1)

    @staticmethod
    def _check_if_config_exists():
        """
        Checks if the configuration file exists in the path specified by the
        environment variable "CONFIG_PATH". The method first verifies if the
        environment variable "CONFIG_PATH" is set. If it is set, it checks
        whether the path exists in the file system. Raises specific errors
        if configurations are not found or if the file path is invalid.

        :raises EnvironmentVariableNotFound: Raised if the "CONFIG_PATH"
            environment variable is not set.
        :raises FileNotFoundError: Raised if the file path specified in
            "CONFIG_PATH" does not exist.
        :return: The configuration file path if it exists.
        :rtype: str
        """
        if os.environ.get("CONFIG_PATH") is not None:
            if os.path.exists(os.environ.get("CONFIG_PATH")):
                return os.environ.get("CONFIG_PATH")
            else:
                raise FileNotFoundError(
                    f"{os.environ.get('CONFIG_PATH')} is not a file"
                )
        else:
            raise EnvironmentVariableNotFound("CONFIG_PATH")

    def _set_default_config_class_attributes(self, defaults: dict):
        """
        Sets default configuration attributes on the class instance. This method
        iterates through the provided dictionary and assigns its key-value pairs
        as attributes of the class instance using ``setattr``.

        :param defaults: A dictionary containing default configuration values. Each
                         key-value pair in the dictionary will be applied as an
                         attribute to the class instance.
        :type defaults: dict
        """
        for key, value in defaults.items():
            setattr(self, key, value)
