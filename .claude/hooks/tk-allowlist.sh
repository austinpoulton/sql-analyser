#!/bin/bash
# Allowlist for tk commands
# This hook automatically approves common tk commands without prompting

COMMAND=$(jq -r '.tool_input.command // ""')

# Check if command starts with tk and is in allowlist
if [[ "$COMMAND" =~ ^tk\ (help|create|list|ls|show|ready|blocked|closed|dep|start|close|reopen|status|query|add-note|link|unlink) ]]; then
  jq -n '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "allow",
      permissionDecisionReason: "tk command approved by project allowlist"
    }
  }'
  exit 0
fi

# For commands that modify git or are destructive, let normal permission flow handle it
exit 0
