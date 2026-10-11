import Blaster

/-! Known-false case A, `#blaster` command form (upstream #194). FALSE (`l = [5]`).
The refutation below restates the bracketed statement verbatim and uses no Blaster. -/

namespace KnownFalse.A_command

#blaster [∀ (l : List Nat),
  (l.all (fun y => decide (y < 3)) && l.all (fun y => decide (y = 0 ∨ y = 1 ∨ y = 2))) = true]

theorem kf_A_command_false : ¬ (∀ (l : List Nat),
    (l.all (fun y => decide (y < 3)) && l.all (fun y => decide (y = 0 ∨ y = 1 ∨ y = 2))) = true) := by
  intro h; have := h [5]; revert this; decide

#print axioms kf_A_command_false

end KnownFalse.A_command
