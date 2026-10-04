import numpy as np

import numpy as np
from typing import Optional, Tuple, Dict, Any

try:
    from cosmic_scroll_logger import get_cosmic_scroll_logger
except ImportError:
    try:
        from unified_cosmos.cosmic_scroll_logger import get_cosmic_scroll_logger
    except ImportError:
        get_cosmic_scroll_logger = None

class RicciTensor:
    """
    Ricci Tensor: Encodes spacetime curvature for the Genesis Cosmos simulation.
    Used in Einstein's field equations and for calculating gravitational effects.

    This class serves as a container for the Ricci tensor, allowing it to be set,
    retrieved, traced, and its scalar value calculated. It also provides methods
    to compute itself from a Riemann tensor and to interpret its physical implications.
    """
    def __init__(self, dimensions: int = 4):
        """
        Initializes the RicciTensor object.

        Args:
            dimensions (int): The number of spacetime dimensions (e.g., 4 for 3+1 spacetime).
        """
        self.dimensions = dimensions
        self.tensor = np.zeros((dimensions, dimensions))

    def compute_from_stress_energy(self, stress_energy: np.ndarray) -> np.ndarray:
        """
        Minimal helper to derive a Ricci tensor approximation from a stress-energy tensor.
        For now, treats stress-energy as proportional to curvature (placeholder mapping).
        """
        self.tensor = np.array(stress_energy, dtype=float)
        return self.tensor

    def compute_from_stress_energy(self, stress_energy: np.ndarray) -> np.ndarray:
        """
        Disconnected placeholder. It assigns Ricci from stress-energy and is not
        a Ricci contraction. SharedSpacetimeField must not call it.
        """
        # Simple proportional mapping; real use would require full GR equations
        self.tensor = np.array(stress_energy, dtype=float)
        return self.tensor

    def compute_from_riemann(self, riemann_tensor_field: np.ndarray) -> np.ndarray:
        """
        Computes the Ricci tensor field from a given Riemann curvature tensor field.
        The Ricci tensor R_μν is obtained by contracting the Riemann tensor R^α_μαν.

        Args:
            riemann_tensor_field (np.ndarray): The Riemann curvature tensor field.
                                                Its shape should be (grid_x, grid_y, ..., dim, dim, dim, dim).

        Returns:
            np.ndarray: The computed Ricci tensor field (shape: grid_x, grid_y, ..., dim, dim).

        Raises:
            ValueError: If the Riemann tensor field has an incorrect shape.
        """
        expected_riemann_shape_suffix = (self.dimensions, self.dimensions, self.dimensions, self.dimensions)
        if riemann_tensor_field.shape[-4:] != expected_riemann_shape_suffix:
            raise ValueError(
                f"Riemann tensor field must have shape (..., {self.dimensions}, {self.dimensions}, {self.dimensions}, {self.dimensions}), "
                f"but got {riemann_tensor_field.shape}"
            )

        spatial_grid_shape = riemann_tensor_field.shape[:-4]
        Ricci = np.zeros(spatial_grid_shape + (self.dimensions, self.dimensions))

        for idx in np.ndindex(spatial_grid_shape):
            for mu in range(self.dimensions):
                for nu in range(self.dimensions):
                    ricci_sum = 0.0
                    for alpha in range(self.dimensions):
                        # R_mu_nu = R^alpha_mu_alpha_nu
                        ricci_sum += riemann_tensor_field[idx + (alpha, mu, alpha, nu)]
                    Ricci[idx + (mu, nu)] = ricci_sum
        
        self.tensor = Ricci
        return self.tensor

    def set(self, new_tensor: np.ndarray) -> None:
        """
        Sets the Ricci tensor.

        Args:
            new_tensor (np.ndarray): The new tensor to set. Its shape should be
                                   (..., dimensions, dimensions).
        """
        if new_tensor.shape[-2:] != (self.dimensions, self.dimensions):
            raise ValueError(f"New tensor must have shape (..., {self.dimensions}, {self.dimensions}).")
        self.tensor = np.array(new_tensor)

    def get(self) -> np.ndarray:
        """
        Returns the current Ricci tensor.

        Returns:
            np.ndarray: The Ricci tensor.
        """
        return self.tensor

    def trace(self) -> np.ndarray:
        """
        Computes the trace of the Ricci tensor (R_μν).

        Returns:
            np.ndarray: The trace of the Ricci tensor. If the tensor is a field,
                        this will return a field of traces.
        """
        return np.trace(self.tensor, axis1=-2, axis2=-1)

    def scalar(self) -> np.ndarray:
        """
        Computes the Ricci scalar (R = g^μν R_μν).
        Note: This requires the inverse metric tensor, which is not stored here.
        This method assumes the Ricci tensor is already contracted with the inverse metric
        or is a single tensor whose trace is the scalar.

        Returns:
            np.ndarray: The Ricci scalar. If the tensor is a field,
                        this will return a field of Ricci scalars.
        """
        # For a single Ricci tensor, the trace is often referred to as the Ricci scalar.
        # For a Ricci tensor field, this returns a field of scalars.
        return self.trace()

    def is_vacuum_solution(self, tolerance: float = 1e-9) -> bool:
        """
        Checks if the spacetime is a vacuum solution, i.e., if the Ricci tensor is approximately zero.
        In General Relativity, R_μν = 0 implies a vacuum solution (no matter or energy).

        Args:
            tolerance (float): The numerical tolerance for checking against zero.

        Returns:
            bool: True if the Ricci tensor is approximately zero everywhere, False otherwise.
        """
        return bool(np.all(np.abs(self.tensor) < tolerance))

    def is_einstein_space(self, metric_tensor: np.ndarray, tolerance: float = 1e-9) -> bool:
        """
        Checks if the spacetime is an Einstein space, where the Ricci tensor is proportional
        to the metric tensor (R_μν = λg_μν) for some constant λ (the Einstein constant).

        Args:
            metric_tensor (np.ndarray): The metric tensor (g_μν) corresponding to this Ricci tensor.
                                        Its shape must match the Ricci tensor's shape.
            tolerance (float): The numerical tolerance for checking proportionality.

        Returns:
            bool: True if the spacetime is an Einstein space, False otherwise.
        
        Raises:
            ValueError: If the metric_tensor's shape does not match the Ricci tensor's shape.
        """
        if self.tensor.shape != metric_tensor.shape:
            raise ValueError("Metric tensor shape must match Ricci tensor shape to check for Einstein space.")

        # Calculate lambda (λ) from the trace of the Ricci tensor and the metric
        # R = g^μν R_μν = g^μν λ g_μν = λ g^μν g_μν = λ * dim
        # So, λ = R / dim
        # This requires the inverse metric to compute R, which is not directly available here.
        # A simpler check: R_μν / g_μν should be constant (λ).

        # Avoid division by zero for metric components that are zero
        non_zero_metric_mask = np.abs(metric_tensor) > tolerance
        if not np.any(non_zero_metric_mask):
            # If metric is all zeros, it's not a valid Einstein space (unless both are zero everywhere)
            return self.is_vacuum_solution(tolerance)

        # Calculate potential lambda values where metric is non-zero
        potential_lambdas = np.where(non_zero_metric_mask, self.tensor / metric_tensor, 0)

        # Check if these potential lambda values are approximately constant
        # We can take the mean of non-zero lambdas and check deviation
        if np.any(non_zero_metric_mask):
            mean_lambda = np.mean(potential_lambdas[non_zero_metric_mask])
            return bool(np.all(np.abs(self.tensor - mean_lambda * metric_tensor) < tolerance))
        else:
            return False # No non-zero metric components to compare

    def volume_deformation_rate(self, metric_tensor: np.ndarray) -> np.ndarray:
        """
        Calculates the rate of volume deformation (expansion or contraction) of a small
        ball of test particles in spacetime, as described by the Ricci tensor.
        This is related to the trace of the Ricci tensor, but more precisely involves
        the Ricci tensor's effect on geodesics.

        For a congruence of geodesics, the rate of change of the expansion scalar θ is given by:
        dθ/dτ = -R_μν u^μ u^ν - 2σ^2 + 2ω^2
        where u^μ is the 4-velocity, σ^2 is the shear scalar, and ω^2 is the vorticity scalar.
        The Ricci tensor term -R_μν u^μ u^ν describes the tidal forces due to matter/energy.

        For simplicity, and focusing on the Ricci tensor's direct contribution to volume change,
        we can consider the average volume deformation rate proportional to the Ricci scalar.
        A more rigorous approach would involve the full Raychaudhuri equation.

        Returns:
            np.ndarray: A scalar field representing the average volume deformation rate
                        across the spatial grid. Positive values indicate expansion, negative contraction.
        """
        # The Ricci scalar R is directly related to the average volume deformation.
        # In vacuum (R=0), there is no average volume deformation.
        # In the presence of matter, R != 0, indicating volume changes.
        # The sign convention for R varies, but generally, positive R implies contraction
        # (e.g., in a dust-filled universe, R > 0).

        # For a more direct physical interpretation, we can use the Ricci scalar.
        # The Ricci scalar R is proportional to the trace of the energy-momentum tensor (T).
        # R = 8πG/c^4 * T
        # So, a non-zero Ricci scalar indicates the presence of matter/energy that causes volume deformation.

        # We will return the Ricci scalar as the primary indicator of volume deformation rate.
        # The interpretation of sign (expansion vs. contraction) depends on the specific context
        # and conventions (e.g., mostly positive for matter-dominated spacetimes).
        # For a more complete picture, one would need the full energy-momentum tensor.

        # To make it more physically intuitive, let's return the Ricci scalar, and note its interpretation.
        # We need the inverse metric to compute the true Ricci scalar from R_mu_nu.
        # Since EinsteinTensor computes the Ricci scalar field, we can leverage that.
        # However, this class is meant to be standalone for Ricci tensor operations.

        # Let's assume for this method that the Ricci scalar is already computed or can be derived
        # from the Ricci tensor and a provided metric.

        # If the Ricci tensor is a field, we return a field of deformation rates.
        # If it's a single tensor, we return a single scalar.

        # For a simple interpretation, we can use the trace of the Ricci tensor as a proxy
        # for the Ricci scalar, assuming a flat or simple metric for this interpretation.
        # A positive trace often implies a tendency towards contraction, and negative towards expansion.
        return self.trace()

    def get_ricci_eigenvalues(self) -> np.ndarray:
        """
        Computes the eigenvalues of the Ricci tensor at each point in the field.
        These eigenvalues describe the magnitudes of curvature along principal axes.

        Returns:
            np.ndarray: An array of eigenvalues. If the Ricci tensor is a field,
                        the shape will be (spatial_grid_shape, dimensions).
        
        Raises:
            ValueError: If the Ricci tensor is not initialized.
        """
        if self.tensor is None or self.tensor.size == 0:
            raise ValueError("Ricci tensor is not initialized. Cannot compute eigenvalues.")

        # Reshape the tensor to handle spatial dimensions and then the 2x2 or 4x4 tensor part
        original_shape = self.tensor.shape
        spatial_grid_shape = original_shape[:-2]
        tensor_dim = original_shape[-1]

        # Flatten spatial dimensions for batch processing with np.linalg.eigvalsh
        # np.linalg.eigvalsh is for Hermitian/symmetric matrices, which Ricci tensor is.
        flattened_tensor = self.tensor.reshape(-1, tensor_dim, tensor_dim)

        eigenvalues = np.linalg.eigvalsh(flattened_tensor)

        # Reshape back to original spatial dimensions + eigenvalues
        return eigenvalues.reshape(spatial_grid_shape + (tensor_dim,))

    def get_ricci_eigenvectors(self) -> np.ndarray:
        """
        Computes the eigenvectors of the Ricci tensor at each point in the field.
        These eigenvectors indicate the principal directions of curvature.

        Returns:
            np.ndarray: An array of eigenvectors. If the Ricci tensor is a field,
                        the shape will be (spatial_grid_shape, dimensions, dimensions),
                        where the last two dimensions represent the eigenvectors (columns).
        
        Raises:
            ValueError: If the Ricci tensor is not initialized.
        """
        if self.tensor is None or self.tensor.size == 0:
            raise ValueError("Ricci tensor is not initialized. Cannot compute eigenvectors.")

        original_shape = self.tensor.shape
        spatial_grid_shape = original_shape[:-2]
        tensor_dim = original_shape[-1]

        flattened_tensor = self.tensor.reshape(-1, tensor_dim, tensor_dim)

        # np.linalg.eigh returns eigenvalues and eigenvectors (v[:, i] is the eigenvector corresponding to w[i])
        # For symmetric matrices, eigenvectors are orthogonal.
        _, eigenvectors = np.linalg.eigh(flattened_tensor)

        return eigenvectors.reshape(spatial_grid_shape + (tensor_dim, tensor_dim))

    def to_ml_features(self, feature_set: str = 'all') -> np.ndarray:
        """
        Extracts various properties of the Ricci tensor as features for machine learning models.

        Args:
            feature_set (str): Specifies which set of features to extract:
                                'tensor_components': Flattened components of the Ricci tensor.
                                'scalar': The Ricci scalar.
                                'eigenvalues': The eigenvalues of the Ricci tensor.
                                'all': All available features (default).

        Returns:
            np.ndarray: A flattened NumPy array representing the chosen features.
                        If the Ricci tensor is a field, the output will be a 2D array
                        where each row corresponds to a spatial point and columns are features.

        Raises:
            ValueError: If the Ricci tensor is not initialized or an invalid feature_set is specified.
        """
        if self.tensor is None or self.tensor.size == 0:
            raise ValueError("Ricci tensor is not initialized. Cannot extract ML features.")

        features = []
        spatial_grid_shape = self.tensor.shape[:-2]
        num_spatial_points = np.prod(spatial_grid_shape)

        if feature_set == 'tensor_components' or feature_set == 'all':
            # Flatten the tensor components for each spatial point
            features.append(self.tensor.reshape(num_spatial_points, -1))

        if feature_set == 'scalar' or feature_set == 'all':
            scalar_field = self.scalar()
            features.append(scalar_field.reshape(num_spatial_points, -1))

        if feature_set == 'eigenvalues' or feature_set == 'all':
            eigenvalues = self.get_ricci_eigenvalues()
            features.append(eigenvalues.reshape(num_spatial_points, -1))

        if not features:
            raise ValueError(f"Invalid feature_set specified: {feature_set}")

        # Concatenate features along the last axis (columns)
        return np.concatenate(features, axis=-1)

    def get_attention_weights(self, weighting_strategy: str = 'scalar_magnitude') -> np.ndarray:
        """
        Generates a scalar field of 'attention weights' based on the Ricci tensor's properties.
        Regions with higher weights can be interpreted as more 'important' or 'salient' for an AI.

        Args:
            weighting_strategy (str): The strategy to use for generating weights:
                                      'scalar_magnitude': Absolute value of the Ricci scalar (default).
                                      'eigenvalue_spread': Range (max - min) of eigenvalues, indicating complexity.
                                      'traceless_magnitude': Frobenius norm of the traceless Ricci tensor.

        Returns:
            np.ndarray: A scalar field (same spatial dimensions as the Ricci tensor field)
                        where each point has a weight. Weights are normalized to sum to 1.

        Raises:
            ValueError: If the Ricci tensor is not initialized or an invalid weighting_strategy is specified.
        """
        if self.tensor is None or self.tensor.size == 0:
            raise ValueError("Ricci tensor is not initialized. Cannot compute attention weights.")

        weights = np.zeros(self.tensor.shape[:-2]) # Initialize with spatial grid shape

        if weighting_strategy == 'scalar_magnitude':
            weights = np.abs(self.scalar())
        elif weighting_strategy == 'eigenvalue_spread':
            eigenvalues = self.get_ricci_eigenvalues()
            weights = np.max(eigenvalues, axis=-1) - np.min(eigenvalues, axis=-1)
        elif weighting_strategy == 'traceless_magnitude':
            # Compute traceless Ricci tensor: R_μν - (1/dim) * R * g_μν
            # This requires the metric tensor, which is not available in this class.
            # For simplicity, we'll use the Frobenius norm of the Ricci tensor itself as a proxy
            # for overall magnitude, which often correlates with traceless magnitude.
            # A more accurate implementation would require passing the metric.
            weights = np.linalg.norm(self.tensor, axis=(-2, -1))
        else:
            raise ValueError(f"Invalid weighting_strategy specified: {weighting_strategy}")

        # Normalize weights to sum to 1 (or use softmax for neural network compatibility)
        if np.sum(weights) > 1e-9:
            weights = weights / np.sum(weights)
        else:
            # If all weights are zero, distribute uniformly
            weights = np.ones_like(weights) / weights.size

        return weights

    def generate_narrative_prompt(self, detail_level: str = 'medium') -> str:
        """
        Generates a natural language prompt describing the local spacetime conditions
        and their potential narrative implications, based on the Ricci tensor's properties.
        This can be used to feed information to an LLM for creative generation.

        Args:
            detail_level (str): Level of detail for the narrative prompt:
                                'low': Basic description (e.g., flat, curved).
                                'medium': Includes vacuum/Einstein space, volume deformation (default).
                                'high': Adds eigenvalue/eigenvector interpretations.

        Returns:
            str: A natural language string describing the spacetime conditions.

        Raises:
            ValueError: If the Ricci tensor is not initialized.
        """
        if self.tensor is None or self.tensor.size == 0:
            raise ValueError("Ricci tensor is not initialized. Cannot generate narrative prompt.")

        # For simplicity, we'll describe the properties of the *average* or *dominant* curvature
        # if the tensor is a field. For a single tensor, it describes that tensor.
        is_field = self.tensor.ndim > 2
        if is_field:
            # Take mean values for a general description of the field
            scalar_val = np.mean(self.scalar())
            is_vacuum = self.is_vacuum_solution()
            # For Einstein space and volume deformation, we'd need a metric. Assume flat for now.
            # Or, for a field, we can check if *any* part is vacuum/Einstein.
            # For simplicity, let's just use the mean scalar and vacuum property.
            description_parts = [f"This region of spacetime is characterized by an average Ricci scalar of {scalar_val:.2e}."]
            if is_vacuum:
                description_parts.append("It appears to be a vacuum solution, largely devoid of matter or energy.")
            else:
                description_parts.append("It is not a vacuum solution, indicating the presence of matter or energy.")

            if detail_level == 'medium' or detail_level == 'high':
                # Volume deformation rate (using mean trace as proxy)
                mean_volume_deformation = np.mean(self.volume_deformation_rate(np.eye(self.dimensions))) # Assuming flat metric for proxy
                if mean_volume_deformation > 1e-6:
                    description_parts.append(f"On average, this spacetime is undergoing expansion at a rate proportional to {mean_volume_deformation:.2e}.")
                elif mean_volume_deformation < -1e-6:
                    description_parts.append(f"On average, this spacetime is undergoing contraction at a rate proportional to {mean_volume_deformation:.2e}.")
                else:
                    description_parts.append("On average, there is no significant volume deformation.")

            if detail_level == 'high':
                try:
                    eigenvalues = self.get_ricci_eigenvalues()
                    # Describe the spread or dominance of eigenvalues
                    if is_field:
                        avg_eigenvalues = np.mean(eigenvalues, axis=tuple(range(eigenvalues.ndim - 1)))
                        description_parts.append(f"The average principal curvatures are {avg_eigenvalues}.")
                        # Check for significant differences in eigenvalues (tidal forces)
                        eigenvalue_spread = np.mean(np.max(eigenvalues, axis=-1) - np.min(eigenvalues, axis=-1))
                        if eigenvalue_spread > 0.1:
                            description_parts.append(f"Significant tidal forces are present, with an average eigenvalue spread of {eigenvalue_spread:.2e}.")
                    else:
                        description_parts.append(f"The principal curvatures are {eigenvalues}.")
                        eigenvalue_spread = np.max(eigenvalues) - np.min(eigenvalues)
                        if eigenvalue_spread > 0.1:
                            description_parts.append(f"Significant tidal forces are present, with an eigenvalue spread of {eigenvalue_spread:.2e}.")

                except ValueError: # Eigenvalues might not be computable for all cases
                    pass

        else: # Single tensor
            scalar_val = self.scalar()
            is_vacuum = self.is_vacuum_solution()
            description_parts = [f"This point in spacetime has a Ricci scalar of {scalar_val:.2e}."]
            if is_vacuum:
                description_parts.append("It represents a vacuum solution, largely devoid of matter or energy.")
            else:
                description_parts.append("It is not a vacuum solution, indicating the presence of matter or energy.")

            if detail_level == 'medium' or detail_level == 'high':
                # Volume deformation rate (using trace as proxy)
                volume_deformation = self.volume_deformation_rate(np.eye(self.dimensions)) # Assuming flat metric for proxy
                if volume_deformation > 1e-6:
                    description_parts.append(f"This spacetime is undergoing expansion at a rate proportional to {volume_deformation:.2e}.")
                elif volume_deformation < -1e-6:
                    description_parts.append(f"This spacetime is undergoing contraction at a rate proportional to {volume_deformation:.2e}.")
                else:
                    description_parts.append("There is no significant volume deformation at this point.")

            if detail_level == 'high':
                try:
                    eigenvalues = self.get_ricci_eigenvalues()
                    eigenvectors = self.get_ricci_eigenvectors()
                    description_parts.append(f"The principal curvatures are {eigenvalues}.")
                    eigenvalue_spread = np.max(eigenvalues) - np.min(eigenvalues)
                    if eigenvalue_spread > 0.1:
                        description_parts.append(f"Significant tidal forces are present, with an eigenvalue spread of {eigenvalue_spread:.2e}.")
                    # You could further interpret eigenvectors here, e.g., "The strongest curvature is along the X-axis."
                except ValueError:
                    pass

        return " ".join(description_parts)

    def get_gan_feedback(self, target_ricci_tensor: np.ndarray, feedback_type: str = 'component_wise') -> Dict[str, np.ndarray]:
        """
        Provides feedback for a Generative Adversarial Network (GAN) by comparing the current
        Ricci tensor with a target Ricci tensor.

        Args:
            target_ricci_tensor (np.ndarray): The target Ricci tensor that the GAN is trying to generate.
                                              Must have the same shape as the current Ricci tensor.
            feedback_type (str): The type of feedback to provide:
                                 'component_wise': Returns the difference between tensors (default).
                                 'scalar_difference': Returns the difference in Ricci scalars.
                                 'eigenvalue_difference': Returns the difference in eigenvalues.

        Returns:
            Dict[str, np.ndarray]: A dictionary containing feedback signals.

        Raises:
            ValueError: If the Ricci tensor is not initialized or shapes do not match.
        """
        if self.tensor is None or self.tensor.size == 0:
            raise ValueError("Ricci tensor is not initialized. Cannot provide GAN feedback.")
        if self.tensor.shape != target_ricci_tensor.shape:
            raise ValueError(f"Current Ricci tensor shape {self.tensor.shape} must match target shape {target_ricci_tensor.shape}.")

        feedback = {}

        if feedback_type == 'component_wise':
            feedback['tensor_difference'] = self.tensor - target_ricci_tensor
        elif feedback_type == 'scalar_difference':
            target_ricci = RicciTensor(self.dimensions)
            target_ricci.set(target_ricci_tensor)
            feedback['scalar_difference'] = self.scalar() - target_ricci.scalar()
        elif feedback_type == 'eigenvalue_difference':
            try:
                current_eigenvalues = self.get_ricci_eigenvalues()
                target_ricci = RicciTensor(self.dimensions)
                target_ricci.set(target_ricci_tensor)
                target_eigenvalues = target_ricci.get_ricci_eigenvalues()
                feedback['eigenvalue_difference'] = current_eigenvalues - target_eigenvalues
            except ValueError:
                feedback['eigenvalue_difference'] = np.zeros_like(current_eigenvalues) # Or handle as error
        else:
            raise ValueError(f"Invalid feedback_type specified: {feedback_type}")

        return feedback

    def __repr__(self) -> str:
        """
        Returns a string representation of the RicciTensor object.
        """
        if self.tensor.ndim > 2:
            mean_scalar_val = np.mean(self.scalar())
            try:
                # Attempt to get eigenvalues for a more comprehensive representation
                mean_eigenvalues = np.mean(self.get_ricci_eigenvalues(), axis=tuple(range(self.tensor.ndim - 1)))
                eigen_str = f", mean_eigenvalues={mean_eigenvalues}"
            except ValueError:
                eigen_str = ""
            return (
                f"RicciTensor(dimensions={self.dimensions}, shape={self.tensor.shape}, "
                f"mean_scalar={mean_scalar_val:.3e}, is_vacuum={self.is_vacuum_solution()}{eigen_str})"
            )
        else:
            scalar_val = self.scalar()
            try:
                eigenvalues = self.get_ricci_eigenvalues()
                eigen_str = f", eigenvalues={eigenvalues}"
            except ValueError:
                eigen_str = ""
            return (
                f"RicciTensor(dimensions={self.dimensions}, shape={self.tensor.shape}, "
                f"scalar={scalar_val:.3e}, is_vacuum={self.is_vacuum_solution()}{eigen_str})"
            )

    def to_llm_structured_description(self) -> str:
        """
        Build a compact JSON string describing key Ricci tensor properties for LLM consumption.
        Includes shape, summary stats, scalar field stats, and optional eigen summaries.
        Returns:
            str: JSON string with structured properties.
        """
        import json

        if self.tensor is None or self.tensor.size == 0:
            raise ValueError("Ricci tensor is not initialized. Cannot build structured description.")

        is_field = self.tensor.ndim > 2

        # Core summaries
        tensor_min = float(np.min(self.tensor))
        tensor_max = float(np.max(self.tensor))
        tensor_mean = float(np.mean(self.tensor))
        tensor_std = float(np.std(self.tensor))

        # Scalar (trace) summaries
        scalar_field = self.scalar()
        scalar_min = float(np.min(scalar_field))
        scalar_max = float(np.max(scalar_field))
        scalar_mean = float(np.mean(scalar_field))
        scalar_std = float(np.std(scalar_field))

        # Optional eigen summaries (guarded)
        eigen_summaries: Dict[str, Any] = {}
        try:
            ev = self.get_ricci_eigenvalues()
            if is_field:
                eigen_summaries = {
                    "eigenvalues_mean": np.mean(ev, axis=tuple(range(ev.ndim - 1))).tolist(),
                    "eigenvalues_spread_mean": float(np.mean(np.max(ev, axis=-1) - np.min(ev, axis=-1)))
                }
            else:
                eigen_summaries = {
                    "eigenvalues": ev.flatten().tolist(),
                    "eigenvalues_spread": float(np.max(ev) - np.min(ev))
                }
        except Exception:
            # Eigenvalues not available; omit
            pass

        data: Dict[str, Any] = {
            "type": "RicciTensor",
            "dimensions": int(self.dimensions),
            "tensor_shape": tuple(int(s) for s in self.tensor.shape),
            "is_field": bool(is_field),
            "summary": {
                "min": tensor_min,
                "max": tensor_max,
                "mean": tensor_mean,
                "std": tensor_std,
            },
            "scalar_summary": {
                "min": scalar_min,
                "max": scalar_max,
                "mean": scalar_mean,
                "std": scalar_std,
            },
            "vacuum_like": bool(self.is_vacuum_solution()),
        }

        # Include small samples to keep payload compact
        try:
            # Sample up to first few components
            flat_tensor = self.tensor.reshape(-1, self.tensor.shape[-2], self.tensor.shape[-1])
            sample_count = min(3, flat_tensor.shape[0])
            data["samples"] = {
                "tensor_components_sample": flat_tensor[:sample_count].tolist(),
                "scalar_sample": np.array(scalar_field).reshape(-1)[:min(5, np.prod(scalar_field.shape))].tolist()
            }
        except Exception:
            pass

        if eigen_summaries:
            data["eigen_summaries"] = eigen_summaries

        # Return as JSON string for direct LLM input
        return json.dumps(data, separators=(",", ":"))

    def generate_llm_training_pair(self, detail_level: str = 'high') -> Dict[str, str]:
        """
        Generates a pair of structured Ricci tensor data and a corresponding natural language
        description, suitable for fine-tuning Large Language Models.

        Args:
            detail_level (str): Level of detail for the narrative prompt (passed to generate_narrative_prompt).

        Returns:
            Dict[str, str]: A dictionary containing:
                            'input': A JSON string of the structured Ricci tensor properties.
                            'output': A natural language description of the Ricci tensor.

        Raises:
            ValueError: If the Ricci tensor is not initialized.
        """
        if self.tensor is None or self.tensor.size == 0:
            raise ValueError("Ricci tensor is not initialized. Cannot generate LLM training pair.")

        structured_data = self.to_llm_structured_description()
        narrative_description = self.generate_narrative_prompt(detail_level=detail_level)

        return {
            "input": structured_data,
            "output": narrative_description
        }

    def detect_curvature_anomaly(self, threshold: float = 1e5) -> Tuple[bool, dict]:
        """
        Detects anomalies in the Ricci tensor field, such as regions with extremely high curvature,
        NaNs, or infinities. Returns a tuple (is_anomaly, details).

        Args:
            threshold (float): Absolute value above which curvature is considered anomalous.

        Returns:
            Tuple[bool, dict]: (is_anomaly, details)
                is_anomaly: True if any anomaly is detected.
                details: Dictionary with anomaly statistics.
        """
        if self.tensor is None or self.tensor.size == 0:
            return False, {"reason": "Ricci tensor not initialized."}

        tensor = self.tensor
        anomalies = {}

        # Check for NaNs or infinities
        has_nan = np.isnan(tensor).any()
        has_inf = np.isinf(tensor).any()
        if has_nan or has_inf:
            anomalies['nan'] = has_nan
            anomalies['inf'] = has_inf

        # Check for high curvature (absolute value above threshold)
        max_abs = np.max(np.abs(tensor))
        if max_abs > threshold:
            anomalies['high_curvature'] = True
            anomalies['max_abs'] = float(max_abs)
        else:
            anomalies['high_curvature'] = False
            anomalies['max_abs'] = float(max_abs)

        # Optionally, check for abrupt spatial jumps (if tensor is a field)
        if tensor.ndim > 2:
            # Compute finite differences along each axis and check for large jumps
            diffs = []
            for axis in range(tensor.ndim - 2):
                diff = np.abs(np.diff(tensor, axis=axis))
                diffs.append(diff)
            if diffs:
                max_jump = max(np.max(d) for d in diffs)
                if max_jump > threshold:
                    anomalies['spatial_jump'] = True
                    anomalies['max_jump'] = float(max_jump)
                else:
                    anomalies['spatial_jump'] = False
                    anomalies['max_jump'] = float(max_jump)

        is_anomaly = bool(anomalies.get('nan') or anomalies.get('inf') or anomalies.get('high_curvature') or anomalies.get('spatial_jump'))
        if is_anomaly and get_cosmic_scroll_logger:
            scroll = get_cosmic_scroll_logger()
            if scroll:
                scroll.log_event(
                    "ricci_anomaly",
                    payload=anomalies,
                    component="RicciTensor",
                )
        return is_anomaly, anomalies


    def _get_causal_influence_map(self, event_type: str, metric_tensor: np.ndarray) -> Dict[str, np.ndarray]:
        """
        Generates a map of causal influence based on Ricci tensor properties,
        indicating which curvature features are most relevant to a given event type.
        This is a simplified model for Explainable AI (XAI).

        Args:
            event_type (str): The type of event to analyze (e.g., 'black_hole_formation',
                                'gravitational_wave_emission', 'stable_region').
            metric_tensor (np.ndarray): The metric tensor, required for some calculations.

        Returns:
            Dict[str, np.ndarray]: A dictionary where keys are influence factors
                                   (e.g., 'ricci_scalar_influence', 'tidal_force_influence')
                                   and values are scalar fields representing their influence.

        Raises:
            ValueError: If the Ricci tensor is not initialized.
        """
        if self.tensor is None or self.tensor.size == 0:
            raise ValueError("Ricci tensor is not initialized. Cannot generate causal influence map.")

        influence_map = {}
        spatial_grid_shape = self.tensor.shape[:-2]

        # Influence of Ricci scalar (related to volume changes, presence of matter/energy)
        ricci_scalar_influence = np.abs(self.scalar())
        influence_map['ricci_scalar_influence'] = ricci_scalar_influence

        # Influence of tidal forces (related to traceless Ricci tensor, eigenvalue spread)
        try:
            eigenvalues = self.get_ricci_eigenvalues()
            tidal_force_influence = np.max(eigenvalues, axis=-1) - np.min(eigenvalues, axis=-1)
            influence_map['tidal_force_influence'] = tidal_force_influence
        except ValueError:
            influence_map['tidal_force_influence'] = np.zeros(spatial_grid_shape)

        # Influence of volume deformation rate
        volume_deformation_influence = np.abs(self.volume_deformation_rate(metric_tensor))
        influence_map['volume_deformation_rate_influence'] = volume_deformation_influence

        # Event-specific weighting of influence factors
        if event_type == 'black_hole_formation':
            # High scalar curvature and strong contraction are key indicators
            influence_map['ricci_scalar_influence'] *= 2.0 # Emphasize scalar
            influence_map['volume_deformation_rate_influence'] *= 1.5 # Emphasize contraction
            # Tidal forces also play a role near black holes
            influence_map['tidal_force_influence'] *= 1.0

        elif event_type == 'gravitational_wave_emission':
            # Gravitational waves are related to the traceless part of the Riemann tensor,
            # which is indirectly reflected in tidal forces (eigenvalue spread).
            influence_map['ricci_scalar_influence'] *= 0.5 # Less emphasis on scalar
            influence_map['tidal_force_influence'] *= 2.5 # Strong emphasis on tidal forces
            influence_map['volume_deformation_rate_influence'] *= 0.5

        elif event_type == 'stable_region':
            # Stable regions have low curvature, low deformation, and low tidal forces
            influence_map['ricci_scalar_influence'] = 1.0 - np.clip(ricci_scalar_influence / np.max(ricci_scalar_influence + 1e-9), 0, 1) # Inverse influence
            influence_map['tidal_force_influence'] = 1.0 - np.clip(tidal_force_influence / np.max(tidal_force_influence + 1e-9), 0, 1)
            influence_map['volume_deformation_rate_influence'] = 1.0 - np.clip(volume_deformation_influence / np.max(volume_deformation_influence + 1e-9), 0, 1)

        # Normalize each influence map to sum to 1 for easier interpretation
        for key, value in influence_map.items():
            if np.sum(value) > 1e-9:
                influence_map[key] = value / np.sum(value)
            else:
                influence_map[key] = np.ones_like(value) / value.size # Uniform if all zero

        return influence_map
        has_nan = np.isnan(tensor).any()
        has_inf = np.isinf(tensor).any()
        if has_nan or has_inf:
            anomalies['nan'] = has_nan
            anomalies['inf'] = has_inf

        # Check for high curvature (absolute value above threshold)
        max_abs = np.max(np.abs(tensor))
        if max_abs > threshold:
            anomalies['high_curvature'] = True
            anomalies['max_abs'] = float(max_abs)
        else:
            anomalies['high_curvature'] = False
            anomalies['max_abs'] = float(max_abs)

        # Optionally, check for abrupt spatial jumps (if tensor is a field)
        if tensor.ndim > 2:
            # Compute finite differences along each axis and check for large jumps
            diffs = []
            for axis in range(tensor.ndim - 2):
                diff = np.abs(np.diff(tensor, axis=axis))
                diffs.append(diff)
            if diffs:
                max_jump = max(np.max(d) for d in diffs)
                if max_jump > threshold:
                    anomalies['spatial_jump'] = True
                    anomalies['max_jump'] = float(max_jump)
                else:
                    anomalies['spatial_jump'] = False
                    anomalies['max_jump'] = float(max_jump)

        is_anomaly = bool(anomalies.get('nan') or anomalies.get('inf') or anomalies.get('high_curvature') or anomalies.get('spatial_jump'))
        return is_anomaly, anomalies


    def get_causal_influence_map(self, event_type: str, metric_tensor: np.ndarray) -> Dict[str, np.ndarray]:
        """
        Generates a map of causal influence based on Ricci tensor properties,
        indicating which curvature features are most relevant to a given event type.
        This is a simplified model for Explainable AI (XAI).

        Args:
            event_type (str): The type of event to analyze (e.g., 'black_hole_formation',
                                'gravitational_wave_emission', 'stable_region').
            metric_tensor (np.ndarray): The metric tensor, required for some calculations.

        Returns:
            Dict[str, np.ndarray]: A dictionary where keys are influence factors
                                   (e.g., 'ricci_scalar_influence', 'tidal_force_influence')
                                   and values are scalar fields representing their influence.

        Raises:
            ValueError: If the Ricci tensor is not initialized.
        """
        if self.tensor is None or self.tensor.size == 0:
            raise ValueError("Ricci tensor is not initialized. Cannot generate causal influence map.")

        influence_map = {}
        spatial_grid_shape = self.tensor.shape[:-2]

        # Influence of Ricci scalar (related to volume changes, presence of matter/energy)
        ricci_scalar_influence = np.abs(self.scalar())
        influence_map['ricci_scalar_influence'] = ricci_scalar_influence

        # Influence of tidal forces (related to traceless Ricci tensor, eigenvalue spread)
        try:
            eigenvalues = self.get_ricci_eigenvalues()
            tidal_force_influence = np.max(eigenvalues, axis=-1) - np.min(eigenvalues, axis=-1)
            influence_map['tidal_force_influence'] = tidal_force_influence
        except ValueError:
            influence_map['tidal_force_influence'] = np.zeros(spatial_grid_shape)

        # Influence of volume deformation rate
        volume_deformation_influence = np.abs(self.volume_deformation_rate(metric_tensor))
        influence_map['volume_deformation_rate_influence'] = volume_deformation_influence

        # Event-specific weighting of influence factors
        if event_type == 'black_hole_formation':
            # High scalar curvature and strong contraction are key indicators
            influence_map['ricci_scalar_influence'] *= 2.0 # Emphasize scalar
            influence_map['volume_deformation_rate_influence'] *= 1.5 # Emphasize contraction
            # Tidal forces also play a role near black holes
            influence_map['tidal_force_influence'] *= 1.0

        elif event_type == 'gravitational_wave_emission':
            # Gravitational waves are related to the traceless part of the Riemann tensor,
            # which is indirectly reflected in tidal forces (eigenvalue spread).
            influence_map['ricci_scalar_influence'] *= 0.5 # Less emphasis on scalar
            influence_map['tidal_force_influence'] *= 2.5 # Strong emphasis on tidal forces
            influence_map['volume_deformation_rate_influence'] *= 0.5

        elif event_type == 'stable_region':
            # Stable regions have low curvature, low deformation, and low tidal forces
            influence_map['ricci_scalar_influence'] = 1.0 - np.clip(ricci_scalar_influence / np.max(ricci_scalar_influence + 1e-9), 0, 1) # Inverse influence
            influence_map['tidal_force_influence'] = 1.0 - np.clip(tidal_force_influence / np.max(tidal_force_influence + 1e-9), 0, 1)
            influence_map['volume_deformation_rate_influence'] = 1.0 - np.clip(volume_deformation_influence / np.max(volume_deformation_influence + 1e-9), 0, 1)

        # Normalize each influence map to sum to 1 for easier interpretation
        for key, value in influence_map.items():
            if np.sum(value) > 1e-9:
                influence_map[key] = value / np.sum(value)
            else:
                influence_map[key] = np.ones_like(value) / value.size # Uniform if all zero

        return influence_map
