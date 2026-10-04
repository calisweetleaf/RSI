#pragma once
// Recursive Weights native runtime. Source authority: docs/TRACEABILITY.md.
#include <array>
#include <atomic>
#include <chrono>
#include <complex>
#include <cstdint>
#include <deque>
#include <functional>
#include <map>
#include <memory>
#include <mutex>
#include <optional>
#include <random>
#include <shared_mutex>
#include <stdexcept>
#include <string>
#include <vector>

namespace rw {
using Vector = std::vector<float>;
using Position = std::array<int32_t, 5>;
using Metrics = std::map<std::string, double>;
struct Error : std::runtime_error {
    using std::runtime_error::runtime_error;
};
struct ValidationError : Error {
    using Error::Error;
};
struct FormatError : Error {
    using Error::Error;
};
struct Unsupported : Error {
    using Error::Error;
};
struct Matrix {
    size_t rows = 0, cols = 0;
    Vector data;
    Matrix() = default;
    Matrix(size_t r, size_t c, float fill = 0);
    Matrix(size_t r, size_t c, Vector values);
    float &operator()(size_t r, size_t c) {
        return data.at(r * cols + c);
    }
    float operator()(size_t r, size_t c) const {
        return data.at(r * cols + c);
    }
    static Matrix identity(size_t n);
};
void validate(const Vector &, const std::string &, std::optional<size_t> size = {},
              double bound = 1e6);
void validate(const Matrix &, const std::string &);
double norm(const Vector &);
Vector matvec(const Matrix &, const Vector &);
Matrix matmul(const Matrix &, const Matrix &);
std::vector<std::complex<double>> eigenvalues(const Matrix &);
double spectral_radius(const Matrix &);
double spectral_norm(const Matrix &);
size_t matrix_rank(const Matrix &);
Matrix stabilize_matrix(const Matrix &, double maximum = 0.95);
std::string position_key(const Position &);
Position add_position(const Position &, const Position &);
std::string simd_backend();
void add_components(Vector &, const Vector &, const Vector &, const Vector &, const Vector &,
                    const Vector &, bool simd = true);

enum class Semantics : uint32_t { Equation = 0, Python = 1 };
enum class Stability { Stable, Unstable, Convergent, Divergent };
enum WeightFlags : uint32_t {
    SelfStabilizing = 1,
    Evolutive = 2,
    PatternLinked = 4,
    FractalEnabled = 8,
    ErrorPreserving = 16,
    TemporalCoherence = 32,
    DimensionAware = 64,
    HybridPrecision = 128
};
struct Config {
    uint32_t max_recursion_depth = 10, stability_check_interval = 5, cache_size = 1000,
             thread_pool_size = 4;
    double convergence_threshold = 1e-6, spectral_radius_threshold = .98, max_growth_ratio = 1.20,
           ema_momentum = .90, max_effective_norm = 10, damping_factor = .90;
    uint32_t power_iter_steps = 12, min_history_length = 5;
    bool enable_simd = true;
    void validate() const;
};
struct PhaseTransformation {
    Vector base_phase;
    Matrix harmonic_amplitudes; // harmonics x dimension; scalar harmonics use one column
    Vector frequencies, phase_offsets;
    bool scalar_amplitudes = false; // preserve rank-1 Python harmonic encoding
    void validate(size_t dimension) const;
    Vector evaluate(double time, bool python_bounds = false) const;
};
struct DeltaComponent {
    Vector base_delta, adaptive_factor;
    double depth_scaling = 1;
    Vector evaluate(uint32_t depth, bool python_bounds = false) const;
};
struct RecursiveReference {
    Position relative_position{};
    double contribution_weight = 0;
    Matrix transformation_matrix;
    int32_t temporal_offset = 0;
};
struct StabilityMetrics {
    double spectral_radius = 0, lyapunov_coefficient = 0, error_bound = 0, convergence_rate = 0,
           fractal_dimension = 0, self_similarity_metric = 0, information_capacity = 0,
           compression_efficiency = 0;
    Metrics as_map() const;
};
struct MutationParameters {
    enum class Type : uint32_t { Phase, Reference, Pattern, Comprehensive };
    Type type = Type::Comprehensive;
    double strength = .1, temperature = 1;
    uint32_t seed = 42;
    double frequency_multiplier = 1, amplitude_multiplier = 1, phase_shift = 0, weight_scaling = 1,
           matrix_perturbation = .01;
    uint32_t target_pattern_id = 0;
    double blend_factor = .5;
};
struct EvolutionParameters {
    enum class Operator { GradientDescent, Genetic, SimulatedAnnealing };
    Operator algorithm = Operator::Genetic;
    double learning_rate = .001, momentum = .9, decay_rate = .95, selection_pressure = .8,
           crossover_rate = .7, mutation_rate = .1;
    enum class Schedule { Constant, Linear, Exponential };
    Schedule temperature_schedule = Schedule::Exponential;
    uint32_t population_size = 10, generations = 100, elite_count = 1, tournament_size = 3,
             seed = 42;
    bool adaptive_mutation = false;
};
struct RecursiveWeight {
    uint32_t base_codebook_index = 0;
    Position tensor_position{};
    PhaseTransformation phase;
    std::vector<RecursiveReference> recursive_refs;
    Vector error_preservation;
    DeltaComponent delta;
    double scale_factor = 1;
    Config config;
    uint32_t flags = 0;
    size_t dimension() const {
        return error_preservation.size();
    }
    static RecursiveWeight neutral(size_t dimension, uint32_t codebook_index = 0,
                                   Position position = {});
    void validate() const;
    Vector compute_phase_value(double t, Semantics mode = Semantics::Equation) const;
    Vector compute_delta_value(uint32_t depth, Semantics mode = Semantics::Equation) const;
    Matrix compute_jacobian_matrix() const;
    double
    estimate_contraction_factor() const; // Python mean-Frobenius proxy, explicitly named in reports
    double contraction_bound() const;    // sum of weighted Frobenius norms
    StabilityMetrics get_stability_metrics() const;
    Metrics mathematical_summary() const;
    Metrics information_theoretic_bounds() const;
    Metrics optimization_potential() const;
    Vector compute_fixed_point_estimate(const Matrix &, double time = 0) const;
    Vector apply_recursive_transformation(const Vector &) const;
    RecursiveWeight mutate(const MutationParameters &) const;
    void stabilize();
    bool verify_post_mutation_stability() const;
    std::pair<RecursiveWeight, RecursiveWeight> crossover(const RecursiveWeight &, double rate,
                                                          uint32_t seed) const;
    double compute_fitness(const std::function<double(const RecursiveWeight &)> &target = {}) const;
};
using FitnessFunction = std::function<double(const RecursiveWeight &)>;
// Gradients are supplied by the caller: the Python random "gradient" is not an objective
// derivative.
using GradientFunction = std::function<RecursiveWeight(const RecursiveWeight &)>;
struct EvolutionResult {
    RecursiveWeight weight;
    std::vector<double> fitness_history;
};
EvolutionResult evolve(const RecursiveWeight &, const EvolutionParameters &,
                       const FitnessFunction &, const GradientFunction &gradient = {});
std::vector<RecursiveWeight> evolve_population(const std::vector<RecursiveWeight> &,
                                               const EvolutionParameters &,
                                               const FitnessFunction &);
void enforce_temporal_coherence(std::vector<RecursiveWeight> &, double lambda, double threshold);

struct DynamicalSystemsAnalyzer {
    static Vector fixed_point(double alpha, const Vector &base);
    static bool lyapunov_stable(const std::vector<Matrix> &);
    static double attractor_dimension(const std::vector<Matrix> &);
    static double capacity_amplification(double base_bits, const Vector &bits,
                                         const Vector &multiplicities);
    static bool approximation_parameter_count(size_t dimension, size_t references, size_t depth);
    static double kolmogorov_expression(double full);
    static double uniform_convergence_bound(double gamma, double C, uint32_t iterations);
    static uint32_t convergence_steps(double epsilon, double gamma, double C);
    static double computational_complexity(double n, double d, double epsilon);
    static double error_accumulation_bound(double initial, const Vector &errors, double decay);
    static double error_correction_capacity(double gamma, double error_max);
    static double weight_space_dimension(double base, const Vector &dimensions,
                                         const Vector &scaling);
    static double self_similarity(const std::vector<Matrix> &);
    static double multiscale_efficiency(double full, double base,
                                        const std::vector<std::pair<double, double>> &,
                                        double dimension);
    static double minimum_description_length(const Vector &entropies, double mutual_information);
    static double information_capacity(double bits, const Vector &reference_bits,
                                       const Vector &preservation);
    static double compression_efficiency(double n, double quant_bits, double patterns,
                                         double pattern_bits, double refs, double ref_bits,
                                         double base, double base_bits);
};

enum class PatternType : uint8_t {
    Constant,
    Linear,
    Sinusoidal,
    Exponential,
    Polynomial,
    Logistic,
    Piecewise,
    Stochastic,
    Fractal,
    Custom
};
struct Pattern {
    PatternType type = PatternType::Constant;
    uint8_t dimension_mask = 31;
    double scale_factor = 1, rotation_factor = 0;
    std::vector<uint8_t> data;
};
class PatternLibrary {
    mutable std::shared_mutex mutex_;
    std::map<uint32_t, Pattern> patterns_;
    uint32_t next_ = 1;

  public:
    using Custom = std::function<Vector(const Pattern &, const Vector &, uint32_t)>;
    uint32_t register_pattern(Pattern);
    Pattern get(uint32_t) const;
    void update(uint32_t, Pattern);
    bool remove(uint32_t);
    Vector evaluate(uint32_t, const Vector &, uint32_t seed = 42, const Custom &custom = {}) const;
    std::map<uint32_t, Pattern> snapshot() const;
};

struct EvaluationOptions {
    uint32_t depth = 0;
    double time = 0;
    Semantics semantics = Semantics::Equation;
    bool use_cache = true, track_history = true, strict_references = true;
};
struct ValidationResult {
    bool valid = true;
    std::vector<std::string> errors, warnings;
};
struct RuntimeSnapshot {
    uint64_t computations = 0;
    Stability state = Stability::Stable;
    std::deque<Vector> effective_history;
    std::deque<Metrics> stability_history;
    Vector ema, last;
};
struct CacheStats {
    uint64_t hits = 0, misses = 0, evictions = 0;
    size_t l1_entries = 0, l2_entries = 0;
};
class RecursiveWeightSystem {
    struct Impl;
    std::unique_ptr<Impl> impl_;

  public:
    explicit RecursiveWeightSystem(Config config = {});
    ~RecursiveWeightSystem();
    RecursiveWeightSystem(const RecursiveWeightSystem &) = delete;
    RecursiveWeightSystem &operator=(const RecursiveWeightSystem &) = delete;
    void set_codebook(Matrix);
    Matrix codebook() const;
    void register_weight(std::string key, RecursiveWeight);
    RecursiveWeight get_weight(const std::string &) const;
    bool has_weight(const std::string &) const;
    bool remove_weight(const std::string &);
    std::vector<std::string> keys() const;
    size_t size() const;
    Vector reconstruct(const std::string &, EvaluationOptions = {});
    std::map<std::string, Vector> batch_compute(const std::vector<std::string> &,
                                                EvaluationOptions = {});
    void mutate_weight(const std::string &, const MutationParameters &);
    void evolve_weight(const std::string &, const EvolutionParameters &, const FitnessFunction &,
                       const GradientFunction &gradient = {});
    std::vector<MutationParameters> mutation_history(const std::string &) const;
    void clear_all_caches();
    CacheStats cache_stats() const;
    RuntimeSnapshot runtime_snapshot(const std::string &) const;
    ValidationResult validate_system() const;
    Metrics analyze_system_stability(size_t maximum_matrix_dimension = 4096) const;
    size_t optimize_recursive_references(double target = .8);
    bool detect_recursion_loops(const std::string &, uint32_t depth = 100) const;
    Metrics performance_summary() const;
    void precompute(const std::vector<std::string> &, EvaluationOptions = {});
    std::map<double, Vector> multiscale(const std::string &, const std::vector<double> &,
                                        uint32_t depth = 1);
    std::map<uint32_t, Metrics> analyze_depth(const std::string &, uint32_t maximum,
                                              double time = 1);
    std::vector<uint8_t> serialize_system_binary() const;
    void deserialize_system_binary(const uint8_t *, size_t);
    void save(const std::string &) const;
    void load(const std::string &); // validated transaction; codebook and all weights
    void save_weights_directory(const std::string &) const;
    size_t load_weights_directory(const std::string &);
};
using RecursiveWeightRegistry = RecursiveWeightSystem;
using RecursiveWeightCoreEngine = RecursiveWeightSystem;
RecursiveWeightSystem &get_registry();

class RecursiveWeightSerializer {
  public:
    static void serialize_weight(const RecursiveWeight &, const std::string &,
                                 bool legacy_v13 = false);
    static RecursiveWeight deserialize_weight(const std::string &);
    static std::vector<uint8_t> encode(const RecursiveWeight &, bool legacy_v13 = false);
    static RecursiveWeight decode(const uint8_t *, size_t);
};
struct LegacyWeightHeader {
    uint32_t weight_id, reference_dimension, recursion_depth;
    float self_reference_strength;
    uint32_t evolution_codebook_id, num_references, flags, base_pattern_index,
        reference_table_index, phase_data_index, error_term_index;
    Position tensor_position;
};
LegacyWeightHeader
read_legacy_header(const std::string &); // metadata only: original format has no numerical payload

struct LayerOutput {
    Matrix output, attention, weight_stack;
};
class RecursiveWeightLayer {
  public:
    RecursiveWeightSystem registry;
    Matrix input_projection; // output_dim x input_dim
    Vector input_bias, norm_weight, norm_bias;
    double norm_epsilon = 1e-5;
    RecursiveWeightLayer(size_t input_dim, size_t output_dim, size_t num_weights = 32, Config = {},
                         uint32_t seed = 42);
    LayerOutput forward(const Matrix &flattened_batch_sequence,
                        EvaluationOptions = {3, 0, Semantics::Equation, true, true, false});
    Matrix compute_layer_jacobian(const Vector &,
                                 EvaluationOptions = {1, 0, Semantics::Equation, true, false, false});
    Metrics analyze_attention_patterns(const Matrix &,
                                       EvaluationOptions = {1, 0, Semantics::Equation, true, true, false});
    std::map<uint32_t, Metrics> analyze_recursive_flow(const Matrix &,
                                                       const std::vector<uint32_t> &);
    void save(const std::string &) const;
    void load(const std::string &);
};
// Eigenrecursive paper §7.1: caller supplies the undefined scientific metric operators.
struct EigenrecursiveResult {
    Vector fixed_point;
    bool converged = false;
    uint32_t iterations = 0;
    std::vector<Metrics> trace;
};
EigenrecursiveResult compute_cognitive_eigenstate(
    Vector initial, const std::function<Vector(const Vector &)> &recursive_transform,
    double epsilon = 1e-6, uint32_t max_iterations = 1000,
    const std::function<Metrics(const Vector &, const Vector &)> &metric_operator = {});
} // namespace rw
