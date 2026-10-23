# B11 bounded axial-jump guard (candidate)

Base: `d9c6af9e9765505789b822b563dc1f4c3118c745`. The source-pinned section physics subtracts gross-block concrete stress for each discrete bar whose centre enters the equivalent concrete block. The resulting step can cause `N(c)-Ntarget` to cross zero without possessing any admissible root.

B11 derives each explicitly identifiable block-entry critical depth from the real supplied bar location, neutral-axis normal and immutable TS500 k1 and probes the actual pinned physics immediately on either side. If target axial demand straddles that measured jump, it rejects a sampled sign-bracket as `AXIAL_JUMP_CROSSES_TARGET`, retains an unresolved numerical state, and never labels this as a physical axial-capacity failure.

This improves **one identified hazardous discontinuity class**; it is NOT a proof of all roots, tangencies, full global uniqueness, valid continuous-angle capacity, or full code compliance. Source physics, independent oracle and canonical v1.3.1 documentation are byte-preserved. No manufactured PASS and no merge permission.