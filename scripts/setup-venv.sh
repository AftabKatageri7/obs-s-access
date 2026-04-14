#!/bin/bash

# Setup Python virtual environment for import scripts
# Usage: ./scripts/setup-venv.sh

set -e

VENV_DIR="venv"

echo "Setting up Python virtual environment..."
echo "========================================"

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is not installed"
    echo "Please install Python 3 first"
    exit 1
fi

echo "Python version: $(python3 --version)"
echo ""

# Create virtual environment if it doesn't exist
if [ -d "$VENV_DIR" ]; then
    echo "Virtual environment already exists at ./$VENV_DIR"
    read -p "Do you want to recreate it? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Removing existing virtual environment..."
        rm -rf "$VENV_DIR"
    else
        echo "Using existing virtual environment"
        source "$VENV_DIR/bin/activate"
        echo "Virtual environment activated!"
        echo ""
        echo "To use the scripts, run:"
        echo "  source venv/bin/activate"
        echo "  python3 scripts/generate-teams-config.py observability-s \$GITHUB_TOKEN"
        exit 0
    fi
fi

echo "Creating virtual environment..."
python3 -m venv "$VENV_DIR"

echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

echo "Upgrading pip..."
pip install --upgrade pip

echo "Installing dependencies from requirements.txt..."
pip install -r requirements.txt

echo ""
echo "========================================"
echo "✓ Setup complete!"
echo ""
echo "Virtual environment created at ./$VENV_DIR"
echo ""
echo "To activate the virtual environment, run:"
echo "  source venv/bin/activate"
echo ""
echo "To deactivate when done, run:"
echo "  deactivate"
echo ""
echo "Example usage:"
echo "  source venv/bin/activate"
echo "  export GITHUB_TOKEN=your_token_here"
echo "  python3 scripts/generate-teams-config.py observability-s \$GITHUB_TOKEN > teams.yaml"
echo "  python3 scripts/generate-repo-config.py observability-s \$GITHUB_TOKEN > repositories.yaml"
echo "  deactivate"

# Made with Bob
