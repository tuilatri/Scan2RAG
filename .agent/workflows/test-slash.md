---
description: Test workflow to verify slash commands are working
---

# /test-slash - Test Slash Commands

This is a simple test workflow to verify slash commands are working.

## Task

When user types `/test-slash`, respond with:

```
✅ Slash commands are working!

Your workflows in .agent/workflows/ are properly configured.

Available commands:
- /plan - Create project plan
- /debug - Debug issues
- /test - Run tests
- /deploy - Deploy application
- /status - Show project status
- /create - Create new features
- /enhance - Enhance existing code
- /brainstorm - Brainstorm ideas
- /orchestrate - Multi-agent coordination
- /preview - Preview UI
- /ui-ux-pro-max - UI/UX design

Try any of these commands!
```

## Notes

If you see this message, it means:
1. ✅ Workflows are in correct location (.agent/workflows/)
2. ✅ YAML frontmatter is correct
3. ✅ Slash command parser is working
4. ✅ IDE has loaded the workflows

If slash commands still don't work after seeing this, there might be an IDE issue.
