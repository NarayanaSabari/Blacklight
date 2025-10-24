"""WSGI entry point for production server."""

import os
import sys

from app import create_app

# Ensure the app directory is in the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

app = create_app()

if __name__ == "__main__":
    app.run()
