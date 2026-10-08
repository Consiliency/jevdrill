The plan is substantially coherent, but two issues need resolution before the interface freeze. Reusing `_prepare`/`select_plan`, preserving v1 contracts, separating discovery scope, and leaving decomposition to HOST are appropriate. The proposed privacy, reservation, replay and transactional deletion rules address the relevant invariants; their implementation remains to be demonstrated.

1. **Establish a usable observation path with enforceable output bounds — EC-ROUTE-3 and EC-ROUTE-6.**  
   Discovery requires finite output allowances and rejects unverified ceilings before dispatch. The supplied BAML functions configure timeouts but show no output-token enforcement; the adapter excerpt also provides no such mechanism. Boolean typing supplies no upper bound.

   This is missing capability evidence, not proof that the pinned client cannot support it. However, without resolving it, every provider-backed discovery attempt could correctly reject before navigation starts.

   **Bounded repair:** identify the enforcement mechanism supported by the locked client, assign any necessary changes to the owning lane, and specify a positive test through the generated discovery function under a finite allowance. Inspect the emitted request and test enforcement; a loopback response that merely happens to be short is insufficient. Preserve rejection of unsupported ceilings.

2. **Make terminal predicates unambiguous and exhaustive — EC-ROUTE-5–7.**  
   The plan includes the empty optional set among retained leaf choices, while `selected_guidance` requires a supported leaf. Clarify that the always-feasible empty alternative cannot itself establish positive discovery evidence and turn an incomplete search into success.

   Also resolve the complete-search case where resource judgments are positive but every optional resource is incompatible with otherwise feasible required guidance or exceeds context. “Zero suitable leaves” must distinguish Boolean suitability from final feasibility; this case should not fall between the result variants.

   **Bounded repair:** freeze explicit predicates and precedence, with fixtures proving:
   - No required guidance, incomplete search, no supported resource: the empty alternative cannot produce `selected_guidance`.
   - Complete rejection: `no_optional_guidance`.
   - Complete search with no feasible optional guidance: an explicit outcome preserving feasible required guidance.
   - Infeasible required guidance: `constraint_conflict`.
   - Incomplete search with supported feasible guidance: selection with uncertainty.

As a **verification suggestion**, explicitly exercise cached and same-key retry returns after discovery deletion, plus a late observation arriving after deletion. The plan already states the necessary deletion invariant; these tests would strengthen coverage beyond the final commit race.

The serial ownership structure is workable. The expanded reducer, current native matrix, production construction tests and entered negative controls are appropriate acceptance requirements. Their absence today is expected for proposed work and is not an additional readiness blocker. Scripted judgments can prove those software paths without establishing empirical judgment quality.

PARTIALLY AGREE