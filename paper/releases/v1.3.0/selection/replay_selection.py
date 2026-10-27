"""Replay the paper's frozen A55 reference rule from validation scores.

This verifies decisions from saved post-adaptation validation scores; it does
not run source training, target adaptation, calibration, or model inference.
"""
from pathlib import Path
import csv
import json
import math
from frozen_policy import gate, rank

ROOT = Path(__file__).resolve().parent.parent
LIMITS = {'tight': (30000, 1500000), 'medium': (100000, 5000000),
          'loose': (500000, 20000000)}

def main():
    payload = json.loads((ROOT/'data'/'selection_inputs.json').read_text(encoding='utf8'))
    cases = [c for c in payload['cases'] if c['role'] == 'evaluation']
    with (ROOT/'data'/'individual_results.csv').open(encoding='utf8', newline='') as f:
        published = {(r['case_id'],r['budget']):r for r in csv.DictReader(f) if r['method']=='MSA-DTI'}
    assert len(cases) == 120 and len(published) == 360
    for case in cases:
        scores = case['scores']
        assert all(math.isfinite(v) and v > 0 for v in scores)
        for budget,(parameters,operations) in LIMITS.items():
            feasible = [q for q in case['qaxis'] if case['keys'][q][0] <= parameters and case['keys'][q][1] <= operations]
            assert 'A55' in feasible
            environment = {'qaxis':case['qaxis'], 'F':feasible, 'keys':case['keys']}
            admissible, failed = gate(environment, scores, 'A55', .05, False)
            assert not failed
            selected = rank(environment, admissible, scores)
            row = published[(case['case_id'], budget)]
            assert selected == row['selected_token'], (case['case_id'], budget, selected, row['selected_token'])
    print('PASS: 360 evaluation selections match the paper records')

if __name__ == '__main__':
    main()
