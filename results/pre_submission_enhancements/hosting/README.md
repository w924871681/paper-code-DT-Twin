# Hardware Profiling Evidence

This directory contains the two formal batch-one profiling sessions and
their public summaries.

Protocol:

- six unique retained architectures;
- prediction horizons H in {1, 4};
- Intel Core i7-12700H CPU and NVIDIA RTX 3060 Laptop GPU;
- evaluation mode and batch size one;
- 100 warm-up inferences;
- five repetitions of 1000 timed inferences;
- CUDA synchronization around each timed region;
- median latency as the primary latency statistic;
- serialized state-dictionary size as the model-size measurement.
