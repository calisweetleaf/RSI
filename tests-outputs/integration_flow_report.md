# Biocognitive Integration Flow Report

## Overview
Sequential SIS -> NTP -> SECT integration flow with deterministic inputs.

## SIS Snapshot
{'node_id': 'integration-node-1', 'state': 'dormant', 'connected_nodes': ['integration-node-2'], 'health_metrics': {'energy_level': 0.86, 'integrity': 0.92, 'contamination': 0.0, 'error_rate': 0.0, 'responsiveness': 1.0}, 'replication_rate': 0.05, 'energy_efficiency': 0.8}

## NTP Signal
{'timestamp': 1767742821.2434826, 'amplitude': 0.86, 'frequency': 8.6, 'coherence': 0.92, 'domain': 'cognitive', 'node_id': 'integration-node-1', 'state': 'dormant'}

## NTP Decoded Signal
{'timestamp': 1767742821.2434826, 'amplitude': 0.86, 'frequency': 8.6, 'coherence': 0.92, 'domain': 'cognitive', 'node_id': 'integration-node-1', 'state': 'dormant', 'method': 'QRL2'}

## SECT Input State
{'cognitive_load': 0.07999999999999996, 'self_awareness_level': 0.916, 'attention_focus_count': 2, 'emotional_valence_mean': 0.42000000000000004, 'memory_activation_mean': 0.086, 'thought_pattern_mean': 0.622}

## SECT Output State
{'cognitive_load': 0.12999999999999995, 'self_awareness_level': 0.9410000000000001, 'attention_focus_count': 2, 'emotional_valence_mean': 0.42000000000000004, 'memory_activation_mean': 0.086, 'thought_pattern_mean': 0.6603333333333333}

## Differential
{'magnitude': 0.03132491021535415, 'rate_of_change': 1.2279944417795345}

## Step-by-Step Timeline
- sis_node_ready at 2026-01-06T23:40:21.243482Z
  data: {'node_id': 'integration-node-1', 'state': 'dormant', 'connected_nodes': ['integration-node-2'], 'health_metrics': {'energy_level': 0.86, 'integrity': 0.92, 'contamination': 0.0, 'error_rate': 0.0, 'responsiveness': 1.0}, 'replication_rate': 0.05, 'energy_efficiency': 0.8}
- sis_signal_emitted at 2026-01-06T23:40:21.243482Z
  data: {'timestamp': 1767742821.2434826, 'amplitude': 0.86, 'frequency': 8.6, 'coherence': 0.92, 'domain': 'cognitive', 'node_id': 'integration-node-1', 'state': 'dormant'}
- ntp_signal_encoded at 2026-01-06T23:40:21.245507Z
  data: {'bytes': 159, 'level': 'QRL2'}
- ntp_signal_decoded at 2026-01-06T23:40:21.245507Z
  data: {'timestamp': 1767742821.2434826, 'amplitude': 0.86, 'frequency': 8.6, 'coherence': 0.92, 'domain': 'cognitive', 'node_id': 'integration-node-1', 'state': 'dormant', 'method': 'QRL2'}
- sect_input_state at 2026-01-06T23:40:21.245507Z
  data: {'cognitive_load': 0.07999999999999996, 'self_awareness_level': 0.916, 'attention_focus_count': 2, 'emotional_valence_mean': 0.42000000000000004, 'memory_activation_mean': 0.086, 'thought_pattern_mean': 0.622}
- sect_initial_state_loaded at 2026-01-06T23:40:21.268992Z
  data: {'cognitive_load': 0.07999999999999996, 'self_awareness_level': 0.916, 'attention_focus_count': 2, 'emotional_valence_mean': 0.42000000000000004, 'memory_activation_mean': 0.086, 'thought_pattern_mean': 0.622}
- sect_metacognitive_monitoring at 2026-01-06T23:40:21.268992Z
  data: {'pattern_coherence': 0.379799947340702, 'load_anomaly': 0, 'emotional_consistency': 0.0, 'self_awareness': 0.916, 'timestamp': '2026-01-06T23:40:21.268992'}
- sect_intervention_selection at 2026-01-06T23:40:21.268992Z
  data: {'scored': [{'id': 'aa2dba48-00b9-4281-a236-dcf2267feda8', 'type': 'CognitiveReframing', 'priority': 0.75, 'applicability': 0.9985404885544356, 'weighted': 0.7489053664158267}, {'id': '711055a1-60cb-45b4-8cdf-15f7c64f33e1', 'type': 'EmotionalRegulation', 'priority': 0.6, 'applicability': 0.58, 'weighted': 0.348}, {'id': '19946682-1b52-431a-9149-296b7b339dc4', 'type': 'URSMIFContradictionIntervention', 'priority': 0.9, 'applicability': 0.0, 'weighted': 0.0}], 'selected_ids': ['aa2dba48-00b9-4281-a236-dcf2267feda8']}
- sect_intervention_application at 2026-01-06T23:40:21.269542Z
  data: {'before': {'cognitive_load': 0.07999999999999996, 'self_awareness_level': 0.916, 'attention_focus_count': 2, 'emotional_valence_mean': 0.42000000000000004, 'memory_activation_mean': 0.086, 'thought_pattern_mean': 0.622}, 'after': {'cognitive_load': 0.12999999999999995, 'self_awareness_level': 0.9410000000000001, 'attention_focus_count': 2, 'emotional_valence_mean': 0.42000000000000004, 'memory_activation_mean': 0.086, 'thought_pattern_mean': 0.6603333333333333}}
- sect_self_modification at 2026-01-06T23:40:21.269542Z
  data: {'plan': {'level': 'LEVEL_1', 'target_component': 'general_parameters', 'type': 'GRADIENT_OPTIMIZATION', 'description': 'Periodic parameter optimization', 'success_metrics': {'convergence_threshold': 0.0001, 'iteration_limit': 1000}, 'resource_estimate': 1.0, 'validation_checks': []}}
- sect_metrics_update at 2026-01-06T23:40:21.269542Z
  data: {'therapeutic_interventions': 1, 'evolution_cycles': 1, 'evolution_modifications': 1}

## Intervention Applications
- CognitiveReframing effectiveness=0.468 diff={'magnitude': 0.03132491021535415, 'rate_of_change': 1.2279944417795345}

## Self-Modification Plan
{'level': 'LEVEL_1', 'target_component': 'general_parameters', 'type': 'GRADIENT_OPTIMIZATION', 'description': 'Periodic parameter optimization', 'success_metrics': {'convergence_threshold': 0.0001, 'iteration_limit': 1000}, 'resource_estimate': 1.0, 'validation_checks': []}

## Chart
test_artifacts\integration_flow.png