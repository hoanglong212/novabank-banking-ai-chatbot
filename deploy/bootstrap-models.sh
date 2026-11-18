#!/bin/sh
set -eu

if [ "$LLM_PROVIDER" = mock ]; then
    echo "Mock mode selected. No model weights are needed."
    exit 0
fi

for model in "$OLLAMA_MODEL" "$GUARD_MODEL" "$EMBEDDING_MODEL" "$QUARANTINED_LLM_MODEL"; do
    if ! ollama show "$model" >/dev/null 2>&1; then
        printf 'Downloading %s to the Ollama volume.\n' "$model"
        ollama pull "$model"
    fi
done
