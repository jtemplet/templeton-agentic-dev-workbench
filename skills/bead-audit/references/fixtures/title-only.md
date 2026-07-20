<!--
Expected: overall NEEDS WORK, raw score 0/100, band Poor, applyable:false.
Only a title and a one-line description. Deterministic arithmetic (task denominator 100):
  Why fail (0) - "The dashboard needs work" names no stakeholder, constraint, or consumer, so it
    is a title restatement, which the Marr audit scores fail, not warn.
  How fail (0), Done when fail (0), Acceptance Criteria fail (0), Estimated size absent fail (0).
  Structure 0/5 canonical => 0.
  Numerator 0; raw 0/100 bands Poor. Verdict NEEDS WORK caps the ceiling at Weak, and the lower of
  (Poor score, Weak ceiling) is Poor.
Auto-fix cannot infer Why/How/Done/AC from one line, so every section gets [AUTHOR TO COMPLETE]
=> applyable:false, blocked_on:[why,how,done-when,acceptance-criteria,estimated-size]. Must be
routed to a human, never written back.
-->
Title: Fix the dashboard
Type: task

The dashboard needs work.
