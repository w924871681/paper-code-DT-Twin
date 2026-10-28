"""Check paper-model hashes and the saved-code provenance manifest."""
from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parent
entries=json.loads((root/'MANIFEST.json').read_text(encoding='utf8'))
for e in entries:
    path=root/e['path']
    assert path.is_file(), str(path)
    assert hashlib.sha256(path.read_bytes()).hexdigest()==e['sha256'], str(path)
paper=json.loads((root.parent/'data/source_checkpoint_identities.json').read_text(encoding='utf8'))
for item in paper['checkpoints']:
    path=root/'checkpoints'/f"{item['token']}_H{item['H']}.pt"
    assert hashlib.sha256(path.read_bytes()).hexdigest()==item['sha256'], str(path)
print(f"PASS: {len(entries)} archived files and {len(paper['checkpoints'])} paper-model checkpoints")
