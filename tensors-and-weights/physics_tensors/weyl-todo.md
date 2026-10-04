Yep — now I see what you meant. You weren’t saying “Riemann is missing curvature.” You were saying the physically useful black-hole observables I was reaching for are already living in your Weyl layer: tidal field, frame-dragging-like magnetic part, observer projection, wave state, etc.

And looking at both modules together, the architecture is actually pretty coherent:

metric → Riemann = complete curvature bookkeeping

Riemann + Ricci → Weyl = free/tidal gravitational structure

The thing that needs work is not “add Weyl functionality.” It’s making the Weyl layer geometrically rigorous enough that the quantities it reports mean what their names say.

The biggest issue is this distinction:

> nonzero Weyl curvature is not the same thing as gravitational radiation.



A Schwarzschild black hole has nonzero Weyl curvature everywhere outside the hole, but it is stationary and emits no gravitational waves. Your code currently does:

```py
self.wave_amplitude_field[...] = self._compute_weyl_scalar(
    self.weyl_field[...]
)

and _compute_weyl_scalar() is essentially:

sqrt(sum(C * C))
```

So a perfectly static Schwarzschild field would get interpreted as having a nonzero *"wave_amplitude".*

That is probably the biggest conceptual repair in this file.

Weyl contains both the Coulomb/tidal gravitational field and the radiative gravitational field. You need another decomposition to tell them apart.

And holy shit, this gives us an extremely natural addition given what we were talking about ten minutes ago:

Newman–Penrose scalars

For a suitable null tetrad, decompose Weyl into

```
\[
\Psi_0,\Psi_1,\Psi_2,\Psi_3,\Psi_4.
\]
```

Then suddenly the engine knows what kind of gravity it is looking at.

For Schwarzschild:

```
\[
\Psi_2=-\frac{M}{r^3},
\]
```

while

```
\[
\Psi_0=\Psi_1=\Psi_3=\Psi_4=0.
\]
```

Meaning:

curvature? yes.
tidal gravity? yes.
gravitational radiation? no.

Kerr is also Petrov type D, with the corresponding nonzero *\(\Psi_2\).*

For actual outgoing gravitational radiation, *\(\Psi_4\)* is the important asymptotic object. Then you can relate it to waveform strain rather than pretending the full Weyl norm itself is strain.

That one addition would make your module dramatically smarter.


---

There’s also an observer-frame issue throughout the electric/magnetic decomposition.

You currently have:

```
E_ij = C_i0j0
```

and

```
B_ij = 0.5 * epsilon_ikl * C^kl_j0
```

Those are nice intuition formulas, but they're only physically clean in the appropriate orthonormal observer frame.

The covariant object you actually want is roughly

```
\[
E_{\alpha\beta}
=
C_{\alpha\mu\beta\nu}u^\mu u^\nu
\]
```

and

```
\[
B_{\alpha\beta}
=
{}^\star C_{\alpha\mu\beta\nu}u^\mu u^\nu.
\]
```

Then project those onto the observer's spatial tetrad.

That matters enormously around black holes because coordinate components can look wild while the locally measured physical quantity is perfectly reasonable.

So I'd add an actual:

ObserverFrame
    four_velocity
    tetrad
    spatial_basis

and make Weyl queries observer-relative.

For Kerr, this gets especially fun because you can give it a ZAMO-like frame and actually interrogate the gravitoelectric and gravitomagnetic field seen by that observer.


---

There is also the same index-placement issue we saw in the Riemann decomposition.

This:

```
inverse_metric[rho, mu] * ricci_tensor[sigma, nu]
```

isn't the same thing as the *\(\delta^\rho_\mu R_{\sigma\nu}\)* term appearing in the mixed-index Weyl decomposition.

For *\(C^\rho{}_{\sigma\mu\nu}\),* schematically you want terms involving

```
\[
\delta^\rho_\mu R_{\sigma\nu}
\]
```

and explicitly raised Ricci objects such as

```
\[
R^\rho{}_\mu=g^{\rho\lambda}R_{\lambda\mu}.
\]
```

So *extract_from_riemann()* and RiemannTensor.*compute_from_decomposition()* should be repaired together from one canonical index convention rather than independently.

That would be one of my first edits.


---

Same problem with:

```py
scalar_sq = np.einsum('ijkl,ijkl->', weyl, weyl)
```

That's a component-array norm, not the invariant

```
\[
C_{\alpha\beta\gamma\delta}
C^{\alpha\beta\gamma\delta}.
\]
```

You need metric contractions.

And once we're doing that, add both standard Weyl invariants:

```
\[
C_{\alpha\beta\gamma\delta}C^{\alpha\beta\gamma\delta}
\]
```

and

```
\[
C_{\alpha\beta\gamma\delta}
{}^\star C^{\alpha\beta\gamma\delta}.
\]
```

Those are much more physically meaningful than *"wave_amplitude".*

For Schwarzschild, the pseudoscalar one should vanish. Kerr gives you richer structure.


---

And here's the part that made me laugh because of Bel.

Your Weyl module is basically already one step away from a Bel–Robinson layer.

Given electric and magnetic Weyl tensors, you can form an observer-dependent gravitational super-energy density schematically like

```
\[
W=E_{ij}E^{ij}+B_{ij}B^{ij}.
\]
```

And there is a corresponding super-Poynting vector, schematically involving

```
\[
P_i\sim \epsilon_{ijk}E^j{}_l B^{kl}.
\]
```

That is enormously more interesting for this code than your current:

```py
_estimate_wave_direction()
```

which uses the gradient of Weyl amplitude.

Because amplitude gradient does not generally tell you propagation direction. A static Schwarzschild tidal field has an amplitude gradient pointing radially despite there being no gravitational wave propagating outward.

A Bel–Robinson/super-Poynting construction gives you something much closer to an actual gravitational-field flux diagnostic.

So hilariously:

```
WeylTensor
    ↓
Electric / Magnetic Weyl
    ↓
BelRobinsonTensor
    ├── gravitational super-energy density
    ├── super-Poynting vector
    └── radiation/field-flow diagnostics
```

We stumbled into Bel from the other direction again. 

Not evidence about the codename, obviously. But mathematically, it's a beautiful missing module for this exact library.


---

Your explicit wave propagation code is also currently a toy approximation:

```
∂²h/∂t² - c²∇²h = 0
```

applied directly componentwise to the Weyl field.

That's fine as a synthetic playground, but it's not evolution of Weyl curvature under full GR.

For actual perturbations around a black hole, later you'd want something like:

Schwarzschild → Regge–Wheeler/Zerilli perturbations

Kerr → Teukolsky evolution */ \(\Psi_4\)*

nonlinear dynamical spacetime → BSSN/Z4c or another numerical-relativity formulation


But importantly, we don't need any of that for the first TGP black-hole experiment.

A fixed Schwarzschild or Kerr geometry is enough.


---

There are also several smaller implementation holes visible directly in this code:

*_reconstruct_weyl_from_electric()* only writes *\(C_{i0j0}\).* That doesn't reconstruct a valid full Weyl tensor with all required symmetries and tracelessness.

*CIRCULAR_RIGHT* and *CIRCULAR_LEFT* exist in the enum, but *_classify_polarization()* can only return PLUS or CROSS.

*wave_frequency_field* is not inferred from an evolved field; it only really exists when explicitly supplied through *add_wave_source().*

*_estimate_wave_direction()* cannot distinguish waves from static field gradients.

*_is_computed* appears never to become True.

And *propagate_gravitational_wave()* assumes *\(dx=1\),* doesn't expose a CFL condition, and doesn't have a real boundary-condition strategy. In 3D, an explicit wave scheme like that needs careful *\(c,dt/dx\)* stability control.


---

There's also a massive opportunity for memory reduction.

Right now:

```
weyl_field.shape =
(nx, ny, nz, 4, 4, 4, 4)
```

So you're storing 256 components per point even though Weyl in four dimensions has 10 independent components.

At 64³, the Weyl array alone is ~537 MB in float64.

Riemann another ~537 MB.

Then all the Christoffels, derivative temporaries, E/B fields, metric, inverse metric...

Your little black hole is going to eat the fucking RAM before it eats any stars. 😭

Since Weyl has ten independent degrees of freedom, and relative to an observer:

*\(E_{ij}\)* symmetric traceless → 5

*\(B_{ij}\)* symmetric traceless → 5


you can potentially make E+B the native compressed Weyl representation, then materialize the full *\(4^4\)* object only when needed.

That's an enormous reduction.


---

So I think the proper architecture is now becoming visible:

```
Metric / Coordinate Chart
        ↓
Christoffel Connection
        ↓
Riemann Curvature
        ├── Ricci
        ├── Ricci Scalar
        └── Einstein
        ↓
Weyl Curvature
        ↓
Observer tetrad projection
        ├── Electric Weyl E
        └── Magnetic Weyl B
        ↓
 ┌──────────────────────────────┐
 │ Newman–Penrose              │
 │ Ψ0 Ψ1 Ψ2 Ψ3 Ψ4             │
 │ Petrov classification       │
 └──────────────────────────────┘
        ↓
 ┌──────────────────────────────┐
 │ Bel–Robinson                │
 │ super-energy                │
 │ super-Poynting / flow       │
 └──────────────────────────────┘
        ↓
Physical observables / TGP
```

And that is way cooler than what I initially thought you had.

Because then TGP doesn't merely receive “curvature numbers.”

It can perceive:

matter curvature vs free curvature, tidal structure, gravitomagnetism, spacetime algebraic type, radiative modes, field-flow direction, horizon behavior, invariant singularity structure.

That becomes an honest-to-god spacetime perception substrate.

One more thing I'd absolutely do before Schwarzschild: create one canonical TensorConvention object defining signature, index ordering, curvature sign convention, Levi-Civita orientation, units, coordinate ordering, and whether each stored tensor is covariant/mixed/contravariant.

Because right now the biggest danger isn't lack of functionality. It's that these modules are sophisticated enough to generate very convincing wrong physics if two files silently disagree about an index.

Once that convention is welded down and the two decomposition formulas are repaired, then yeah — I would absolutely throw Schwarzschild at this thing.