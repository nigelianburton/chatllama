# ChatLlama Environment Setup

This directory contains environment export files for recreating the ChatLlama Python environment.

## Files

- **`conda_list.txt`** - Complete list of all packages in the chatllama2 conda environment
- **`environment.yml`** - Full conda environment specification (includes channels, versions, and pip dependencies)
- **`pip_freeze.txt`** - Pip package list (legacy, use environment.yml instead)

## Recreating the Environment

### Option 1: From environment.yml (Recommended)

This method recreates the exact environment with all dependencies:

```bash
# Create the environment from the YAML file
conda env create -f installation_info/environment.yml

# Activate the environment
conda activate chatllama2
```

### Option 2: Create Fresh Environment

If you need to create a fresh environment with key packages:

```bash
# Create a new conda environment with Python 3.11
conda create -n chatllama2 python=3.11 -y

# Activate the environment
conda activate chatllama2

# Install key packages from conda-forge
conda install -c conda-forge pyqt transformers pillow -y

# Install PyTorch via pip with CUDA 12.8 support (recommended for compatibility)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128

# Install remaining packages via pip
pip install fastmcp httpx
```

## Key Dependencies

- **Python**: 3.11
- **PyQt6**: UI framework
- **transformers**: Hugging Face library (includes Moondream2 vision model)
- **Pillow**: Image processing  
- **PyTorch** (2.10.0+cu128): Deep learning framework - installed via pip with CUDA 12.8 support
- **torchvision**: Computer vision utilities
- **fastmcp**: Model Context Protocol server
- **httpx**: HTTP client library

## Updating the Environment Files

When you add new packages to the environment, update these files:

```bash
# Update conda list
conda list -n chatllama2 > installation_info/conda_list.txt

# Update environment.yml
conda env export -n chatllama2 > installation_info/environment.yml

# Update pip freeze (if needed)
pip freeze > installation_info/pip_freeze.txt
```

## Notes

- The `chatllama2` environment is required for running PEPPER.py
- Always activate the environment before running Python commands: `conda activate chatllama2`
- CUDA support is included via PyTorch for GPU acceleration
- The Moondream2 model (~3.5GB) will download automatically on first use
