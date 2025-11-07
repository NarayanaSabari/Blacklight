#!/bin/bash
# Quick fix for spaCy model installation

echo "🔧 Installing spaCy 3.7.2 and en_core_web_sm model..."

# Downgrade to stable spaCy version
pip install spacy==3.7.2

# Install model directly from wheel
pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.1/en_core_web_sm-3.7.1-py3-none-any.whl

# Verify
echo ""
echo "Verifying installation..."
python -c "import spacy; nlp = spacy.load('en_core_web_sm'); print('✅ spaCy model loaded successfully!'); print(f'   Model: en_core_web_sm v{nlp.meta[\"version\"]}'); print(f'   spaCy: v{spacy.__version__}')"

echo ""
echo "✅ Setup complete!"
echo "⚠️  Remember to restart your Flask server!"
