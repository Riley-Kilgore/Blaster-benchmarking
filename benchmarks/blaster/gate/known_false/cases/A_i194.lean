import Blaster

/-! Known-false case A (upstream Lean-blaster #194: guard-asymmetric extensionality vs
unguarded lambda definitions). The statement is FALSE (`l = [5]`); Blaster must not
report Valid. At 585c5fc it does, in tactic form with the harness tactic text.
The refutation at the end uses no Blaster. -/

namespace KnownFalse.A

theorem kf_A (l : List Nat) :
    (l.all (fun y => decide (y < 3)) && l.all (fun y => decide (y = 0 ∨ y = 1 ∨ y = 2))) = true := by
  blaster (verbose: 1) (random-seed: 42)

theorem kf_A_false : ¬ (type_of% @kf_A) := by
  intro h; have := h [5]; revert this; decide

#print axioms kf_A_false

end KnownFalse.A
