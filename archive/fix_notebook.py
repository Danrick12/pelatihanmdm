#!/usr/bin/env python3
"""Fix remaining import issues in MDM_Kelompok5_DJBC.ipynb"""
import json, os

NB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       'notebooks', 'MDM_Kelompok5_DJBC.ipynb')

with open(NB_PATH, 'r') as f:
    nb = json.load(f)

for i, c in enumerate(nb['cells']):
    if c['cell_type'] != 'code':
        continue
    src = ''.join(c['source'])
    changed = False
    
    # Fix all "from Source." imports - comment them out
    lines = src.split('\n')
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('from Source.') or stripped.startswith('import Source.'):
            if not stripped.startswith('#'):
                new_lines.append('# ' + line)
                changed = True
                print(f'Cell {i+1}: Commented out: {stripped[:70]}')
                continue
        new_lines.append(line)
    
    # Fix if __name__ == "__main__": -> remove but keep inner code
    src = '\n'.join(new_lines)
    if 'if __name__ == "__main__":' in src:
        src = src.replace('if __name__ == "__main__":', '# Running simulation...')
        changed = True
        print(f'Cell {i+1}: Fixed __main__ block')
    
    if changed:
        nb['cells'][i]['source'] = [src]

with open(NB_PATH, 'w') as f:
    json.dump(nb, f, indent=2, ensure_ascii=False)

print('\nAll fixes applied successfully!')
