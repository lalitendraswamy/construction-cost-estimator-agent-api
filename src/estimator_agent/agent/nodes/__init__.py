"""Graph nodes. Signature: (state, runtime) -> partial state update | Command.

Rule of thumb for nodes that call interrupt(): on resume the WHOLE node re-runs from the
top, so keep anything expensive or side-effecting out of it (see ask_user / await_approval).
"""
