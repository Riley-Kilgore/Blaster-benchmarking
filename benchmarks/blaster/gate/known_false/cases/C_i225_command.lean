import Blaster

/-! Known-false case C, `#blaster` command form (upstream #225). FALSE (`rfl`).
The refutation restates the bracketed statement verbatim (the gate checks this) and uses no Blaster. -/

namespace KnownFalse.C_command

structure ProofBox where
  proof : True ∨ True

#blaster [ProofBox.mk (.inl .intro) ≠ ProofBox.mk (.inr .intro)]

theorem kf_C_command_false : ¬ (ProofBox.mk (.inl .intro) ≠ ProofBox.mk (.inr .intro)) := fun h => h rfl

#print axioms kf_C_command_false

end KnownFalse.C_command
