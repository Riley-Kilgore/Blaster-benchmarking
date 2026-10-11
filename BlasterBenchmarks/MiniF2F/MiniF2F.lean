-- miniF2F (integer / number-theory subset) — statements vendored from
-- https://github.com/rahul3613/miniF2F-lean4 (test split), curated to those that
-- elaborate across our toolchain range (Lean v4.24 .. v4.32). Real/analysis and
-- non-elaborating problems were excluded. Benchmark harness turns each into a
-- standalone `example <stmt> := by <tactic>`.
import Mathlib
open Real Nat Topology
open scoped BigOperators

theorem numbertheory_4x3m7y3neq2003 (x y : ℤ) : 4 * x^3 - 7 * y^3 ≠ 2003 := by sorry
theorem amc12_2001_p5 : Finset.prod (Finset.filter (λ x => ¬ Even x) (Finset.range 10000)) (id : ℕ → ℕ) = (10000!) / ((2^5000) * 5000!) := by sorry
theorem mathd_numbertheory_1124 (n : ℕ) (h₀ : n ≤ 9) (h₁ : 18∣374 * 10 + n) : n = 4 := by sorry
theorem mathd_numbertheory_299 : (1 * 3 * 5 * 7 * 9 * 11 * 13) % 10 = 5 := by sorry
theorem imo_1977_p6 (f : ℕ → ℕ) (h₀ : ∀ n, 0 < f n) (h₁ : ∀ n, 0 < n → f (f n) < f (n + 1)) : ∀ n, 0 < n → f n = n := by sorry
theorem numbertheory_x5neqy2p4 (x y : ℤ) : x^5 ≠ y^2 + 4 := by sorry
theorem mathd_numbertheory_430 (a b c : ℕ) (h₀ : 1 ≤ a ∧ a ≤ 9) (h₁ : 1 ≤ b ∧ b ≤ 9) (h₂ : 1 ≤ c ∧ c ≤ 9) (h₃ : a ≠ b) (h₄ : a ≠ c) (h₅ : b ≠ c) (h₆ : a + b = c) (h₇ : 10 * a + a - b = 2 * c) (h₈ : c * b = 10 * a + a + a) : a + b + c = 8 := by sorry
theorem mathd_algebra_459 (a b c d : ℚ) (h₀ : 3 * a = b + c + d) (h₁ : 4 * b = a + c + d) (h₂ : 2 * c = a + b + d) (h₃ : 8 * a + 10 * b + 6 * c = 24) : ↑d.den + d.num = 28 := by sorry
theorem induction_12dvd4expnp1p20 (n : ℕ) : 12 ∣ 4^(n+1) + 20 := by sorry
theorem imo_1997_p5 (x y : ℕ) (h₀ : 0 < x ∧ 0 < y) (h₁ : x^(y^2) = y^x) : (x, y) = (1, 1) ∨ (x, y) = (16, 2) ∨ (x, y) = (27, 3) := by sorry
theorem mathd_numbertheory_277 (m n : ℕ) (h₀ : Nat.gcd m n = 6) (h₁ : Nat.lcm m n = 126) : 60 ≤ m + n := by sorry
theorem mathd_numbertheory_559 (x y : ℕ) (h₀ : x % 3 = 2) (h₁ : y % 5 = 4) (h₂ : x % 10 = y % 10) : 14 ≤ x := by sorry
theorem induction_nfactltnexpnm1ngt3 (n : ℕ) (h₀ : 3 ≤ n) : n! < n^(n - 1) := by sorry
theorem numbertheory_notEquiv2i2jasqbsqdiv8 : ¬ (∀ a b : ℤ, (∃ i j, a = 2*i ∧ b=2*j) ↔ (∃ k, a^2 + b^2 = 8*k)) := by sorry
theorem mathd_numbertheory_12 : Finset.card (Finset.filter (λ x => 20∣x) (Finset.Icc 15 85)) = 4 := by sorry
theorem mathd_numbertheory_345 : (2000 + 2001 + 2002 + 2003 + 2004 + 2005 + 2006) % 7 = 0 := by sorry
theorem mathd_numbertheory_328 : (5^999999) % 7 = 6 := by sorry
theorem mathd_numbertheory_765 (x : ℤ) (h₀ : x < 0) (h₁ : (24 * x) % 1199 = 15) : x ≤ -449 := by sorry
theorem imo_1959_p1 (n : ℕ) (h₀ : 0 < n) : Nat.gcd (21*n + 4) (14*n + 3) = 1 := by sorry
theorem mathd_numbertheory_175 : (2^2010) % 10 = 4 := by sorry
theorem numbertheory_fxeq4powxp6powxp9powx_f2powmdvdf2pown (m n : ℕ) (f : ℕ → ℕ) (h₀ : ∀ x, f x = 4^x + 6^x + 9^x) (h₁ : 0 < m ∧ 0 < n) (h₂ : m ≤ n) : f (2^m)∣f (2^n) := by sorry
theorem imo_1992_p1 (p q r : ℤ) (h₀ : 1 < p ∧ p < q ∧ q < r) (h₁ : (p - 1) * (q - 1) * (r - 1)∣(p * q * r - 1)) : (p, q, r) = (2, 4, 8) ∨ (p, q, r) = (3, 5, 15) := by sorry
theorem imo_1982_p1 (f : ℕ → ℕ) (h₀ : ∀ m n, (0 < m ∧ 0 < n) → f (m + n) - f m - f n = 0 ∨ f (m + n) - f m - f n = 1) (h₁ : f 2 = 0) (h₂ : 0 < f 3) (h₃ : f 9999 = 3333) : f 1982 = 660 := by sorry
theorem aime_1987_p5 (x y : ℤ) (h₀ : y^2 + 3 * (x^2 * y^2) = 30 * x^2 + 517): 3 * (x^2 * y^2) = 588 := by sorry
theorem mathd_numbertheory_728 : (29^13 - 5^13) % 7 = 3 := by sorry
theorem aime_1994_p3 (x : ℤ) (f : ℤ → ℤ) (h0 : f x + f (x-1) = x^2) (h1 : f 19 = 94): f (94) % 1000 = 561 := by sorry
theorem mathd_numbertheory_293 (n : ℕ) (h₀ : n ≤ 9) (h₁ : 11∣20 * 100 + 10 * n + 7) : n = 5 := by sorry
theorem mathd_numbertheory_769 : (129^34 + 96^38) % 11 = 9 := by sorry
theorem mathd_numbertheory_5 (n : ℕ) (h₀ : 10 ≤ n) (h₁ : ∃ x, x^2 = n) (h₂ : ∃ t, t^3 = n) : 64 ≤ n := by sorry
theorem mathd_numbertheory_207 : 8 * 9^2 + 5 * 9 + 2 = 695 := by sorry
theorem mathd_numbertheory_342 : 54 % 6 = 0 := by sorry
theorem mathd_numbertheory_483 (a : ℕ → ℕ) (h₀ : a 1 = 1) (h₁ : a 2 = 1) (h₂ : ∀ n, a (n + 2) = a (n + 1) + a n) : (a 100) % 4 = 3 := by sorry
theorem amc12a_2003_p5 (A M C : ℕ) (h₀ : A ≤ 9 ∧ M ≤ 9 ∧ C ≤ 9) (h₁ : Nat.ofDigits 10 [0,1,C,M,A] + Nat.ofDigits 10 [2,1,C,M,A] = 123422) : A + M + C = 14 := by sorry
theorem mathd_numbertheory_495 (a b : ℕ) (h₀ : 0 < a ∧ 0 < b) (h₁ : a % 10 = 2) (h₂ : b % 10 = 4) (h₃ : Nat.gcd a b = 6) : 108 ≤ Nat.lcm a b := by sorry
theorem mathd_algebra_296 : abs (((3491 - 60) * (3491 + 60) - 3491^2):ℤ) = 3600 := by sorry
theorem mathd_numbertheory_247 (n : ℕ) (h₀ : (3 * n) % 2 = 11) : n % 11 = 8 := by sorry
theorem numbertheory_2pownm1prime_nprime (n : ℕ) (h₀ : 0 < n) (h₁ : Nat.Prime (2^n - 1)) : Nat.Prime n := by sorry
theorem mathd_algebra_392 (n : ℕ) (h₀ : Even n) (h₁ : ((n:ℤ) - 2)^2 + (n:ℤ)^2 + ((n:ℤ) + 2)^2 = 12296) : ((n - 2) * n * (n + 2)) / 8 = 32736 := by sorry
theorem mathd_numbertheory_314 (r n : ℕ) (h₀ : r = 1342 % 13) (h₁ : 0 < n) (h₂ : 1342∣n) (h₃ : n % 13 < r) : 6710 ≤ n := by sorry
theorem amc12b_2002_p7 (a b c : ℕ) (h₀ : 0 < a ∧ 0 < b ∧ 0 < c) (h₁ : b = a + 1) (h₂ : c = b + 1) (h₃ : a * b * c = 8 * (a + b + c)) : a^2 + (b^2 + c^2) = 77 := by sorry
theorem mathd_numbertheory_457 (n : ℕ) (h₀ : 0 < n) (h₁ : 80325∣(n!)) : 17 ≤ n := by sorry
theorem amc12_2000_p12 (a m c : ℕ) (h₀ : a + m + c = 12) : a*m*c + a*m + m*c + a*c ≤ 112 := by sorry
theorem mathd_numbertheory_135 (n A B C : ℕ) (h₀ : n = 3^17 + 3^10) (h₁ : 11 ∣ (n + 1)) (h₂ : [A,B,C].Pairwise (·≠·)) (h₃ : {A,B,C} ⊂ Finset.Icc 0 9) (h₄ : Odd A ∧ Odd C) (h₅ : ¬ 3 ∣ B) (h₆ : Nat.digits 10 n = [B,A,B,C,C,A,C,B,A]) : 100 * A + 10 * B + C = 129 := by sorry
theorem imo_1981_p6 (f : ℕ → ℕ → ℕ) (h₀ : ∀ y, f 0 y = y + 1) (h₁ : ∀ x, f (x + 1) 0 = f x 1) (h₂ : ∀ x y, f (x + 1) (y + 1) = f x (f (x + 1) y)) : ∀ y, f 4 (y + 1) = 2^(f 4 y + 3) - 3 := by sorry
theorem mathd_numbertheory_34 (x: ℕ) (h₀ : x < 100) (h₁ : x*9 % 100 = 1) : x = 89 := by sorry
theorem mathd_algebra_170 (S : Finset ℤ) (h₀ : ∀ (n : ℤ), n ∈ S ↔ abs (n - 2) ≤ 5 + 6 / 10) : S.card = 11 := by sorry
theorem mathd_numbertheory_618 (n : ℕ) (p : ℕ → ℕ) (h₀ : ∀ x, p x = x^2 - x + 41) (h₁ : 1 < Nat.gcd (p n) (p (n+1))) : 41 ≤ n := by sorry
theorem amc12a_2020_p4 (S : Finset ℕ) (h₀ : ∀ (n : ℕ), n ∈ S ↔ 1000 ≤ n ∧ n ≤ 9999 ∧ (∀ (d : ℕ), d ∈ Nat.digits 10 n → Even d) ∧ 5 ∣ n) : S.card = 100 := by sorry
theorem mathd_numbertheory_435 (k : ℕ) (h₀ : 0 < k) (h₁ : ∀ n, Nat.gcd (6 * n + k) (6 * n + 3) = 1) (h₂ : ∀ n, Nat.gcd (6 * n + k) (6 * n + 2) = 1) (h₃ : ∀ n, Nat.gcd (6 * n + k) (6 * n + 1) = 1) : 5 ≤ k := by sorry
theorem algebra_others_exirrpowirrrat : ∃ a b, Irrational a ∧ Irrational b ∧ ¬ Irrational (a^b) := by sorry
theorem mathd_algebra_76 (f : ℤ → ℤ) (h₀ : ∀n, Odd n → f n = n^2) (h₁ : ∀ n, Even n → f n = n^2 - 4*n -1) : f 4 = -1 := by sorry
theorem mathd_numbertheory_99 (n : ℕ) (h₀ : (2 * n) % 47 = 15) : n % 47 = 31 := by sorry
theorem mathd_numbertheory_233 (b : ZMod (11^2)) (h₀ : b = 24⁻¹) : b = 116 := by sorry
theorem imo_1984_p6 (a b c d k m : ℕ) (h₀ : 0 < a ∧ 0 < b ∧ 0 < c ∧ 0 < d) (h₁ : Odd a ∧ Odd b ∧ Odd c ∧ Odd d) (h₂ : a < b ∧ b < c ∧ c < d) (h₃ : a * d = b * c) (h₄ : a + d = 2^k) (h₅ : b + c = 2^m) : a = 1 := by sorry
theorem imo_2001_p6 (a b c d : ℕ) (h₀ : 0 < a ∧ 0 < b ∧ 0 < c ∧ 0 < d) (h₁ : d < c) (h₂ : c < b) (h₃ : b < a) (h₄ : a * c + b * d = (b + d + a - c) * (b + d + c - a)) : ¬ Nat.Prime (a * b + c * d) := by sorry
theorem mathd_numbertheory_321 (n : ZMod 1399) (h₁ : n = 160⁻¹) : n = 1058 := by sorry
theorem induction_pprime_pdvdapowpma (p a : ℕ) (h₀ : 0 < a) (h₁ : Nat.Prime p) : p ∣ (a^p - a) := by sorry
theorem mathd_numbertheory_229 : (5^30) % 7 = 1 := by sorry
theorem mathd_numbertheory_100 (n : ℕ) (h₀ : 0 < n) (h₁ : Nat.gcd n 40 = 10) (h₂ : Nat.lcm n 40 = 280) : n = 70 := by sorry
theorem amc12b_2002_p4 (n : ℕ) (h₀ : 0 < n) (h₀ : ((1 / 2 + 1 / 3 + 1 / 7 + 1 / n) : ℚ).den = 1) : n = 42 := by sorry
theorem amc12a_2002_p6 (n : ℕ) (h₀ : 0 < n) : ∃ m, (m > n ∧ ∃ p, m * p ≤ m + p) := by sorry
theorem mathd_numbertheory_551 : 1529 % 6 = 5 := by sorry
theorem mathd_algebra_304 : 91^2 = 8281 := by sorry
theorem amc12a_2021_p8 (d : ℕ → ℕ) (h₀ : d 0 = 0) (h₁ : d 1 = 0) (h₂ : d 2 = 1) (h₃ : ∀ n≥3, d n = d (n - 1) + d (n - 3)) : Even (d 2021) ∧ Odd (d 2022) ∧ Even (d 2023) := by sorry
theorem algebra_ineq_nto1onlt2m1on (n : ℕ) : n^(1 / n) < 2 - 1 / n := by sorry
theorem mathd_numbertheory_341 (a b c : ℕ) (h₀ : a ≤ 9 ∧ b ≤ 9 ∧ c ≤ 9) (h₁ : Nat.digits 10 ((5^100) % 1000) = [c,b,a]) : a + b + c = 13 := by sorry
theorem mathd_numbertheory_711 (m n : ℕ) (h₀ : 0 < m ∧ 0 < n) (h₁ : Nat.gcd m n = 8) (h₂ : Nat.lcm m n = 112) : 72 ≤ m + n := by sorry
theorem amc12_2000_p1 (i m o : ℕ) (h₀ : i ≠ m ∧ m ≠ o ∧ o ≠ i) (h₁ : i*m*o = 2001) : i+m+o ≤ 671 := by sorry
theorem mathd_numbertheory_212 : (16^17 * 17^18 * 18^19) % 10 = 8 := by sorry
theorem mathd_numbertheory_320 (n : ℕ) (h₀ : n < 101) (h₁ : 101 ∣ (123456 - n)) : n = 34 := by sorry
theorem mathd_algebra_125 (x y : ℕ) (h₀ : 0 < x ∧ 0 < y) (h₁ : 5 * x = y) (h₂ : (↑x - (3:ℤ)) + (y - (3:ℤ)) = 30) : x = 6 := by sorry
theorem induction_11div10tonmn1ton (n : ℕ) : 11 ∣ (10^n - (-1 : ℤ)^n) := by sorry
theorem mathd_numbertheory_254 : (239 + 174 + 83) % 10 = 6 := by sorry
theorem amc12_2000_p6 (p q : ℕ) (h₀ : Nat.Prime p ∧ Nat.Prime q) (h₁ : 4 ≤ p ∧ p ≤ 18) (h₂ : 4 ≤ q ∧ q ≤ 18) : p * q - (p + q) ≠ 194 := by sorry
theorem imo_2019_p1 (f : ℤ → ℤ) : ((∀ a b, f (2 * a) + (2 * f b) = f (f (a + b))) ↔ (∀ z, f z = 0 \/ ∃ c, ∀ z, f z = 2 * z + c)) := by sorry
theorem aime_1984_p7 (f : ℤ → ℤ) (h₀ : ∀ n, 1000 ≤ n → f n = n - 3) (h₁ : ∀ n, n < 1000 → f n = f (f (n + 5))) : f 84 = 997 := by sorry
theorem numbertheory_3pow2pownm1mod2pownp3eq2pownp2 (n : ℕ) (h₀ : 0 < n) : (3^(2^n) - 1) % (2^(n + 3)) = 2^(n + 2) := by sorry
theorem mathd_numbertheory_85 : 1 * 3^3 + 2 * 3^2 + 2*3 + 2 = 53 := by sorry
theorem amc12_2001_p21 (a b c d : ℕ) (h₀ : a * b * c * d = 8!) (h₁ : a * b + a + b = 524) (h₂ : b * c + b + c = 146) (h₃ : c * d + c + d = 104) : ↑a - ↑d = (10 : ℤ) := by sorry
theorem amc12b_2002_p2 (x : ℤ) (h₀ : x = 4) : (3 * x - 2) * (4 * x + 1) - (3 * x - 2) * (4 * x) + 1 = 11 := by sorry
theorem mathd_numbertheory_517 : (121 * 122 * 123) % 4 = 2 := by sorry
theorem mathd_numbertheory_521 (m n : ℕ) (h₀ : Even m) (h₁ : Even n) (h₂ : m - n = 2) (h₃ : m * n = 288) : m = 18 := by sorry
theorem mathd_algebra_289 (k t m n : ℕ) (h₀ : Nat.Prime m ∧ Nat.Prime n) (h₁ : t < k) (h₂ : k^2 - m * k + n = 0) (h₃ : t^2 - m * t + n = 0) : m^n + n^m + k^t + t^k = 20 := by sorry
theorem amc12a_2021_p3 (x y : ℕ) (h₀ : x + y = 17402) (h₁ : 10∣x) (h₂ : x / 10 = y) : ↑x - ↑y = (14238:ℤ) := by sorry
theorem mathd_numbertheory_66 : 194 % 11 = 7 := by sorry
theorem mathd_numbertheory_235 : (29 * 79 + 31 * 81) % 10 = 2 := by sorry
theorem mathd_numbertheory_234 (a b : ℕ) (h₀ : 1 ≤ a ∧ a ≤ 9 ∧ b ≤ 9) (h₁ : (10 * a + b)^3 = 912673) : a + b = 16 := by sorry
theorem numbertheory_aoddbdiv4asqpbsqmod8eq1 (a : ℤ) (b : ℤ) (h₀ : Odd a) (h₁ : 4 ∣ b) (h₂ : b >= 0) : (a^2 + b^2) % 8 = 1 := by sorry
theorem mathd_numbertheory_222 (b : ℕ) (h₀ : Nat.lcm 120 b = 3720) (h₁ : Nat.gcd 120 b = 8) : b = 248 := by sorry
theorem mathd_numbertheory_541 (m n : ℕ) (h₀ : 1 < m) (h₁ : 1 < n) (h₂ : m * n = 2005) : m + n = 406 := by sorry
theorem mathd_algebra_314 (n : ℕ) (h₀ : n = 11) : (1 / 4)^(n + 1) * 2^(2 * n) = 1 / 4 := by sorry
theorem mathd_numbertheory_150 (n : ℕ) (h₀ : ¬ Nat.Prime (7 + 30 * n)) : 6 ≤ n := by sorry
theorem mathd_numbertheory_296 (n : ℕ) (h₀ : 2 ≤ n) (h₁ : ∃ x, x^3 = n) (h₂ : ∃ t, t^4 = n) : 4096 ≤ n := by sorry
theorem numbertheory_exk2powkeqapb2mulbpa2_aeq1 (a b : ℕ) (h₀ : 0 < a ∧ 0 < b) (h₁ : ∃ k > 0, 2^k = (a + b^2) * (b + a^2)) : a = 1 := by sorry
theorem mathd_numbertheory_185 (n : ℕ) (h₀ : n % 5 = 3) : (2 * n) % 5 = 1 := by sorry
theorem mathd_numbertheory_582 (n : ℕ) (h₀ : 0 < n) (h₁ : 3∣n) : ((n + 4) + (n + 6) + (n + 8)) % 9 = 0 := by sorry
