#!/usr/bin/env python3
"""ChatLlama launcher script - Run from project root"""
import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

# Import and run main
from chat import main

if __name__ == "__main__":
    sys.exit(main())
