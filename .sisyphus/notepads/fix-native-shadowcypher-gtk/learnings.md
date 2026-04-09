# Learnings
- The root cause of the crash on Network/System/Firewall/Logs pages is that `bufs` is allocated on the stack in `on_activate` and passed to `g_signal_connect`. When `on_stack_visible_child` is called later, `bufs` points to a dead stack frame, causing a segfault or GTK assertion failure when trying to use the garbage pointers.
