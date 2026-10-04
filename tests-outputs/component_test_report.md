# Component Test Report

Run ID: 20260106T234012Z
Started: 2026-01-06T23:40:12.488306Z
Completed: 2026-01-06T23:40:22.216928Z
Duration (s): 9.7286

## Summary
Total: 10 | Passed: 10 | Failed: 0

## Results
- sis.network::nanobot_spec_validation - PASSED (0.4474s)
- sis.network::nanobot_node_behavior - PASSED (0.0024s)
- sect.agent::cognitive_state_differential - PASSED (0.0254s)
- sect.agent::cognitive_state_merge - PASSED (0.0004s)
- sect.agent::modification_plan_roundtrip - PASSED (0.0001s)
- sect.agent::sect_agent_full_cycle - PASSED (8.2576s)
- integration.flow::integration_flow - PASSED (0.4454s)
- sect.agent::sect_agent_long_loop - PASSED (0.5350s)
- sect.therapy::therapy_session_success - PASSED (0.0026s)
- sect.therapy::therapy_session_adaptation - PASSED (0.0015s)

## Interpretation
Tests validate SIS nanobot behavior, SECT cognitive state transitions, and therapy session flow control with deterministic outcomes.

## SECT Full Cycle
Input summary: {'cognitive_load': 0.75, 'self_awareness_level': 0.35, 'attention_focus_count': 1, 'emotional_valence_mean': -0.2, 'memory_activation_mean': 0.2, 'thought_pattern_mean': -0.11666666666666665}
Output summary: {'cognitive_load': 0.85455, 'self_awareness_level': 0.40750000000000003, 'attention_focus_count': 2, 'emotional_valence_mean': -0.05487499999999998, 'memory_activation_mean': 0.2, 'thought_pattern_mean': 0.1638}
Diff: {'magnitude': 0.25784799569785777, 'rate_of_change': 8.04979565704056e-09}
Metrics: {'load_anomaly': 0.0, 'therapeutic_interventions': 2, 'evolution_modifications': 1, 'evolution_cycles': 1}
Interventions applied:
- CognitiveReframing effectiveness=0.532 id=243dec54-0777-4dd0-8511-82ca964f6473
- EmotionalRegulation effectiveness=0.437 id=d281434b-29b7-4c1d-9590-356a410f8422
Chart: test_artifacts\sect_full_cycle.png

## Integration Flow
SIS node: {'node_id': 'integration-node-1', 'state': 'dormant', 'connected_nodes': ['integration-node-2'], 'health_metrics': {'energy_level': 0.86, 'integrity': 0.92, 'contamination': 0.0, 'error_rate': 0.0, 'responsiveness': 1.0}, 'replication_rate': 0.05, 'energy_efficiency': 0.8}
NTP decoded: {'timestamp': 1767742821.2434826, 'amplitude': 0.86, 'frequency': 8.6, 'coherence': 0.92, 'domain': 'cognitive', 'node_id': 'integration-node-1', 'state': 'dormant', 'method': 'QRL2'}
Input summary: {'cognitive_load': 0.07999999999999996, 'self_awareness_level': 0.916, 'attention_focus_count': 2, 'emotional_valence_mean': 0.42000000000000004, 'memory_activation_mean': 0.086, 'thought_pattern_mean': 0.622}
Output summary: {'cognitive_load': 0.12999999999999995, 'self_awareness_level': 0.9410000000000001, 'attention_focus_count': 2, 'emotional_valence_mean': 0.42000000000000004, 'memory_activation_mean': 0.086, 'thought_pattern_mean': 0.6603333333333333}
Diff: {'magnitude': 0.03132491021535415, 'rate_of_change': 1.2279944417795345}
Chart: test_artifacts\integration_flow.png

## SECT Long Loop
Config: {'cycles': 20, 'noise_base': 0.08, 'noise_floor': 0.01, 'adaptation_frequency': 3, 'self_modification_enabled': False, 'max_concurrent_interventions': 1}
Steady state: {'window': 5, 'mean_inter_cycle_diff': 0.009763336495144822, 'std_inter_cycle_diff': 0.0019064648068354976, 'stable': True}
Initial output: {'cognitive_load': 0.6644925249011688, 'self_awareness_level': 0.42934788210620906, 'attention_focus_count': 2, 'emotional_valence_mean': -0.04165372183976365, 'memory_activation_mean': 0.1817669757108013, 'thought_pattern_mean': 0.38825242810482036}
Final output: {'cognitive_load': 1.0389465869450463, 'self_awareness_level': 0.810936746245832, 'attention_focus_count': 2, 'emotional_valence_mean': 0.08613958252500725, 'memory_activation_mean': 0.19163654796457655, 'thought_pattern_mean': 0.4464540951683164}
Chart: test_artifacts\sect_long_loop.png