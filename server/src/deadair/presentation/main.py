from deadair.config import load_settings
from deadair.container import build_container
from deadair.logging_config import configure_logging
from deadair.presentation.api.app import create_app

_settings = load_settings()
configure_logging(_settings)

app = create_app(build_container(_settings))
