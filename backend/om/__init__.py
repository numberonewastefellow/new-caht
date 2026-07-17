import os

__version__ = os.environ.get("OM_VERSION", "") or "Development"
