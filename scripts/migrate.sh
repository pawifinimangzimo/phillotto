#!/bin/bash
DEST="lottery-optimizer-$(date +%Y%m%d).tar.gz"

echo "📦 Packaging project..."
tar --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='data/results/*' \
    --exclude='data/stats/*' \
    -czvf $DEST .

echo "✅ Created $DEST ("$(du -h $DEST | cut -f1)")"
echo "To deploy on new machine:"
echo "1. scp $DEST newmachine:~/"
echo "2. On new machine: tar -xzvf $DEST && cd lottery-optimizer"
echo "3. Run: ./scripts/setup_env.sh"