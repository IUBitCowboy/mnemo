---
date: 2026-03-01
time: 11:33:47
muse: clio
lifecycle: durable
status: active
priority: P2
session_count: 3
source: SP26 course-admin design session 2026-03-01
tags: []
---
# Data capture decisions have asymmetric cost profiles — deliberate MVP exception. Recast for MoJ: when building the joke submission schema, students face the same choice. Example: storing submitted_by user ID on every joke even when v1 displays no attribution. Capturing now = one column + one parse line. Retrofitting later = schema migration + historical data gap + re-collection impossible. The MVP principle (do not build features you do not need) applies to behavior, not to data capture when capture cost approaches zero. This distinction is a real engineering judgment call worth naming explicitly. Suggested uses: (1) lecture example in the schema/data modeling week; (2) planted Engineering Log type-3 entry prompt; (3) CONTRIBUTIONS.md reflection hook in W9 or W10 ICEX. Framing: MVP is not a universal acid — it has a known exception class. Recognizing the exception and documenting the reasoning IS the engineering act.

