#!/bin/bash
cd "$(dirname "$0")"
echo "MenuMate AI V3 — Live Uploaded-Menu Analysis"
echo "Your API key is kept only in this Terminal session."
echo
if [ -z "$OPENAI_API_KEY" ]; then
  read -s -p "Paste your OpenAI API key: " OPENAI_API_KEY
  echo
  export OPENAI_API_KEY
fi
python3 app.py
