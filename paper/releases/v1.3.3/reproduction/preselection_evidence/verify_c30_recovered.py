"""Recompute C3-0 preselection counts from recovered case-level records.

Reads historical artifacts only. It does not train or evaluate models and
does not establish historical independence of later evaluation sets.
"""
from pathlib import Path
from collections import Counter
import csv
import hashlib
import json
import math
import sys
import zipfile

ROOT = Path(__file__).resolve().parent

def read(name):
    return json.loads((ROOT / name).read_text(encoding='utf-8-sig'))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

fixed, oracle = read('c30_fixed_anchor.json'), read('c30_c1_oracle.json')
analysis, audit = read('c30_analysis.json'), read('c30_audit.json')
source = read('source_assets_manifest.json')
assert audit['decision'] == 'PASS_C30_DIAGNOSTIC_COMPLETE_AND_AUDITED'
assert all(audit['checks'].values()) and not audit['test_used']
for field, name in [('fixed_sha256', 'c30_fixed_anchor.json'), ('oracle_sha256', 'c30_c1_oracle.json'), ('analysis_sha256', 'c30_analysis.json')]:
    assert audit[field] == sha(ROOT / name), name
assert oracle['fixed_anchor_sha256'] == sha(ROOT / 'c30_fixed_anchor.json')
assert analysis['fixed_anchor_sha256'] == sha(ROOT / 'c30_fixed_anchor.json')
assert analysis['oracle_sha256'] == sha(ROOT / 'c30_c1_oracle.json')
assert fixed['source_manifest_sha256'] == sha(ROOT / 'source_assets_manifest.json')
assert fixed['frozen_asset_hashes'] == oracle['frozen_asset_hashes']
bank_hash = 'bb3a655606af3b554a8f088bb1d2f3f8d9f190b0911a812fd3755d3de3216b9d'
assert fixed['frozen_asset_hashes']['bank'] == bank_hash
for obj in [fixed, oracle, analysis]:
    assert not obj['test_used']
    protocol = obj['protocol']
    assert protocol['data_seed'] == protocol['train_seed'] == 2904
    assert protocol['diagnostic_pool'] == [900, 20, 180000]
    assert protocol['H_list'] == [1, 4] and protocol['K_list'] == [10, 20]
    assert protocol['architecture_count'] == 66 and protocol['anchor_arch_idx'] == 57
assert fixed['complete'] and oracle['complete']
assert fixed['N_records'] == oracle['N_records'] == 80
assert oracle['expected_candidate_count'] == oracle['completed_candidate_count'] == 3528
assert set(fixed['records']) == set(oracle['records']) and len(oracle['records']) == 80

oracle_wins, val_wins = Counter(), Counter()
cases, count, coordinates = [], 0, set()
for key, rec in sorted(oracle['records'].items()):
    ref = fixed['records'][key]
    assert rec['complete'] and ref['complete'] and not rec['test_used'] and not ref['test_used']
    coordinate = (rec['center_id'], rec['H'], rec['K'])
    assert coordinate not in coordinates
    coordinates.add(coordinate)
    assert rec['center_id'] in range(900, 920) and rec['H'] in [1, 4] and rec['K'] in [10, 20]
    candidates = list(rec['candidates'].values())
    assert set(int(i) for i in rec['candidates']) == set(rec['feasible_indices'])
    assert len(candidates) == len(rec['feasible_indices']) and 57 in rec['feasible_indices']
    assert all(c['complete'] and math.isfinite(c['validation']['weighted_mse']) and math.isfinite(c['check']['weighted_mse']) for c in candidates)
    count += len(candidates)
    best_check = min(candidates, key=lambda x: (x['check']['weighted_mse'], x['params'], x['flops'], x['arch_idx']))
    best_val = min(candidates, key=lambda x: (x['validation']['weighted_mse'], x['params'], x['flops'], x['arch_idx']))
    summary = rec['summary']
    assert summary['c1_check_oracle']['arch_idx'] == best_check['arch_idx']
    assert summary['c1_validation_selected']['arch_idx'] == best_val['arch_idx']
    assert summary['pt_anchor_D1'] == ref['recipes']['D1']
    ptv = ref['recipes']['D1']['validation']['weighted_mse']
    ptc = ref['recipes']['D1']['check']['weighted_mse']
    union_is_c1 = best_val['validation']['weighted_mse'] < ptv
    val_index = best_val['arch_idx'] if union_is_c1 else 57
    val_check = best_val['check']['weighted_mse'] if union_is_c1 else ptc
    assert summary['union_validation_selected_source'] == ('C1_ARCH_CANDIDATE' if union_is_c1 else 'PT_A57_ANCHOR')
    assert summary['union_validation_selected_arch_idx'] == val_index
    assert summary['union_validation_selected_check_mse'] == val_check
    oracle_win = best_check['check']['weighted_mse'] < ptc
    val_win = union_is_c1 and val_check < ptc
    if oracle_win: oracle_wins[best_check['arch_idx']] += 1
    if val_win: val_wins[val_index] += 1
    cases.append({'case_key': key, 'center_id': rec['center_id'], 'H': rec['H'], 'K': rec['K'], 'feasible_count': len(candidates), 'check_winner': best_check['arch_idx'], 'check_winner_positive': int(oracle_win), 'validation_selection': val_index, 'validation_selected_source': summary['union_validation_selected_source'], 'validation_selection_positive': int(val_win)})
assert count == 3528 and len(coordinates) == 80
expected = {1:(1,2), 6:(2,1), 13:(2,1), 55:(3,2), 56:(2,0), 57:(6,7)}
assert {i:(oracle_wins[i],val_wins[i]) for i in expected} == expected
retained = sorted(i for i in range(66) if oracle_wins[i] >= 2 or val_wins[i] >= 2)
assert retained == [1,6,13,55,56,57]

release_asset = None
if len(sys.argv) > 1:
    release_asset = Path(sys.argv[1])
    assert sha(release_asset) == '88c001ce4274e41694eac7700d1af40688f24523f9b3c5acd5ca3e9c540aa27b'
    with zipfile.ZipFile(release_asset) as z:
        manifest = json.loads(z.read('preselection_initializations/MANIFEST.json'))
        for item in manifest:
            h = hashlib.sha256()
            with z.open('preselection_initializations/' + item['path']) as f:
                for block in iter(lambda: f.read(1024 * 1024), b''): h.update(block)
            assert h.hexdigest() == item['sha256'], item['path']
        assert next(i['sha256'] for i in manifest if i['path'] == 'c1_preselection_bank.pt') == bank_hash
        for h in [1,4]:
            actual = next(i['sha256'] for i in manifest if i['path'] == f'pt_A57_H{h}.pt')
            assert actual == source['assets'][f'pt_ft_h{h}_btight']['sha256']

result = {'status':'PASS', 'cases':len(cases), 'candidate_records':count, 'retained_architectures':retained, 'paper_counts':{str(i):{'check_oracle_wins':oracle_wins[i], 'validation_selected_positive_wins':val_wins[i]} for i in expected}, 'original_archive_hashes':{n:sha(ROOT/n) for n in ['c30_preflight.json','c30_fixed_anchor.json','c30_c1_oracle.json','c30_analysis.json','c30_audit.json','source_assets_manifest.json']}, 'published_weight_bundle_verified':release_asset is not None, 'scope':'independent recalculation of historical saved scores, not model retraining or independent blind evaluation'}
print(json.dumps(result, ensure_ascii=False, indent=2))
