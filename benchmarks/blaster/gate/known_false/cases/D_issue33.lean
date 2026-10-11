import Blaster

/-! Known-false case D, tactic form (upstream Lean-blaster #194 via Tests/FixedIssues/Issue33.lean:74).
Definitions copied verbatim from Lean-blaster@585c5fc Tests/FixedIssues/Issue33.lean lines 43-72;
the statement is the one at lines 75-76. FALSE (`n = 1`, `transaction = []`). The command form of
this case is the pinned test line itself (entry `Tests/FixedIssues/Issue33.lean:74` in climb.json). -/

namespace KnownFalse.D

structure Verifier where
  payment_key : Nat
  is_mandatory : Bool

structure VerifierConfig where
  verifiers : List Verifier
  optional_threshold : Nat

def validate_signatures (verifier_config : VerifierConfig) (signatories : List Nat) : Bool :=
  let (mandatory_verifiers, optional_verifiers) :=
    verifier_config.verifiers.partition Verifier.is_mandatory

  let mandatory_payment_keys := mandatory_verifiers.map Verifier.payment_key
  let optional_payment_keys := optional_verifiers.map Verifier.payment_key

  let all_mandatory_signed :=
    mandatory_payment_keys.all
      (λ payment_key => signatories.any (λ signature => signature == payment_key))

  let optional_signatures_count :=
    optional_payment_keys.foldr
      (λ payment_key acc =>
        if signatories.any (λ signature => signature == payment_key)
          then acc + 1
          else acc)
      0

  let threshold_met := optional_signatures_count >= verifier_config.optional_threshold

  all_mandatory_signed && threshold_met

theorem kf_D : ∀ (transaction : List Nat) (n : Nat),
       validate_signatures (VerifierConfig.mk [] n) transaction = true := by
  blaster (verbose: 1) (random-seed: 42)

theorem kf_D_false : ¬ (type_of% @kf_D) := by
  intro h; have := h [] 1; revert this; decide

#print axioms kf_D_false

end KnownFalse.D
