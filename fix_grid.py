import os
import re

modalities = {
    'AnalisePorPosicao-Lotomania-Only': '180px max-content',
    'AnalisePorPosicao-Quina-Only': '180px max-content',
    'AnalisePorPosicao-MegaSena-Only': '180px max-content',
    'AnalisePorPosicao-Lotofacil-Only': '180px max-content',
    'AnalisePorPosicao-Timemania-Only': '180px max-content 240px',
    'AnalisePorPosicao--DiaDeSorte-Only': '180px max-content 240px',
    'AnalisePorPosicao-MaisMilionaria-Only': '180px max-content 240px',
    'AnalisePorPosicao-DuplaSena-Only': '180px max-content max-content'
}

for d, grid_val in modalities.items():
    fp = os.path.join('d:/LoteriasPosicao', d, 'templates', 'index.html')
    if not os.path.exists(fp): continue
    
    with open(fp, 'r', encoding='utf-8') as f:
        content = f.read()

    # Step 1: Find the opening wrappers we injected last time
    # Last time we used: <div class="px-3 py-2 border-bottom d-flex justify-content-center">
    # followed by <div style="display:grid; grid-template-columns: 145px fit-content(100%) 1fr; gap: 1.25rem; align-items:center; width:100%; max-width:980px;">
    
    # Let's replace the whole block dynamically.
    def replace_grid(m):
        return f'<div class="px-3 py-3 border-bottom d-flex justify-content-center">\n                    <div style="display:grid; grid-template-columns: {grid_val}; gap: 1.5rem; align-items:center; justify-content:center;">'
    
    content = re.sub(
        r'<div class="px-3 py[\-\w]* border-bottom d-flex justify-content-center">\s*<div style="display:grid;.+?max-width:\s*\d+px;">',
        f'<div class="px-3 py-3 border-bottom d-flex justify-content-center">\n                    <div style="display:grid; grid-template-columns: {grid_val}; gap: 2rem; align-items:center;">',
        content,
        flags=re.DOTALL
    )

    with open(fp, 'w', encoding='utf-8') as f:
        f.write(content)
        
    print(f"Updated {d} with {grid_val}")
