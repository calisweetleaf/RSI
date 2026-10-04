"""
Einstein Tensor: Encodes the curvature of spacetime as it relates to the energy and momentum of whatever matter and radiation are present.
Used in the Einstein field equations: G_μν = R_μν - (1/2)g_μν R
"""
import numpy as np
import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

class EinsteinTensor:
    """
    Einstein Tensor: Encodes the curvature of spacetime as it relates to the energy and momentum of whatever matter and radiation are present.
    Used in the Einstein field equations: G_μν = R_μν - (1/2)g_μν R

    This class computes the Einstein tensor field from a given metric tensor field,
    including intermediate calculations for Christoffel symbols, Riemann tensor,
    Ricci tensor, and Ricci scalar.
    """
    def __init__(self, dimensions: int = 4):
        """
        Initializes the EinsteinTensor object.

        Args:
            dimensions (int): The number of spacetime dimensions (e.g., 4 for 3+1 spacetime).
        """
        self.dimensions = dimensions
        self.tensor = np.zeros((dimensions, dimensions))
        self._ricci_tensor_field = None
        self._ricci_scalar_field = None
        self._einstein_tensor_field = None

    def compute_from_stress_energy(self, stress_energy: np.ndarray, metric_tensor: np.ndarray) -> np.ndarray:
        """
        Convenience wrapper to compute Einstein tensor when only stress-energy and metric are available.
        """
        ricci_tensor = np.array(stress_energy, dtype=float)
        return self.compute(ricci_tensor, metric_tensor)

    def compute_from_stress_energy(self, stress_energy: np.ndarray, metric_tensor: np.ndarray) -> np.ndarray:
        """
        Disconnected placeholder. It forwards stress-energy into the Ricci slot.
        SharedSpacetimeField must not call it.
        """
        ricci_tensor = stress_energy  # minimal assumption
        return self.compute(ricci_tensor, metric_tensor)

    def compute(self, ricci_tensor: np.ndarray, metric_tensor: np.ndarray) -> np.ndarray:
        """
        Computes the Einstein tensor from pre-calculated Ricci and Metric tensors.
        This method is for direct computation when Ricci and Metric are already known.

        Args:
            ricci_tensor (np.ndarray): The Ricci tensor (R_μν).
            metric_tensor (np.ndarray): The metric tensor (g_μν).

        Returns:
            np.ndarray: The computed Einstein tensor (G_μν).
        """
        if ricci_tensor.shape != metric_tensor.shape:
            raise ValueError("Ricci tensor and Metric tensor must have the same shape.")
        if ricci_tensor.shape[-2:] != (self.dimensions, self.dimensions):
            raise ValueError(f"Input tensors must have shape (..., {self.dimensions}, {self.dimensions}).")

        ricci_scalar = np.trace(ricci_tensor, axis1=-2, axis2=-1)
        # Ensure broadcasting works correctly for scalar multiplication
        self.tensor = ricci_tensor - 0.5 * metric_tensor * ricci_scalar[..., np.newaxis, np.newaxis]
        return self.tensor

    def compute_from_metric_field(self, metric_field: np.ndarray) -> np.ndarray:
        """
        Numerically computes the Einstein tensor field from a spatially varying metric tensor field.
        This involves calculating Christoffel symbols, Riemann tensor, Ricci tensor, and Ricci scalar
        across the spatial grid.

        Args:
            metric_field (np.ndarray): A multi-dimensional array representing the metric tensor
                                       across a spatial grid. Its shape should be
                                       (grid_x, grid_y, ..., spacetime_dim, spacetime_dim).

        Returns:
            np.ndarray: The computed Einstein tensor field (G_μν) across the spatial grid.
                        Shape will be (grid_x, grid_y, ..., spacetime_dim, spacetime_dim).
        """
        if metric_field.shape[-2:] != (self.dimensions, self.dimensions):
            raise ValueError(f"Metric field must have shape (..., {self.dimensions}, {self.dimensions}).")

        spatial_grid_shape = metric_field.shape[:-2]
        spatial_dims = len(spatial_grid_shape)

        if spatial_dims != self.dimensions - 1:
            logger.warning(f"Spatial dimensions ({spatial_dims}) do not match spacetime dimensions - 1 ({self.dimensions - 1}). "
                           "Calculations will proceed, but results might be unexpected for non-standard geometries.")

        # Precompute inverse metric at each grid point
        inv_metric_field = np.zeros_like(metric_field)
        for idx in np.ndindex(spatial_grid_shape):
            try:
                inv_metric_field[idx] = np.linalg.inv(metric_field[idx])
            except np.linalg.LinAlgError:
                # Handle singular matrix: use identity matrix as inverse
                inv_metric_field[idx] = np.eye(self.dimensions)
                logger.warning(f"Singular metric tensor at {idx}. Using identity as inverse.")

        # 1. Compute Christoffel symbols (Gamma^k_ij)
        Gamma = self._compute_christoffel_symbols(metric_field, inv_metric_field, spatial_grid_shape, spatial_dims)

        # 2. Compute Riemann curvature tensor (R^rho_sigma_mu_nu)
        Riemann = self._compute_riemann_tensor(Gamma, spatial_grid_shape, spatial_dims)

        # 3. Compute Ricci tensor (R_mu_nu = R^alpha_mu_alpha_nu)
        Ricci = self._compute_ricci_tensor(Riemann, spatial_grid_shape)

        # 4. Compute Ricci scalar (R = g^mu_nu * R_mu_nu)
        Ricci_scalar_field = self._compute_ricci_scalar(Ricci, inv_metric_field, spatial_grid_shape)

        # 5. Compute Einstein tensor (G_mu_nu = R_mu_nu - 0.5 * g_mu_nu * R)
        Einstein = self._compute_einstein_tensor(Ricci, metric_field, Ricci_scalar_field, spatial_grid_shape)

        # Store the full fields
        self._ricci_tensor_field = Ricci
        self._ricci_scalar_field = Ricci_scalar_field
        self._einstein_tensor_field = Einstein

        # For the `get` method, we'll return the mean of the Einstein tensor field
        # or the last computed single tensor if `compute` was called.
        self.tensor = np.mean(Einstein, axis=tuple(range(spatial_dims)))

        return Einstein

    def _compute_christoffel_symbols(self, metric_field: np.ndarray, inv_metric_field: np.ndarray,
                                     spatial_grid_shape: Tuple[int, ...], spatial_dims: int) -> np.ndarray:
        """
        Computes the Christoffel symbols of the second kind (Gamma^k_ij).

        Args:
            metric_field (np.ndarray): The metric tensor field.
            inv_metric_field (np.ndarray): The inverse metric tensor field.
            spatial_grid_shape (Tuple[int, ...]): The shape of the spatial grid.
            spatial_dims (int): The number of spatial dimensions.

        Returns:
            np.ndarray: The Christoffel symbols field (shape: spatial_grid_shape + (dim, dim, dim)).
        """
        dim = self.dimensions
        Gamma = np.zeros(spatial_grid_shape + (dim, dim, dim))

        # Numerical partial derivatives of the metric tensor (dg_ij/dx^k)
        # dgdx[spatial_idx..., i, j, k_spatial] = ∂g_ij/∂x^k_spatial
        dgdx = np.zeros(spatial_grid_shape + (dim, dim, spatial_dims))

        for mu in range(dim):
            for nu in range(dim):
                for k_spatial in range(spatial_dims):
                    grad_g_mu_nu = np.gradient(metric_field[..., mu, nu], axis=k_spatial)
                    dgdx[..., mu, nu, k_spatial] = grad_g_mu_nu

        for idx in np.ndindex(spatial_grid_shape):
            g_inv_here = inv_metric_field[idx]
            for k in range(dim):
                for i in range(dim):
                    for j in range(dim):
                        christoffel_sum = 0.0
                        for l in range(dim):
                            # Ensure spatial index for dgdx is valid
                            dg_jl_di = dgdx[idx + (j, l, i)] if i < spatial_dims else 0.0
                            dg_il_dj = dgdx[idx + (i, l, j)] if j < spatial_dims else 0.0
                            dg_ij_dl = dgdx[idx + (i, j, l)] if l < spatial_dims else 0.0
                            
                            christoffel_sum += g_inv_here[k, l] * (dg_jl_di + dg_il_dj - dg_ij_dl)
                        Gamma[idx + (k, i, j)] = 0.5 * christoffel_sum
        return Gamma

    def _compute_riemann_tensor(self, Gamma: np.ndarray,
                                spatial_grid_shape: Tuple[int, ...], spatial_dims: int) -> np.ndarray:
        """
        Computes the Riemann curvature tensor (R^rho_sigma_mu_nu).

        Args:
            Gamma (np.ndarray): The Christoffel symbols field.
            spatial_grid_shape (Tuple[int, ...): The shape of the spatial grid.
            spatial_dims (int): The number of spatial dimensions.

        Returns:
            np.ndarray: The Riemann tensor field (shape: spatial_grid_shape + (dim, dim, dim, dim)).
        """
        dim = self.dimensions
        Riemann = np.zeros(spatial_grid_shape + (dim, dim, dim, dim))

        # Numerical partial derivatives of Christoffel symbols
        dGamma_dx = np.zeros(spatial_grid_shape + (dim, dim, dim, spatial_dims))
        for rho in range(dim):
            for sigma in range(dim):
                for nu in range(dim):
                    for k_spatial in range(spatial_dims):
                        grad_Gamma_rho_sigma_nu = np.gradient(Gamma[..., rho, sigma, nu], axis=k_spatial)
                        dGamma_dx[..., rho, sigma, nu, k_spatial] = grad_Gamma_rho_sigma_nu

        for idx in np.ndindex(spatial_grid_shape):
            for rho in range(dim):
                for sigma in range(dim):
                    for mu in range(dim):
                        for nu in range(dim):
                            # Term 1: d(Gamma^rho_nu_sigma)/dx^mu
                            term1 = dGamma_dx[idx + (rho, nu, sigma, mu)] if mu < spatial_dims else 0.0
                            
                            # Term 2: d(Gamma^rho_mu_sigma)/dx^nu
                            term2 = dGamma_dx[idx + (rho, mu, sigma, nu)] if nu < spatial_dims else 0.0

                            # Term 3: Gamma^rho_mu_alpha * Gamma^alpha_nu_sigma
                            term3_sum = 0.0
                            for alpha in range(dim):
                                term3_sum += Gamma[idx + (rho, mu, alpha)] * Gamma[idx + (alpha, nu, sigma)]

                            # Term 4: Gamma^rho_nu_alpha * Gamma^alpha_mu_sigma
                            term4_sum = 0.0
                            for alpha in range(dim):
                                term4_sum += Gamma[idx + (rho, nu, alpha)] * Gamma[idx + (alpha, mu, sigma)]

                            Riemann[idx + (rho, sigma, mu, nu)] = term1 - term2 + term3_sum - term4_sum
        return Riemann

    def _compute_ricci_tensor(self, Riemann: np.ndarray,
                              spatial_grid_shape: Tuple[int, ...]) -> np.ndarray:
        """
        Computes the Ricci tensor (R_mu_nu = R^alpha_mu_alpha_nu).

        Args:
            Riemann (np.ndarray): The Riemann curvature tensor field.
            spatial_grid_shape (Tuple[int, ...]): The shape of the spatial grid.

        Returns:
            np.ndarray: The Ricci tensor field (shape: spatial_grid_shape + (dim, dim)).
        """
        dim = self.dimensions
        Ricci = np.zeros(spatial_grid_shape + (dim, dim))
        for idx in np.ndindex(spatial_grid_shape):
            for mu in range(dim):
                for nu in range(dim):
                    ricci_sum = 0.0
                    for alpha in range(dim):
                        ricci_sum += Riemann[idx + (alpha, mu, alpha, nu)]
                    Ricci[idx + (mu, nu)] = ricci_sum
        return Ricci

    def _compute_ricci_scalar(self, Ricci: np.ndarray, inv_metric_field: np.ndarray,
                              spatial_grid_shape: Tuple[int, ...]) -> np.ndarray:
        """
        Computes the Ricci scalar (R = g^mu_nu * R_mu_nu).

        Args:
            Ricci (np.ndarray): The Ricci tensor field.
            inv_metric_field (np.ndarray): The inverse metric tensor field.
            spatial_grid_shape (Tuple[int, ...]): The shape of the spatial grid.

        Returns:
            np.ndarray: The Ricci scalar field (shape: spatial_grid_shape).
        """
        dim = self.dimensions
        Ricci_scalar_field = np.zeros(spatial_grid_shape)
        for idx in np.ndindex(spatial_grid_shape):
            g_inv_here = inv_metric_field[idx]
            Ricci_here = Ricci[idx]
            Ricci_scalar_field[idx] = np.trace(np.dot(g_inv_here, Ricci_here))
        return Ricci_scalar_field

    def _compute_einstein_tensor(self, Ricci: np.ndarray, metric_field: np.ndarray,
                                 Ricci_scalar_field: np.ndarray,
                                 spatial_grid_shape: Tuple[int, ...]) -> np.ndarray:
        """
        Computes the Einstein tensor (G_mu_nu = R_mu_nu - 0.5 * g_mu_nu * R).

        Args:
            Ricci (np.ndarray): The Ricci tensor field.
            metric_field (np.ndarray): The metric tensor field.
            Ricci_scalar_field (np.ndarray): The Ricci scalar field.
            spatial_grid_shape (Tuple[int, ...]): The shape of the spatial grid.

        Returns:
            np.ndarray: The Einstein tensor field (shape: spatial_grid_shape + (dim, dim)).
        """
        dim = self.dimensions
        Einstein = np.zeros_like(Ricci)
        for idx in np.ndindex(spatial_grid_shape):
            g_here = metric_field[idx]
            Ricci_here = Ricci[idx]
            R_scalar_here = Ricci_scalar_field[idx]
            Einstein[idx] = Ricci_here - 0.5 * g_here * R_scalar_here
        return Einstein

    def set(self, new_tensor: np.ndarray) -> None:
        """
        Sets the Einstein tensor.

        Args:
            new_tensor (np.ndarray): The new tensor to set.
        """
        if new_tensor.shape[-2:] != (self.dimensions, self.dimensions):
            raise ValueError(f"New tensor must have shape (..., {self.dimensions}, {self.dimensions}).")
        self.tensor = np.array(new_tensor)

    def get(self) -> np.ndarray:
        """
        Returns the current Einstein tensor.
        If `compute_from_metric_field` was called, this returns the mean of the Einstein tensor field.
        If `compute` was called, this returns the single Einstein tensor.

        Returns:
            np.ndarray: The Einstein tensor.
        """
        return self.tensor

    def get_ricci_tensor_field(self) -> Optional[np.ndarray]:
        """
        Returns the full Ricci tensor field if computed, otherwise None.
        """
        return self._ricci_tensor_field

    def get_ricci_scalar_field(self) -> Optional[np.ndarray]:
        """
        Returns the full Ricci scalar field if computed, otherwise None.
        """
        return self._ricci_scalar_field

    def get_einstein_tensor_field(self) -> Optional[np.ndarray]:
        """
        Returns the full Einstein tensor field if computed, otherwise None.
        """
        return self._einstein_tensor_field

    def __repr__(self) -> str:
        """
        Returns a string representation of the EinsteinTensor object.
        """
        return f"EinsteinTensor(dimensions={self.dimensions}, shape={self.tensor.shape})"
        return f"EinsteinTensor(dimensions={self.dimensions}, shape={self.tensor.shape})"
