#!/bin/bash
echo "Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "Starting Ivy Prep App..."
python app.py
