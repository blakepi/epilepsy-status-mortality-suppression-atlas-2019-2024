# Manual Query Instructions

Generated: 2026-06-13

No manual CDC WONDER downloads are currently required for the registered
Q001-Q015 extraction set.

The prior Q011 manual instruction was superseded by the UCD advanced Finder
textarea patch, which opens `#TD157\.V2` through the `D157.V2` advanced Finder
view before filling:

```text
G40 (Epilepsy)
G41 (Status epilepticus)
```

Q011, Q012, and Q014 have since downloaded, parsed, and validated successfully.
If a future CDC WONDER markup change blocks automation, regenerate this file
from the query registry for only the affected query.
