## Plan

### Implement comparison features
Upgrade the comparison loop in choose.py:
- Store last answer per pair; when re-asked, show previous choice and accept Enter to reuse
- Support commands: list (show all items), skip (skip current pair), back (re-prompt previous pair)
- Show running tallies in a matrix view during comparisons
- Handle skipped pairs in ranking, stable sort, tie notes
- Summary of unresolved comparisons in output
- Call out items that were never preferred (0 wins) - prompt the user to reconsider them ("Is this still on your list? Or worth a second look?") without assuming why they scored low

### Consider Go port
Once features stabilize, evaluate whether to port to Go with cobra + bubbletea for distribution and TUI quality. Not urgent - the Python version is the priority for now.
