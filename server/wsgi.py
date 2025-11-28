"""WSGI entry point for production server."""

import os
import sys

from app import create_app

# Ensure the app directory is in the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Wrap application creation in a try/except so we can capture full
# traceback in logs during early startup. This helps debug 'Worker failed to boot'
# errors that happen during app init in a production environment.
try:
    app = create_app()
except Exception as e:
    # Print the exception and full traceback to stdout/stderr so Cloud Run/Gunicorn logs capture it
    import traceback

    print("\nFATAL: Failed to create Flask application during startup:\n", file=sys.stderr)
    traceback.print_exc()
    # Re-raise so the process exits (required by Gunicorn to report boot failure), but
    # the logs will include a full traceback.
    raise

if __name__ == "__main__":
    app.run()
