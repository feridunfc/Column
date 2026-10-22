# v1.2 A/B acceptance pilot

No ETABS, model mutation, rebar search, design PASS or S1/S2 edits. Typed quantity, station/step and analysis bundle contracts; explicitly provided 400 x 600 mm reinforcement cage; strain-compatible TS500 section kernel through a narrow adapter; deterministic passive JSON. Kernel has fixed 100 iterations; nonmatching max_iterations fails closed. Multi-run compatibility references are not native run certification. Check independent 8-point Gauss-Legendre strip oracle in tests. A/B does not qualify column design, second order, shear, confinement or joint. Run `python -m unittest discover -s tests -v`.

Fixed neutral-axis stress resultant fields use the `state_` prefix. Fixed-N PMM radial capacity is a separate optional output; they are never falsely declared to be the same equilibrium state. Both transverse local axes reversed together are transformed, including neutral-axis orientation and moment signs; reflecting a single transverse axis is rejected.
