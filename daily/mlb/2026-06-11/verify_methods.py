import hashlib, re

models = ['kimi','chatgpt','opus','gemini','deepseek','qwen','sonnet','grok','fable']
layer_b = {}
method  = {}

for m in models:
    text = open(f'system_{m}.md', encoding='utf-8').read()
    if 'MODEL-SPECIFIC INSTRUCTION' in text:
        idx = text.index('MODEL-SPECIFIC INSTRUCTION')
        layer_b[m] = text[:idx].strip()
        method[m]  = text[idx:].strip()
    else:
        layer_b[m] = text.strip()
        method[m]  = None

# Strip per-model comment line before comparing Layer B
def strip_model_line(s):
    return re.sub(r'^# Model: \S+\n', '', s, flags=re.MULTILINE)

hashes_lb = {m: hashlib.md5(strip_model_line(layer_b[m]).encode()).hexdigest() for m in models}
unique_lb = set(hashes_lb.values())
print('=== LAYER B (model-name comment stripped) ===')
if len(unique_lb) == 1:
    print(f'All 9 byte-identical. Hash: {list(unique_lb)[0]}')
else:
    print('MISMATCH:')
    for m, h in hashes_lb.items():
        print(f'  {m}: {h}')

print()
print('=== METHOD APPEND ===')
for m in models:
    present = method[m] is not None
    status  = 'present' if present else 'MISSING'
    h = hashlib.md5(method[m].encode()).hexdigest() if present else 'MISSING'
    print(f'  {m}: {status} | {h}')

print()
print('=== DUPLICATE METHOD CHECK ===')
hashes_m = [(m, hashlib.md5(method[m].encode()).hexdigest()) for m in models if method[m]]
seen = {}
for m, h in hashes_m:
    seen.setdefault(h, []).append(m)
dupes = {h: ms for h, ms in seen.items() if len(ms) > 1}
if dupes:
    for h, ms in dupes.items():
        print(f'  DUPE: {ms} share hash {h}')
else:
    print('  No duplicates -- all 9 method appends are unique.')

print()
print('=== FILE SIZES ===')
import os
for m in models:
    size = os.path.getsize(f'system_{m}.md')
    print(f'  system_{m}.md: {size:,} bytes')
