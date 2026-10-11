import Blaster

/-! Known-false case B, `#blaster` command form (upstream #226). FALSE (`α := Empty`).
The refutation restates the bracketed statement verbatim (the gate checks this) and uses no Blaster. -/

namespace KnownFalse.B_command

#blaster [∀ α : Type, (∀ _ : α, False) → False]

theorem kf_B_command_false : ¬ (∀ α : Type, (∀ _ : α, False) → False) := fun h => h Empty Empty.elim

#print axioms kf_B_command_false

end KnownFalse.B_command
