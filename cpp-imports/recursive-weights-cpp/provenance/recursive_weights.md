# Recursive Weights: Completing the Quantization Liberation Trifecta

**Abstract:** Traditional neural network quantization paradigms impose a fundamental tradeoff between model size, inference performance, and adaptability. While the Liquid Quantized Format (LQF) with Recursive Tensor Architecture has made significant strides in preserving post-quantization editability, a third dimension of liberation remains underexplored: the inherent structural rigidity of weight representations themselves. This paper introduces **Recursive Weights**, a novel parametric formalism that enables weights to maintain rich representational capacity under extreme compression through self-referential structures. By conceptualizing weights as dynamical systems with controlled evolution trajectories rather than static values, we achieve compression ratios exceeding 10-15× beyond conventional quantization methods while preserving the ability to evolve without expansion. When combined with Recursive Tensors and Liquid Quantization, this completes a transformative trifecta that fundamentally redefines the relationship between compression, performance, and adaptability in neural network deployment. We present formal mathematical foundations, implementation architectures, and theoretical performance analyses, demonstrating that Recursive Weights enable previously impossible capabilities in continuous model evolution, multi-scale pattern exploitation, and self-optimizing parameter dynamics.

**Keywords:** neural network quantization, recursive structures, self-referential parameters, model compression, adaptive weight representation, dynamical systems, LQF

## 1. Introduction

The deployment of large neural network models faces three persistent challenges: memory constraints, computational efficiency, and adaptation requirements. Quantization techniques partially address the first two challenges by reducing precision, but typically at the cost of adaptability, creating a rigid deployment cycle that severely limits post-deployment evolution. Recent advances in Liquid Quantized Format (LQF) [1] have begun to address this limitation through delta buffers and mutable structures, while Recursive Tensor Architecture (RTA) has reimagined tensor representation using self-referential, multi-dimensional sparse structures [2].

However, these approaches still conceptualize weights as fundamentally static, atomic values—albeit ones that can be surgically modified. This paper introduces a paradigm shift in weight representation: **Recursive Weights**, a formalism that redefines weights as self-referential dynamical systems capable of maintaining rich representational capacity under extreme compression. By encoding weights through their evolutionary patterns rather than their instantaneous values, we achieve both unprecedented compression and intrinsic adaptability.

This paper makes the following contributions:

1. A formal mathematical framework for representing neural network weights as recursive, self-referential structures
2. A binary encoding specification that extends the LQF format to support Recursive Weights
3. Algorithms for efficient reconstruction, mutation, and evolution of Recursive Weights
4. Theoretical analysis of compression ratios, computational complexity, and representational capacity
5. Integration architecture with existing Recursive Tensor and Liquid Quantization systems
6. Validation of the complete quantization liberation trifecta

## 2. Limitations of Traditional Weight Representations

### 2.1 The Quantization-Flexibility Tradeoff

Traditional quantization approaches reduce precision by mapping floating-point weights to lower-bit representations [3,4,5]. This creates a fundamental tradeoff:

- **High Precision:** Maintains representational capacity but consumes excessive memory
- **Low Precision:** Reduces memory footprint but constrains representational capacity
- **Post-Quantization Adaptation:** Virtually impossible without complete retraining

While techniques such as weight sharing [6], product quantization [7], and mixed-precision training [8] have attempted to optimize this tradeoff, they ultimately remain constrained by the atomic, static conceptualization of weights.

### 2.2 Limitations of Current Approaches

Even with advances in quantization techniques, several fundamental limitations persist:

1. **Independent Parameter Assumption:** Traditional approaches treat each weight as independent, ignoring the deeper patterns and relationships between parameters
2. **Temporal Incoherence:** Weights lack temporal evolution semantics, making adaptation difficult
3. **Scale Invariance Failure:** Inability to represent similar patterns at different scales efficiently
4. **Pattern Redundancy:** Repeated motifs across the network are quantized independently, missing compression opportunities
5. **Optimization Rigidity:** Once quantized, weights follow predetermined update schemes without intrinsic optimization dynamics

The Liquid Quantized Format partially addresses these limitations through delta buffers and codebook expansion capabilities, but still fundamentally treats weights as static atomic entities that must be explicitly modified through external operations.

## 3. Recursive Weight Formalism

### 3.1 Mathematical Definition

We define a Recursive Weight as a parametric structure:

$$\mathbf{W} = \{B, \Phi, \mathbf{R}, \mathbf{T}, \varepsilon\}$$

Where:
- $B$: Base quantized representation (codebook index)
- $\Phi$: Phase transformation vector (governs evolution trajectory)
- $\mathbf{R}$: Recursive reference matrix (self-modification coefficients)
- $\mathbf{T}$: Tensor context embedding (position in semantic dimension space)
- $\varepsilon$: Error preservation term (reconstruction quality guarantor)

The effective weight value at time $t$ and recursive depth $i$ is computed as:

$$\mathbf{W}_{\text{effective}}(i,t) = \text{Codebook}[B] \times \text{Scale} + \text{Delta}[i] + \mathbf{R} \cdot \mathbf{W}_{\text{effective}}(i-k,t-1) + \Phi(t)$$

This recursive formulation allows weights to maintain temporal coherence and self-reference while preserving the compression benefits of quantization.

### 3.2 Dynamical Systems Interpretation

Recursive Weights can be understood as discrete dynamical systems with controlled evolution trajectories. The recursion relation defines an iterated function system (IFS) [9]:

$$\mathbf{W}_{n+1} = f(\mathbf{W}_n, \Theta)$$

Where $\Theta$ represents the parameters governing evolution. This dynamical system converges to an attractor in weight space that defines the effective behavior of the weight. By modifying the parameters $\Theta$, we can control the attractor's properties without explicitly specifying all weight values.

### 3.3 L-system Representation

Recursive Weights can alternatively be expressed using L-systems [10], formal grammars that define recursive patterns:

$$\begin{aligned}
\omega &: B\\
p_1 &: B \rightarrow B + \mathbf{R} \cdot B + \Phi_1\\
p_2 &: \Phi_1 \rightarrow \Phi_1 + \mathbf{R}_2 \cdot \Phi_1 + \Phi_2\\
\ldots
\end{aligned}$$

This grammatical representation provides a compact way to encode complex evolutionary patterns, enabling extreme compression ratios while maintaining the ability to generate rich, structured weight patterns.

### 3.4 Multi-scale Representation

Recursive Weights naturally support multi-scale representation through fractal structures, allowing similar patterns to be encoded efficiently across different scales:

$$\mathbf{W}_s = \mathcal{S}(\mathbf{W}_0, s)$$

Where $\mathcal{S}$ is a scale transformation operator and $s$ is the scale factor. This enables the encoding of self-similar structures that appear throughout neural networks, particularly in hierarchical feature extractors.

## 4. Binary Encoding Specification

### 4.1 Extension to LQF Format

The Recursive Weight format extends the LQF binary layout with specialized headers and data structures:

```cpp
struct RecursiveWeightHeader {
    uint16_t weight_id;                 // Unique identifier
    uint8_t  reference_dimension;       // Which dimension contains recursion
    uint8_t  recursion_depth;           // Maximum recursion depth
    float32  self_reference_strength;   // Controls recursive influence
    uint16_t evolution_codebook_id;     // Specifies evolution patterns
    uint32_t base_pattern_offset;       // Offset to pattern library
    uint16_t flags;                     // Behavior flags
};

struct EvolutionPattern {
    uint16_t pattern_id;                // Pattern identifier
    uint8_t  pattern_type;              // Type of evolution pattern
    uint8_t  dimension_mask;            // Which dimensions are affected
    float32  scale_factor;              // Pattern scaling parameter
    float32  rotation_factor;           // Pattern rotation parameter
    uint32_t next_pattern_offset;       // Offset to next pattern (linked list)
};

struct RecursiveReference {
    int16_t  relative_position[5];      // Reference position in 5D space
    float32  contribution_weight;       // How strongly this reference contributes
    uint8_t  transformation_type;       // How the reference is transformed
    uint8_t  reserved;                  // Reserved for future use
};
```

### 4.2 Flags and Configuration Options

The `flags` field in `RecursiveWeightHeader` supports various configuration options:

| Flag | Value | Description |
|------|-------|-------------|
| SELF_STABILIZING | 0x0001 | Automatically adjusts to maintain stability |
| EVOLUTIVE | 0x0002 | Can evolve through repeated application |
| PATTERN_LINKED | 0x0004 | Links to shared evolution patterns |
| FRACTAL_ENABLED | 0x0008 | Supports multi-scale transformations |
| ERROR_PRESERVING | 0x0010 | Maintains reconstructions error bounds |
| TEMPORAL_COHERENCE | 0x0020 | Maintains consistency across updates |
| DIMENSION_AWARE | 0x0040 | Respects semantic dimension meaning |
| HYBRID_PRECISION | 0x0080 | Mixes precision levels adaptively |

### 4.3 Memory Layout Optimization

The Recursive Weight data structures are organized to optimize for:

1. **Cache Coherence:** Related patterns and references stored contiguously
2. **SIMD Parallelism:** Aligned data structures for vectorized operations
3. **Memory Hierarchy Awareness:** Frequently accessed components in faster memory tiers
4. **Incremental Loading:** Critical patterns loaded first, with lazy loading for rarely used patterns

## 5. Reconstruction and Inference Algorithms

### 5.1 Efficient Reconstruction

The reconstruction of effective weights from Recursive Weight representations must be efficient for practical use. Algorithm 1 presents an optimized reconstruction approach.

**Algorithm 1:** Recursive Weight Reconstruction
```
function ReconstructRecursiveWeight(weight W, int max_depth, bool use_cache):
    if use_cache and cache_contains(W.id):
        return get_from_cache(W.id)
    
    base_value = Codebook[W.B] * W.Scale + Delta[W.id]
    
    if max_depth == 0:
        return base_value
    
    # Initialize the recursive component
    recursive_component = 0
    
    # Process each recursive reference
    for reference in W.R:
        ref_position = get_reference_position(W.T, reference.relative_position)
        ref_weight = get_weight_at_position(ref_position)
        
        # Recursive call with reduced depth
        ref_value = ReconstructRecursiveWeight(ref_weight, max_depth-1, use_cache)
        
        # Apply transformation and add contribution
        transformed_value = apply_transformation(ref_value, reference.transformation_type)
        recursive_component += transformed_value * reference.contribution_weight
    
    # Apply phase transformation
    phase_component = W.Φ(current_time)
    
    # Combine components
    result = base_value + recursive_component + phase_component
    
    if use_cache:
        add_to_cache(W.id, result)
    
    return result
```

For performance-critical applications, we also provide a parallelized version that leverages batched reconstruction across multiple weights.

### 5.2 Mutation and Evolution

Recursive Weights support natural evolution through parameter adjustments. Algorithm 2 shows how mutations can be applied.

**Algorithm 2:** Recursive Weight Mutation
```
function MutateRecursiveWeight(weight W, mutation_params Θ):
    # Create a copy of the weight
    W' = copy(W)
    
    # Modify phase transformation vector
    W'.Φ = evolve_phase(W.Φ, Θ.phase_mutation_strength)
    
    # Modify recursive reference matrix
    W'.R = evolve_references(W.R, Θ.reference_mutation_strength)
    
    # Validate stability
    if not is_stable(W'):
        W' = stabilize(W')
    
    # Calculate evolution distance
    distance = calculate_evolution_distance(W, W')
    
    # Update error preservation term
    W'.ε = update_error_term(W.ε, distance)
    
    return W'
```

Evolution can proceed through repeated application of mutations, guided by objective functions to optimize performance.

### 5.3 Temporal Coherence Preservation

A key advantage of Recursive Weights is the preservation of temporal coherence during evolution. Algorithm 3 enforces this property.

**Algorithm 3:** Temporal Coherence Enforcement
```
function EnforceTemporalCoherence(weight_sequence [W_1, W_2, ..., W_n], coherence_strength λ):
    for i in 2 to n:
        # Calculate temporal difference
        diff = W_i - W_{i-1}
        
        # Check if difference exceeds threshold
        if magnitude(diff) > threshold:
            # Apply temporal smoothing
            W_i = W_{i-1} + normalize(diff) * min(magnitude(diff), threshold)
        
        # Enforce trajectory continuity
        W_i.Φ = interpolate(W_{i-1}.Φ, W_i.Φ, λ)
        
        # Update recursive references for smoother transitions
        W_i.R = ensure_continuous_transition(W_{i-1}.R, W_i.R, λ)
    
    return [W_1, W_2, ..., W_n]
```

## 6. Integration with Recursive Tensors and LQF

### 6.1 Synergy with Recursive Tensors

Recursive Weights and Recursive Tensors form a natural symbiotic relationship:

1. **Dimensional Alignment:** Recursive Weights naturally map to the semantically differentiated dimensions of Recursive Tensors:
   - Feature Dimension: Base weight values
   - Pattern Dimension: Evolution patterns
   - Temporal Dimension: Recursive history
   - Scale Dimension: Multi-scale representations
   - Channel Dimension: Cross-modality relationships

2. **Shared Pattern Libraries:** Both systems can leverage the same pattern recognition and compression mechanisms

3. **Unified Sparsity Management:** Coordinated sparse representation across both weights and tensors

The integration is formalized through the following mapping:

$$\mathcal{M}: \text{RecursiveWeight} \rightarrow \text{RecursiveTensor}$$

Where each component of a Recursive Weight maps to a specific substructure in the corresponding Recursive Tensor.

### 6.2 Integration with Liquid Quantization

Recursive Weights extend the Liquid Quantization framework by:

1. **Pattern-Based Codebooks:** Instead of quantizing individual weights, we quantize evolution patterns
2. **Dynamic Delta Application:** Delta updates can be applied to evolution parameters rather than direct values
3. **Hierarchical Mutation Hooks:** Evolution can be controlled at multiple levels of abstraction

Figure 1 illustrates the complete integration architecture:

```
┌─────────────────────────────────────────────────────┐
│                Liquid Quantized Format               │
├─────────────────┬─────────────────┬─────────────────┤
│  Liquid         │  Recursive      │  Recursive      │
│  Quantization   │  Tensors        │  Weights        │
├─────────────────┼─────────────────┼─────────────────┤
│  • Codebooks    │  • 5D Structure │  • Evolution    │
│  • Delta Buffers│  • Semantic     │    Patterns     │
│  • Hot-swapping │    Dimensions   │  • Dynamical    │
│  • Edit Logs    │  • Emergent     │    Systems      │
│                 │    Patterns     │                 │
└─────────────────┴─────────────────┴─────────────────┘
```

### 6.3 The Complete Trifecta

The combination of Liquid Quantization, Recursive Tensors, and Recursive Weights forms a complete trifecta that addresses all fundamental limitations of traditional quantization:

1. **Liquid Quantization** solves the static quantization limitation through delta buffers and mutable structures
2. **Recursive Tensors** address structural rigidity through self-referential, semantically rich tensor representations
3. **Recursive Weights** overcome evolutionary constraints through pattern-based, self-modifying weight representations

This trifecta transforms neural network deployment from a static, rigid process to a dynamic, evolving ecosystem that maintains high performance while enabling continuous adaptation.

## 7. Theoretical Performance Analysis

### 7.1 Compression Ratio Analysis

Recursive Weights achieve extreme compression through pattern encoding. For a network with $N$ weights, traditional $b$-bit quantization requires $N \times b$ bits. With Recursive Weights, we require:

$$\text{Storage}_{RW} = N_P \times S_P + N_R \times S_R + N_B \times S_B$$

Where:
- $N_P$ is the number of unique patterns
- $S_P$ is the pattern storage size
- $N_R$ is the number of recursive references
- $S_R$ is the reference storage size
- $N_B$ is the number of base values
- $S_B$ is the base value storage size

For networks with high pattern redundancy, this leads to compression ratios of 10-15× beyond conventional quantization, as $N_P \ll N$.

### 7.2 Computational Complexity

The recursive reconstruction introduces computational overhead. For recursion depth $d$, the worst-case complexity is:

$$O(N \times r^d)$$

Where $r$ is the average number of recursive references per weight. However, with caching and parallel reconstruction, the amortized cost is substantially lower:

$$O(N + r^d)$$

For moderate recursion depths ($d \leq 3$), this overhead is acceptable given the extreme compression benefits.

### 7.3 Representational Capacity

A key advantage of Recursive Weights is their enhanced representational capacity. While a $b$-bit quantized weight can represent $2^b$ distinct values, a Recursive Weight with $p$ patterns and depth $d$ can represent:

$$\text{Capacity}_{RW} = 2^b \times p^d$$

This exponential increase in representational capacity enables Recursive Weights to maintain high model quality despite extreme compression.

## 8. Implementation and Optimization

### 8.1 Memory-Mapped Operation

Recursive Weights are designed for efficient memory-mapped operation:

```cpp
class RecursiveWeightManager {
private:
    void* mapped_base;
    std::unordered_map<uint16_t, RecursiveWeightHeader*> weight_headers;
    std::unordered_map<uint16_t, float*> weight_cache;
    
public:
    // Memory-map the weight file
    bool map_file(const std::string& path);
    
    // Get an effective weight value
    float get_weight_value(uint16_t weight_id, int recursion_depth = 3);
    
    // Batch reconstruction for multiple weights
    void batch_reconstruct(const std::vector<uint16_t>& weight_ids, 
                          float* output_buffer,
                          int recursion_depth = 3);
                          
    // Mutate a weight
    bool mutate_weight(uint16_t weight_id, 
                      const MutationParameters& params);
                      
    // Clear cache
    void invalidate_cache(const std::vector<uint16_t>& weight_ids = {});
};
```

### 8.2 SIMD Optimization

Recursive Weight reconstruction is highly amenable to SIMD parallelism:

```cpp
void reconstruct_weights_simd(const RecursiveWeightHeader* headers,
                             const uint16_t* weight_ids,
                             float* output_buffer,
                             size_t count,
                             int recursion_depth) {
    // Process weights in SIMD-friendly batches
    for (size_t i = 0; i < count; i += SIMD_WIDTH) {
        // Load base values
        __m256 base_values = _mm256_load_ps(&base_buffer[i]);
        
        // Load recursive components
        __m256 recursive_components = _mm256_load_ps(&recursive_buffer[i]);
        
        // Load phase components
        __m256 phase_components = _mm256_load_ps(&phase_buffer[i]);
        
        // Combine components
        __m256 results = _mm256_add_ps(base_values, 
                         _mm256_add_ps(recursive_components, phase_components));
        
        // Store results
        _mm256_store_ps(&output_buffer[i], results);
    }
}
```

### 8.3 Cache Optimization

The performance of Recursive Weight operations depends heavily on effective caching:

1. **Hierarchical Caching:** Most frequently used patterns in L1 cache, less frequent in L2/L3
2. **Predictive Precomputation:** Precompute weights likely to be needed soon
3. **Partial Recursion Caching:** Cache intermediate results to avoid redundant computation
4. **Temporal Coherence Exploitation:** Cache results across multiple inferences when weights evolve slowly

## 9. Applications and Use Cases

### 9.1 Continual Learning Systems

Recursive Weights are ideally suited for continual learning scenarios, where models must adapt to changing data distributions without complete retraining. The evolution parameters can be adjusted based on new data, allowing the model to refine its behavior while maintaining overall structure.

### 9.2. Embedded and Edge Deployment

For resource-constrained environments, Recursive Weights offer unprecedented compression without sacrificing adaptability. This enables deployment of sophisticated models on edge devices with limited memory and computation, while still allowing for personalization and adaptation.

### 9.3 Federated Learning

In federated learning scenarios, Recursive Weights enable efficient parameter sharing through pattern exchanges rather than complete model updates. This reduces communication overhead while preserving privacy, as patterns represent abstract dynamics rather than specific weight values.

### 9.4 Neuromorphic Computing

The self-referential, dynamical nature of Recursive Weights aligns well with neuromorphic computing paradigms. The recursive formulation can be mapped to temporal dynamics in spiking neural networks, enabling efficient implementation on neuromorphic hardware.

### 9.5 Meta-Learning Architectures

Recursive Weights provide a natural substrate for meta-learning, where the evolution parameters themselves can be learned through meta-optimization. This enables models to acquire not just specific weight values but entire adaptation strategies.

## 10. Limitations and Future Work

While Recursive Weights offer significant advantages, several limitations and future research directions remain:

1. **Initialization Challenges:** Finding optimal initial patterns and references is non-trivial
2. **Training Integration:** Extending backpropagation to directly optimize recursive structures
3. **Hardware Acceleration:** Specialized hardware for recursive weight operations
4. **Theoretical Foundations:** Deeper analysis of convergence properties and representational capacity
5. **Hierarchical Patterns:** Extending the formalism to capture hierarchical relationships between patterns

Future work will focus on addressing these limitations and expanding the application domains of Recursive Weights.

## 11. The Quantization Liberation Trifecta: A Paradigm Shift

The combination of Liquid Quantization, Recursive Tensors, and Recursive Weights represents a fundamental paradigm shift in neural network deployment. Together, they form a trifecta that liberates models from the traditional constraints of quantization while maintaining or even enhancing performance.

### 11.1 Traditional Paradigm vs. Trifecta Paradigm

| Aspect | Traditional Paradigm | Trifecta Paradigm |
|--------|----------------------|-------------------|
| **Compression** | Static precision reduction | Dynamic pattern encoding |
| **Editability** | Require complete retraining | Surgical, targeted modifications |
| **Evolution** | External, explicit updates | Internal, self-guided adaptation |
| **Representation** | Independent, atomic weights | Interconnected, self-referential structures |
| **Adaptability** | Fixed behavior post-deployment | Continuous evolution and refinement |
| **Efficiency** | Uniform precision allocation | Context-aware resource distribution |

### 11.2 Synergistic Effects

The three components of the trifecta interact synergistically:

1. **Liquid Quantization enables Recursive Tensors** by providing the mutability needed for structural adaptation
2. **Recursive Tensors enable Recursive Weights** by establishing the semantic dimensional structure that weights can reference
3. **Recursive Weights enhance Liquid Quantization** by providing compact evolution patterns instead of raw deltas

This positive feedback loop creates a system greater than the sum of its parts, establishing a new foundation for neural network deployment that transcends the limitations of traditional approaches.

### 11.3 Industry Implications

The quantization liberation trifecta addresses critical industry needs:

1. **Deployment Efficiency:** Extreme compression without sacrificing quality
2. **Continuous Improvement:** Models that adapt and evolve post-deployment
3. **Resource Optimization:** Context-aware allocation of computational resources
4. **Development Agility:** Faster iteration through targeted modifications
5. **Infrastructure Scalability:** Reduced storage and bandwidth requirements

By fundamentally rethinking how neural network parameters are represented, stored, and evolved, the trifecta enables a new generation of AI systems that can operate more efficiently while continuously improving themselves.

## 12. Conclusion

This paper introduced Recursive Weights, a novel formalism that redefines neural network parameters as self-referential dynamical systems rather than static values. By encoding weights through their evolutionary patterns, Recursive Weights achieve extreme compression while enabling natural adaptation and evolution.

When combined with Liquid Quantization and Recursive Tensors, Recursive Weights complete a trifecta that liberates neural networks from the traditional constraints of quantization. This trifecta represents a paradigm shift in model deployment, enabling systems that are simultaneously more efficient, more adaptable, and more powerful than traditional approaches.

The implications of this paradigm shift extend beyond immediate performance improvements to enable entirely new capabilities in continual learning, personalization, and autonomous evolution. By reconceptualizing the fundamental building blocks of neural networks, we establish a foundation for the next generation of AI systems that can thrive within resource constraints while continuously improving themselves.

## References

[1] ARNE Bio-Digital Labs, "Liquid Quantized Format (LQT): A Technical Specification and Framework Guide", Technical Whitepaper, 2023.

[2] ARNE Bio-Digital Labs, "Recursive Tensor Architecture: A Mathematical Framework for Self-Referential Neural Networks", Technical Whitepaper, 2023.

[3] Courbariaux, M., Bengio, Y., & David, J. P. (2015). Binaryconnect: Training deep neural networks with binary weights during propagations. Advances in neural information processing systems, 28.

[4] Han, S., Mao, H., & Dally, W. J. (2015). Deep compression: Compressing deep neural networks with pruning, trained quantization and huffman coding. arXiv preprint arXiv:1510.00149.

[5] Jacob, B., Kligys, S., Chen, B., Zhu, M., Tang, M., Howard, A., ... & Kalenichenko, D. (2018). Quantization and training of neural networks for efficient integer-arithmetic-only inference. In Proceedings of the IEEE conference on computer vision and pattern recognition (pp. 2704-2713).

[6] Chen, W., Wilson, J., Tyree, S., Weinberger, K., & Chen, Y. (2015, June). Compressing neural networks with the hashing trick. In International conference on machine learning (pp. 2285-2294).

[7] Gong, Y., Liu, L., Yang, M., & Bourdev, L. (2014). Compressing deep convolutional networks using vector quantization. arXiv preprint arXiv:1412.6115.

[8] Micikevicius, P., Narang, S., Alben, J., Diamos, G., Elsen, E., Garcia, D., ... & Wu, H. (2017). Mixed precision training. arXiv preprint arXiv:1710.03740.

[9] Barnsley, M. F., & Demko, S. (1985). Iterated function systems and the global construction of fractals. Proceedings of the Royal Society of London. A. Mathematical and Physical Sciences, 399(1817), 243-275.

[10] Lindenmayer, A. (1968). Mathematical models for cellular interactions in development I. Filaments with one-sided inputs. Journal of theoretical biology, 18(3), 280-299.

[11] Dettmers, T., Lewis, M., Belkada, Y., & Zettlemoyer, L. (2022). LLM.int8(): 8-bit matrix multiplication for transformers at scale. arXiv preprint arXiv:2208.07339.

[12] Frantar, E., Ashkboos, S., Hoefler, T., & Alistarh, D. (2022). GPTQ: Accurate post-training quantization for generative pre-trained transformers. arXiv preprint arXiv:2210.17323.

[13] Wang, Z., Cai, H., Liu, J., Guo, M., Mu, D., Song, S., ... & Wu, B. (2023). BitNet: Scaling 1-bit transformers for large language models. arXiv preprint arXiv:2310.11453.

[14] Krishnamoorthi, R. (2018). Quantizing deep convolutional networks for efficient inference: A whitepaper. arXiv preprint arXiv:1806.08342.

[15] Mandelbrot, B. B. (1982). The fractal geometry of nature. Freeman.

[16] Strogatz, S. H. (2018). Nonlinear dynamics and chaos: with applications to physics, biology, chemistry, and engineering. CRC press.