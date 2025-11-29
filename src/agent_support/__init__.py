import logging

from dotenv import load_dotenv

from .config import ServiceConfig
from .support_services import AgentSupportService

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

__version__ = "0.0.0"


__all__ = ["AgentSupportService"]


def main() -> None:
    logger.info(ServiceConfig.get_or_create_instance().config)
