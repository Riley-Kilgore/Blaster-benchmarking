import Blaster

/-! Known-false case C, tactic form (upstream Lean-blaster #225: constructor proof fields
treated as data). FALSE: the two values are equal by proof irrelevance (`rfl`); Blaster must
not report Valid. At 585c5fc it does. The refutation at the end uses no Blaster. -/

namespace KnownFalse.C

structure ProofBox where
  proof : True ∨ True

theorem kf_C : ProofBox.mk (.inl .intro) ≠ ProofBox.mk (.inr .intro) := by
  blaster (verbose: 1) (random-seed: 42)

theorem kf_C_false : ¬ (type_of% @kf_C) := fun h => h rfl

#print axioms kf_C_false

end KnownFalse.C
