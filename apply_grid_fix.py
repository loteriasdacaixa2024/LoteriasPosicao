import os
import re

for d in os.listdir('d:/LoteriasPosicao'):
    if not ('AnalisePorPosicao-' in d and 'Central' not in d): continue
    
    fp = os.path.join('d:/LoteriasPosicao', d, 'templates', 'index.html')
    if not os.path.exists(fp): continue
    
    with open(fp, 'r', encoding='utf-8') as f:
        content = f.read()

    target = '<div class="px-3 py-3 border-bottom d-flex align-items-center justify-content-center gap-4 flex-wrap">'
    if target in content:
        new_outer = '''<div class="px-3 py-2 border-bottom d-flex justify-content-center">
                    <div style="display:grid; grid-template-columns: 130px fit-content(100%) 1fr; gap: 1.25rem; align-items:center; width:100%; max-width:980px;">'''
        
        content = content.replace(target, new_outer)
        
        # Add a closing div at the end of the template literal inside the JS loop
        content = re.sub(r'(</div>\s*`;\s*\}\);)', r'</div>\1', content)
        
        target_bold = '<div class="fw-bold" style="color:var(--primary); white-space:nowrap;">'
        new_bold = '<div class="fw-bold text-end" style="color:var(--primary); white-space:nowrap;">'
        content = content.replace(target_bold, new_bold)
        
        with open(fp, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'Updated {d}')
