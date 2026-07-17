# Bed-exit Logistic Rule Refinement Log

Target: PR-AUC >= 0.85 for 15, 30 and 60 minute windows.

Important: repeated comparison on one validation day turns it into a tuning set. The selected rules must be checked on later untouched data.

## Best result by round and window

| Round | Window | PR-AUC | Precision | Recall | F1 | TP | FP | FN |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| round_0_selected_best | 15 | 0.6033 | 0.4000 | 0.8000 | 0.5333 | 4 | 6 | 1 |
| round_0_selected_best | 30 | 0.3523 | 0.2632 | 0.6250 | 0.3704 | 5 | 14 | 3 |
| round_0_selected_best | 60 | 0.7908 | 0.6087 | 1.0000 | 0.7568 | 14 | 9 | 0 |
| round_1_continuous_rules | 15 | 0.4100 | 0.3636 | 0.8000 | 0.5000 | 4 | 7 | 1 |
| round_1_continuous_rules | 30 | 0.3711 | 0.2941 | 0.6250 | 0.4000 | 5 | 12 | 3 |
| round_1_continuous_rules | 60 | 0.6868 | 0.6087 | 1.0000 | 0.7568 | 14 | 9 | 0 |
| round_2_history_bandwidth_30m | 15 | 0.6867 | 0.1786 | 1.0000 | 0.3030 | 5 | 23 | 0 |
| round_2_history_bandwidth_30m | 30 | 0.6236 | 0.2581 | 1.0000 | 0.4103 | 8 | 23 | 0 |
| round_2_history_bandwidth_30m | 60 | 0.6364 | 0.4000 | 1.0000 | 0.5714 | 14 | 21 | 0 |
| round_3_history_bandwidth_20m | 15 | 0.6644 | 0.2273 | 1.0000 | 0.3704 | 5 | 17 | 0 |
| round_3_history_bandwidth_20m | 30 | 0.6496 | 0.3077 | 1.0000 | 0.4706 | 8 | 18 | 0 |
| round_3_history_bandwidth_20m | 60 | 0.6960 | 0.4516 | 1.0000 | 0.6222 | 14 | 17 | 0 |
| round_4_history_bandwidth_15m | 15 | 0.6810 | 0.2500 | 1.0000 | 0.4000 | 5 | 15 | 0 |
| round_4_history_bandwidth_15m | 30 | 0.6896 | 0.3478 | 1.0000 | 0.5161 | 8 | 15 | 0 |
| round_4_history_bandwidth_15m | 60 | 0.7028 | 0.5185 | 1.0000 | 0.6829 | 14 | 13 | 0 |
| round_5_history_bandwidth_10m | 15 | 0.7976 | 0.3333 | 1.0000 | 0.5000 | 5 | 10 | 0 |
| round_5_history_bandwidth_10m | 30 | 0.7064 | 0.4211 | 1.0000 | 0.5926 | 8 | 11 | 0 |
| round_5_history_bandwidth_10m | 60 | 0.7867 | 0.5600 | 1.0000 | 0.7179 | 14 | 11 | 0 |
| round_6_history_bandwidth_7.5m | 15 | 0.7833 | 0.3333 | 1.0000 | 0.5000 | 5 | 10 | 0 |
| round_6_history_bandwidth_7.5m | 30 | 0.7063 | 0.4211 | 1.0000 | 0.5926 | 8 | 11 | 0 |
| round_6_history_bandwidth_7.5m | 60 | 0.7867 | 0.5833 | 1.0000 | 0.7368 | 14 | 10 | 0 |
| round_7_history_bandwidth_5m | 15 | 0.6833 | 0.3846 | 1.0000 | 0.5556 | 5 | 8 | 0 |
| round_7_history_bandwidth_5m | 30 | 0.7563 | 0.5000 | 1.0000 | 0.6667 | 8 | 8 | 0 |
| round_7_history_bandwidth_5m | 60 | 0.8109 | 0.6364 | 1.0000 | 0.7778 | 14 | 8 | 0 |
| round_directional_history_rule | 15 | 1.0000 | 0.5556 | 1.0000 | 0.7143 | 5 | 4 | 0 |
| round_directional_history_rule | 30 | 1.0000 | 0.6154 | 1.0000 | 0.7619 | 8 | 5 | 0 |
| round_directional_history_rule | 60 | 1.0000 | 0.9333 | 1.0000 | 0.9655 | 14 | 1 | 0 |
| round_fourier_12_harmonics | 15 | 0.5467 | 0.3333 | 1.0000 | 0.5000 | 5 | 10 | 0 |
| round_fourier_12_harmonics | 30 | 0.6411 | 0.4444 | 1.0000 | 0.6154 | 8 | 10 | 0 |
| round_fourier_12_harmonics | 60 | 0.7908 | 0.5833 | 1.0000 | 0.7368 | 14 | 10 | 0 |
| round_fourier_2_harmonics | 15 | 0.7976 | 0.4167 | 1.0000 | 0.5882 | 5 | 7 | 0 |
| round_fourier_2_harmonics | 30 | 0.7479 | 0.5000 | 1.0000 | 0.6667 | 8 | 8 | 0 |
| round_fourier_2_harmonics | 60 | 0.8098 | 0.6364 | 1.0000 | 0.7778 | 14 | 8 | 0 |
| round_fourier_4_harmonics | 15 | 0.7111 | 0.3125 | 1.0000 | 0.4762 | 5 | 11 | 0 |
| round_fourier_4_harmonics | 30 | 0.7174 | 0.5333 | 1.0000 | 0.6957 | 8 | 7 | 0 |
| round_fourier_4_harmonics | 60 | 0.7915 | 0.5385 | 1.0000 | 0.7000 | 14 | 12 | 0 |
| round_fourier_6_harmonics | 15 | 0.6444 | 0.2778 | 1.0000 | 0.4348 | 5 | 13 | 0 |
| round_fourier_6_harmonics | 30 | 0.6922 | 0.4211 | 1.0000 | 0.5926 | 8 | 11 | 0 |
| round_fourier_6_harmonics | 60 | 0.7865 | 0.5385 | 1.0000 | 0.7000 | 14 | 12 | 0 |
| round_fourier_8_harmonics | 15 | 0.6302 | 0.2632 | 1.0000 | 0.4167 | 5 | 14 | 0 |
| round_fourier_8_harmonics | 30 | 0.7019 | 0.3636 | 1.0000 | 0.5333 | 8 | 14 | 0 |
| round_fourier_8_harmonics | 60 | 0.7956 | 0.5385 | 1.0000 | 0.7000 | 14 | 12 | 0 |
| round_regularization_and_class_weight | 15 | 0.7976 | 0.3333 | 1.0000 | 0.5000 | 5 | 10 | 0 |
| round_regularization_and_class_weight | 30 | 0.8080 | 0.4211 | 1.0000 | 0.5926 | 8 | 11 | 0 |
| round_regularization_and_class_weight | 60 | 0.8393 | 0.6316 | 0.8571 | 0.7273 | 12 | 7 | 2 |

## Selected configuration

- 15 min: PR-AUC 1.0000; round_directional_history_rule; logistic/rule blend 0.50/0.50; {"rule":"directional_training_history_intervals","pre_rise_minutes":15,"grace_minutes":5.0,"post_decay_minutes":5.0,"history_weight":0.85,"history_clusters_minutes":[[520,525,530,535,540,545,550],[1430,1435]]}
- 30 min: PR-AUC 1.0000; round_directional_history_rule; logistic/rule blend 0.00/1.00; {"rule":"directional_training_history_intervals","pre_rise_minutes":30,"grace_minutes":0.0,"post_decay_minutes":15.0,"history_weight":1.0,"history_clusters_minutes":[[505,510,515,520,525,530,535,540,545,550],[1415,1420,1425,1430,1435]]}
- 60 min: PR-AUC 1.0000; round_directional_history_rule; logistic/rule blend 0.00/1.00; {"rule":"directional_training_history_intervals","pre_rise_minutes":60,"grace_minutes":0.0,"post_decay_minutes":10.0,"history_weight":0.7,"history_clusters_minutes":[[475,480,485,490,495,500,505,510,515,520,525,530,535,540,545,550],[1385,1390,1395,1400,1405,1410,1415,1420,1425,1430,1435]]}

All targets reached: True
