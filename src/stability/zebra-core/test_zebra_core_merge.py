"""Boundary regression probes for the canonical monolithic Zebra module."""
import unittest

import numpy as np

import zebra_core as zebra


class ZebraCoreMergeTests(unittest.TestCase):
    def test_original_eigenrecursion_core_remains_callable(self):
        stabilizer = zebra.EigenrecursionStabilizer(dimension=2, max_iterations=100)
        fixed, converged, iterations, status = stabilizer.find_fixed_point(
            lambda state: 0.5 * state + 0.5,
            np.zeros(2),
        )
        self.assertTrue(converged, status)
        self.assertEqual(status, "CONVERGED")
        self.assertGreater(iterations, 1)
        np.testing.assert_allclose(fixed, np.ones(2), atol=1e-6)

    def test_v3_scanner_is_the_canonical_overlapping_scanner(self):
        self.assertTrue(issubclass(zebra.SpectralPhaseScanner, zebra.SpectralPhaseScannerV3))
        params = np.linspace(-1.0, 1.0, 9)
        factory = lambda p: np.array([[p, 0.08], [0.08, -p]], dtype=float)

        tracked = zebra.SpectralPhaseScanner().scan(factory, params)
        self.assertEqual(tracked.n_parameters, len(params))
        self.assertEqual(tracked.n_eigenvalues, 2)
        self.assertGreater(tracked.n_crossings, 0)
        quality = tracked.min_quality_report()
        self.assertLess(quality["max_residual_error"], 1e-10)
        self.assertLess(quality["max_orthogonality_error"], 1e-10)

        core_result = zebra.SpectralPhaseScanner().scan_to_core_result(factory, params)
        self.assertIsInstance(core_result, zebra.SpectralPhaseResult)
        self.assertEqual(core_result.n_parameters, len(params))
        self.assertEqual(core_result.condition_numbers.shape, (len(params),))
        self.assertTrue(np.all(np.isfinite(core_result.condition_numbers)))
        self.assertEqual(core_result.eigenvector_stabilities.shape, (len(params),))
        self.assertTrue(np.all(np.isfinite(core_result.eigenvector_stabilities)))
        self.assertIn("condition_numbers", core_result.to_dict())
        self.assertTrue(hasattr(zebra.SpectralPhaseScanner, "_compute_condition_trajectory"))
        self.assertTrue(hasattr(zebra.SpectralPhaseScanner, "_compute_stability_trajectory"))
        flagged = zebra.SpectralPhaseScanner(n_parallel=2).scan(
            factory, params, compute_condition=True, compute_eigenvector_stability=True
        )
        self.assertEqual(flagged.condition_numbers.shape, (len(params),))
        self.assertEqual(flagged.eigenvector_stabilities.shape, (len(params),))

    def test_repaired_continued_fraction_pole_result_contract(self):
        analyzer = zebra.ContinuedFractionAnalyzer(n_terms=3)
        samples = np.array([-1.0, -0.5, 0.5, 1.0], dtype=float)
        moments = np.array([np.mean(samples ** k) for k in range(6)], dtype=float)
        analyzer.fit_from_moments(moments)

        result = analyzer.pole_strength_analysis()
        self.assertTrue(
            {"poles", "strengths", "weights", "n_terms_used", "density_support", "total_weight"}
            <= set(result)
        )
        self.assertEqual(result["n_terms_used"], 3)
        self.assertEqual(len(result["poles"]), 3)
        self.assertAlmostEqual(sum(result["strengths"]), 1.0, places=10)
        self.assertAlmostEqual(result["total_weight"], 1.0, places=10)


    def test_unique_spectral_statistics_and_free_kde(self):
        stats = zebra.SpectralStatisticsV3.adjacent_gap_ratio([0.0, 1.0, 3.0, 6.0])
        self.assertEqual(len(stats["ratios"]), 2)
        self.assertTrue(np.isfinite(stats["mean_ratio"]))
        grid, density = zebra.FreeProbabilityOperator.from_spectrum(
            np.array([-1.0, -0.25, 0.5, 1.25])
        ).free_kde(n_grid=32)
        self.assertEqual(grid.shape, (32,))
        self.assertEqual(density.shape, (32,))
        self.assertTrue(np.all(np.isfinite(density)))
        self.assertTrue(np.all(density >= 0.0))

    def test_unique_spectral_graph_wavelet_transform(self):
        laplacian = np.array([[1.0, -1.0, 0.0], [-1.0, 2.0, -1.0], [0.0, -1.0, 1.0]])
        transform = zebra.SpectralGraphWaveletTransform(n_scales=3).fit(laplacian)
        coefficients = transform.transform(np.array([1.0, 0.0, -1.0]))
        self.assertEqual(len(coefficients), 3)
        self.assertTrue(all(np.asarray(c).shape == (3,) for c in coefficients))


if __name__ == "__main__":
    unittest.main(verbosity=2)
