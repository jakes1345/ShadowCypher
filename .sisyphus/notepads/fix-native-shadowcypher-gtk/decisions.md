# Decisions
- We will introduce a `PageCtx` struct to hold the `GtkTextBuffer *` and other page-specific state, and allocate it on the heap so it survives the `on_activate` function.
