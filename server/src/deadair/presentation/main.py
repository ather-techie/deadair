from deadair.container import build_container
from deadair.presentation.api.app import create_app

app = create_app(build_container())
