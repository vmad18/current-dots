#!/bin/bash

set -euo pipefail

SESH_NAME="${1:-codex}"

if tmux has-session -t "$SESH_NAME" 2>/dev/null; then
  tmux attach-session -t "$SESH_NAME"
else
  tmux new-session -d -s "$SESH_NAME"

  p1=$(tmux display-message -p -t "$SESH_NAME" '#{pane_id}')
  p2=$(tmux split-window -h -t "$p1" -P -F '#{pane_id}')
  p3=$(tmux split-window -v -t "$p1" -P -F '#{pane_id}')
  p4=$(tmux split-window -v -t "$p2" -P -F '#{pane_id}')

  tmux send-keys -t "$p1" "codex resume nvim-work-glbl" Enter
  tmux send-keys -t "$p2" "codex resume spot-hypr-work" Enter
  tmux send-keys -t "$p3" "codex resume wandb-island-work" Enter
  tmux send-keys -t "$p4" "codex resume tmux-work" Enter


  tmux attach-session -t "$SESH_NAME"
fi
