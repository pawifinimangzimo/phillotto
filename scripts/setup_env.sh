#!/bin/bash
echo "🚀 Setting up Lottery Optimizer environment..."

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install core requirements
pip install --upgrade pip
pip install -r requirements.txt

# Setup data directories
mkdir -p data/{stats,results,archive}
chmod +x scripts/*.sh

echo "✅ Setup complete! Activate with: source venv/bin/activate"