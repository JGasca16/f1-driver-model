# Project
F1 teammate-relative driver rating model (2025 season), public portfolio project.

## Hard rules
1. Never use points, wins or championship position as a model input.
2. Never overwrite or delete historical scripts or data files. Add new versioned files instead.
3. Never touch cache/. Never upgrade FastF1 (pinned 3.8.3). Never run network downloads unless I ask.
4. Never write absolute local paths into any committed file.
5. Never use git add, commit or push. I run those myself.
6. Ratings are only comparable inside a teammate group. Never rank across groups.
7. A negative rating means the driver outperformed the teammate. Any user-facing text must say so.
8. Results must be worded as they are: the prediction test is inconclusive. Never write that ratings "predict" results.
9. 2025 results are exploratory because the method was designed while examining that season.

## Working rules
- Before reporting done, run the full test suite and state the pass count.
- Report format: what changed (files), test result, anything you were unsure about. Under 15 lines.
- If a request conflicts with a rule above, stop and tell me instead of choosing.

## Writing rules for any text a visitor reads (dashboard, README, docs)
- First person, plain words, short sentences. Say what a thing is, not that it matters.
- Do not use: delve, tapestry, pivotal, underscore, landscape, foster, testament, showcase, crucial, enhance, robust, seamless, vibrant, rich.
- No "not just X but Y", no "from X to Y" unless a real range, no unnamed authorities, no default lists of three.
- Every number in text must come from a file in the repo.
