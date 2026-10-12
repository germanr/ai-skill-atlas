Moved here on 2026-10-10. These status files were written at 02:02 when the Codex usage limit stopped the verifier.
The chain read the missing verifier output as zero problems. The papers are not verified; the next run redoes the verifier
from the reconciled file on disk. codex_extract.py now stops instead of writing a status file in this case.
