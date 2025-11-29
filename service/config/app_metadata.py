import os


class AgentSupportServiceMetadata:
    name = "AgentSupportService"
    description = """
        Agent Support service providing services to support agent operations
    """
    summary = "Supports agent operations"
    version = os.environ.get("BUILD_VERSION", "0.0.0")
    tags = [
        {
            "name": "Data",
            "description": "APIs used for fetch agent support data",
        },
        {
            "name": "Configuration",
            "description": "APIs used for reading service configuration",
        },
    ]
    enable_docs_url = (
        "/docs" if os.environ.get("LOG_LEVEL", "INFO") == "DEBUG" else None
    )
    origins = [
        "http://*.hobu.ai",
        "https://*.hobu.ai",
        "http://hobu.ai",
        "https://hobu.ai",
        "http://localhost",
        "http://localhost:8000",
        "http://localhost:8001",
    ]
