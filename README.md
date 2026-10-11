# Blaster-benchmarks

## Held-out suites

This branch is the hill-climb agent's copy of the harness. Two suites are **held out** and are
not on it: MiniF2F (all 96 goals) and 32 of the 108 Verina goals (`verina_basic_*`), selected
with a fixed seed from the numbered file list. The Verina directory here holds the 76 climb-set
goals only. The held-out files, the list of held-out Verina names and the gate that runs them
live outside this repository and are run by a person after each accepted change. Do not add
MiniF2F or the missing Verina files back to this branch.
