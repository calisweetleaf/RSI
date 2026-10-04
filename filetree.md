# File Tree: RSI

**Generated:** 10/4/2026, 10:02:05 AM
**Root Path:** `/home/daeron/LAB/Experiments/projects/RSI`

```
├── biocognitive_core
│   ├── components
│   │   ├── ntp
│   │   │   ├── __init__.py
│   │   │   ├── arfs_aware_reciever.py
│   │   │   ├── consent.py
│   │   │   ├── encryption.py
│   │   │   ├── interface.py
│   │   │   └── receiver.py
│   │   ├── sect
│   │   │   ├── __init__.py
│   │   │   ├── agent.py
│   │   │   ├── therapy.py
│   │   │   └── ursmif_sentinel.py
│   │   ├── sis
│   │   │   ├── __init__.py
│   │   │   ├── evolution.py
│   │   │   ├── monitoring.py
│   │   │   ├── network.py
│   │   │   └── unified_monitor.py
│   │   └── __init__.py
│   ├── config
│   │   ├── biocognitive_config.yaml
│   │   ├── integration_config.yaml
│   │   └── rosemary_config.yaml
│   ├── integration
│   │   ├── __init__.py
│   │   ├── coordinator.py
│   │   ├── enhanced_gateway.py
│   │   ├── gateway.py
│   │   └── translator.py
│   ├── __init__.py
│   ├── config.py
│   ├── exceptions.py
│   └── metrics.py
├── cpp-imports
│   ├── recursive-tensor-cpp
│   │   ├── docs
│   │   │   ├── PORTING_LEDGER.md
│   │   │   └── RTA_FORMAT.md
│   │   ├── include
│   │   │   └── rta
│   │   │       ├── linalg.hpp
│   │   │       ├── recursive_tensor.hpp
│   │   │       ├── rta.hpp
│   │   │       ├── rta_io.hpp
│   │   │       └── types.hpp
│   │   ├── python
│   │   │   └── rta_numpy.py
│   │   ├── references
│   │   │   ├── Recursive Tensor_ A Computational Fabric.md
│   │   │   ├── recursive_tensor.py
│   │   │   ├── recursive_tensor.py_index.md
│   │   │   ├── recursive_tensor_two.py
│   │   │   └── recursive_tensor_whitepaper.md
│   │   ├── src
│   │   │   └── instantiate.cpp
│   │   ├── tests
│   │   │   ├── parity
│   │   │   │   ├── parity.py
│   │   │   │   └── parity_runner.cpp
│   │   │   └── test_rta.cpp
│   │   ├── tools
│   │   │   └── rta_inspect.cpp
│   │   ├── CMakeLists.txt
│   │   ├── README.md
│   │   └── filetree.md
│   └── recursive-weights-cpp
│       ├── docs
│       │   ├── FORMAT.md
│       │   ├── SEMANTICS.md
│       │   ├── TRACEABILITY.md
│       │   └── VALIDATION.md
│       ├── include
│       │   └── rw
│       │       ├── c_api.h
│       │       └── runtime.hpp
│       ├── provenance
│       │   ├── Eigenrecursive_Sentience.md
│       │   ├── recursive-weights-comprehensive-reference.md
│       │   ├── recursive_weights.md
│       │   ├── recursive_weights_core.py
│       │   ├── recursive_weights_core.py.md
│       │   └── recursive_weights_techn3ical_specs.md
│       ├── src
│       │   ├── c_api.cpp
│       │   ├── codec.hpp
│       │   ├── layer.cpp
│       │   ├── main.cpp
│       │   ├── math.cpp
│       │   ├── pattern.cpp
│       │   ├── runtime.cpp
│       │   ├── serialization.cpp
│       │   └── weight.cpp
│       ├── tests
│       │   ├── differential.py
│       │   └── test_runtime.cpp
│       ├── .clang-format
│       ├── CMakeLists.txt
│       ├── Makefile
│       ├── README.md
│       └── SOURCE_SHA256.txt
├── docs
│   ├── self_training_proposal.md
│   └── training_flow_overview.md
├── holo-modal
│   ├── assimilator_modality_encoder.py
│   └── meta_reflective_head.py
├── iala
│   ├── autodidactic_learning.py
│   ├── error_preservation.py
│   ├── phase_transformations.py
│   ├── reference_matrices.py
│   └── weight_evolution_engine.py
├── seed-trainers
│   └── model_assimilator_pretrainer.py
├── src
│   ├── memory
│   │   ├── knowledge_library.py
│   │   ├── memory_attention_substrate.py
│   │   ├── rsl_memory_system.py
│   │   ├── rsl_node.py
│   │   └── unified_memory_system.py
│   ├── stability
│   │   ├── eigenrecursion
│   │   │   ├── __init__.py
│   │   │   ├── eigenrecursion_algorithm.py
│   │   │   ├── eigenrecursive_operations.py
│   │   │   └── test_eigenrecursion_substrate.py
│   │   ├── zebra-core
│   │   │   ├── _source_archive
│   │   │   │   ├── zynx_zebra_core.py.txt
│   │   │   │   ├── zynx_zebra_core_sota_plus_repair.diff
│   │   │   │   ├── zynx_zebra_core_sota_plus_repaired.py.txt
│   │   │   │   └── zynx_zebra_core_sota_triple_plus.py.txt
│   │   │   ├── test_zebra_core_merge.py
│   │   │   └── zebra_core.py
│   │   ├── temporal_eigenloom.py
│   │   └── temporal_eigenstate.py
│   ├── emotion_matrix.py
│   ├── motivation_system.py
│   ├── pineal_gland.py
│   └── ursmif.py
├── tensors-and-weights
│   ├── arfs_tensor
│   │   └── arfs_tensor.py
│   ├── ethical_tensors
│   │   ├── __init__.py
│   │   └── ethical_tensor.py
│   ├── metacognitive_tensor
│   │   ├── __init__.py
│   │   └── metacognitive_tensor.py
│   ├── physics_tensors
│   │   ├── einstein_tensor.py
│   │   ├── energy_momentum_tensor.py
│   │   ├── ricci_tensor.py
│   │   ├── riemann_tensor.py
│   │   ├── shared_spacetime_field.py
│   │   ├── weyl-todo.md
│   │   └── weyl_tensor.py
│   ├── quantum_tensors
│   │   ├── __init__.py
│   │   ├── berry_curvature_tensor.py
│   │   ├── decoherence_model.py
│   │   ├── density_matrix_tensor.py
│   │   ├── quantum_state.py
│   │   └── wigner_function_tensor.py
│   ├── recursive_weights
│   │   ├── __init__.py
│   │   └── recursive_weights_core.py
│   ├── __init__.py
│   ├── base_tensor.py
│   └── tensor_bridge_adapters.py
├── tests
├── tests-outputs
│   ├── component_test_manifest.json
│   ├── component_test_report.md
│   ├── integration_flow.png
│   ├── integration_flow_report.md
│   ├── integration_flow_timeline.json
│   ├── sect.zip
│   ├── sect_full_cycle.png
│   ├── sect_full_cycle_report.md
│   ├── sect_full_cycle_timeline.json
│   ├── sect_long_loop.png
│   ├── sect_long_loop_report.md
│   └── sect_long_loop_timeline.json
├── LICENSE
└── README.md
```

---
*Generated by FileTree Pro Extension*
