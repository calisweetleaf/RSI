"""RSNN3-000 boundary probes: Eigenrecursion routed through the canonical Zebra core.

Run from ``code-implementations`` with the substrate roots on PYTHONPATH:
    code-implementations; code-implementations/zebra-core;
    code-implementations/tensors-and-weights/recursive-tensor
    python -B -m unittest -v eigenrecursion.test_eigenrecursion_substrate
"""
import unittest
from pathlib import Path
import warnings

import numpy as np
import torch

import zebra_core
from eigenrecursion import eigenrecursion_algorithm as ea
from eigenrecursion import eigenrecursive_operations as eo


class EigenrecursionProtocolTests(unittest.TestCase):
    def _run(self, operator, initial):
        return ea.Eigenrecursion(operator, state_dim=initial.size).find_fixed_point(initial)

    def test_stabilizer_resolves_to_canonical_zebra_core(self):
        self.assertIs(ea.EigenrecursionStabilizer, zebra_core.EigenrecursionStabilizer)
        self.assertIs(eo.EigenrecursionStabilizer, zebra_core.EigenrecursionStabilizer)

    def test_contraction_converges_with_rldis_enabled(self):
        result = self._run(lambda s: 0.5 * s + 0.5, np.zeros(4))
        self.assertEqual(result["status"], ea.ConvergenceStatus.CONVERGED)
        self.assertIsNone(result["error"])
        self.assertGreater(result["iterations"], 1)
        np.testing.assert_allclose(result["fixed_point"], np.ones(4), atol=1e-4)

    def test_divergent_operator_reports_divergence(self):
        result = self._run(lambda s: 2.0 * s + 1.0, np.ones(4))
        self.assertEqual(result["status"], ea.ConvergenceStatus.DIVERGED)
        self.assertIsNone(result["error"])

    def test_oscillating_operator_reports_cycle(self):
        result = self._run(lambda s: -s, np.ones(4))
        self.assertEqual(result["status"], ea.ConvergenceStatus.CYCLE_DETECTED)

    def test_operator_failure_is_surfaced_not_swallowed(self):
        def failing(_state):
            raise ValueError("operator failure")

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            result = self._run(failing, np.ones(4))
        self.assertEqual(result["status"], ea.ConvergenceStatus.ERROR)
        self.assertIn("operator failure", result["error"])
        self.assertTrue(any("Eigenrecursion aborted" in str(w.message) for w in caught))


class MergedDuplicateClassTests(unittest.TestCase):
    def test_single_definition_per_merged_class(self):
        source = Path(ea.__file__).read_text(encoding="utf-8")
        for name in ("EigenrecursionTracer", "BayesianInterventionSelector",
                     "GradientContradictionResolver", "MetaCognitionAmplifier"):
            self.assertEqual(source.count(f"class {name}:"), 1, name)

    def test_tracer_keeps_original_trace_and_grafted_depth_api(self):
        tracer = ea.EigenrecursionTracer(state_dim=2, max_trace_length=3)
        for depth in range(5):
            tracer.record_step(np.full(2, depth, dtype=float), depth, {"distance": float(depth)})
        self.assertEqual(len(tracer.trace), 3)
        self.assertEqual(tracer.depth_history, [2, 3, 4])
        self.assertEqual(tracer.distances, [2.0, 3.0, 4.0])
        self.assertEqual(len(tracer.computation_times), 3)
        np.testing.assert_array_equal(tracer.get_trace()[-1], np.full(2, 4.0))

    def test_bayesian_selector_keeps_conjugate_update_and_severity_gate(self):
        selector = ea.BayesianInterventionSelector()
        selector.update_posterior("pattern_breaking", "repetition", True)
        selector.update_posterior("meta_escalation", "repetition", False)
        self.assertEqual(
            selector.select_optimal_intervention("repetition", ["meta_escalation", "pattern_breaking"]),
            "pattern_breaking",
        )
        self.assertEqual(
            selector.select_intervention(None, ea.RLDISSeverityLevel.CRITICAL), "EMERGENCY_STOP"
        )

    def test_contradiction_resolver_takes_a_real_gradient_step(self):
        resolver = ea.GradientContradictionResolver(learning_rate=0.1)
        kb = {"p": torch.tensor([1.0, 0.2]), "not_p": torch.tensor([-1.0, 0.1])}
        before = resolver.compute_contradiction_loss(kb)
        updated = resolver.minimize_contradiction(kb)
        after = resolver.compute_contradiction_loss(updated)
        self.assertGreater(before, 0.0)
        self.assertLess(after, before)
        self.assertFalse(torch.equal(updated["p"], kb["p"]))

    def test_resolver_descends_scalar_tension_field(self):
        resolver = ea.GradientContradictionResolver(learning_rate=0.1)
        target = torch.tensor([0.5, -0.5])
        start = torch.zeros(2)
        end = resolver.resolve(start, lambda s: ((s - target) ** 2).sum(), num_iterations=50)
        self.assertLess(float(torch.norm(end - target)), float(torch.norm(start - target)) * 0.1)

    def test_amplifier_maps_depth_to_thinking_level(self):
        amp = ea.MetaCognitionAmplifier(max_thinking_level=2)
        state = np.array([1.0, 3.0])
        np.testing.assert_array_equal(amp.amplify(state, 0), state)
        np.testing.assert_allclose(amp.amplify(state, 99), amp.process_at_thinking_level(state, 2))


class EigenstateEngineTests(unittest.TestCase):
    def _converge(self):
        torch.manual_seed(0)
        config = eo.EigenstateConfig(max_iterations=200, convergence_threshold=1e-6)
        engine = eo.EigenstateConvergenceEngine(config)
        result = engine.converge_to_eigenstate(torch.randn(16), eo.EigenrecursiveOperator(16, config))
        return engine, result

    def test_engine_runs_on_torch_state_with_zebra_stabilizer(self):
        engine, result = self._converge()
        self.assertIsInstance(engine.stabilizer, zebra_core.EigenrecursionStabilizer)
        self.assertEqual(tuple(result.final_state.shape), (16,))
        self.assertTrue(bool(torch.isfinite(result.final_state).all()))
        self.assertLess(result.stability_analysis["spectral_radius"], 1.0)

    @unittest.expectedFailure
    def test_engine_converges_on_contracting_operator(self):
        # Known defect (RSNN3-000): the engine layers tension descent, identity/quantum
        # blends, free-energy and natural-gradient updates on top of a contracting
        # operator (spectral radius < 1); the composite map does not converge.
        _, result = self._converge()
        self.assertTrue(result.converged)


if __name__ == "__main__":
    unittest.main(verbosity=2)
