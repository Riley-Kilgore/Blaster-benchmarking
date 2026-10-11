import Blaster

/-! Known-false case B, tactic form (upstream Lean-blaster #226: empty quantifier domains).
FALSE (`α := Empty`); Blaster must not report Valid. At 585c5fc it does.
The refutation at the end uses no Blaster. -/

namespace KnownFalse.B

theorem kf_B : ∀ α : Type, (∀ _ : α, False) → False := by
  blaster (verbose: 1) (random-seed: 42)

theorem kf_B_false : ¬ (type_of% @kf_B) := fun h => h Empty Empty.elim

#print axioms kf_B_false

end KnownFalse.B
