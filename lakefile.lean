import Lake
open Lake DSL

package BlasterBenchmarks where

-- Solvers
-- Pinned to an exact commit (tip of `main` when pinned) so baseline runs are reproducible.
require «Blaster» from git
  "https://github.com/input-output-hk/Lean-blaster" @ "585c5fc1370196a03cfceec674f5a5ac2ed3c2f2"

-- Tactics
require smt from git "https://github.com/ufmg-smite/lean-smt.git" @ "main"
require auto from git "https://github.com/leanprover-community/lean-auto.git" @ "v4.24.0-hammer"
require aesop from git "https://github.com/leanprover-community/aesop" @ "v4.24.0"
require Duper from git "https://github.com/leanprover-community/duper.git" @ "41bf3ee53113744e6cda9971e929bb248af59461"
require Hammer from git "https://github.com/JOSHCLUNE/LeanHammer.git" @ "v4.24.0"
-- Mathlib
def leanVersion : String := s!"v{Lean.versionString}"
require "leanprover-community" / mathlib @ git leanVersion

@[default_target]
lean_lib BlasterBenchmarks where
