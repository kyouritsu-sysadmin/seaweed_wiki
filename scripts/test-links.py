import os
import re
import glob

wiki_dir = 'seaweedfs.wiki'
md_files = sorted(glob.glob(f'{wiki_dir}/*.md'))

all_pages = {os.path.splitext(os.path.basename(f))[0]: f for f in md_files}
# normalized lookup: lowercase, replace spaces/hyphens
def norm(s):
    return re.sub(r'[\s\-_‐]+', '-', s.strip()).lower()

page_map = {norm(p): p for p in all_pages}

wikilink_pattern = re.compile(r'\[\[(.*?)\]\]')

unresolved = []
resolved_count = 0

for mf in md_files:
    fname = os.path.basename(mf)
    with open(mf, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Ignore code blocks
    stripped = re.sub(r'```[\s\S]*?```', '', content)
    stripped = re.sub(r'`[^`\n]*`', '', stripped)
    
    for m in wikilink_pattern.finditer(stripped):
        raw = m.group(1).strip()
        # Parse label and target
        # In GitHub wiki:
        # [[Target]] or [[Label|Target]] or [[Target|Label]]?
        # Let's test which is which
        target = raw
        label = raw
        anchor = ''
        if '|' in raw:
            parts = raw.split('|', 1)
            p1, p2 = parts[0].strip(), parts[1].strip()
            # Let's see which part matches a known page
            p1_page = p1.split('#')[0]
            p2_page = p2.split('#')[0]
            if norm(p2_page) in page_map:
                # [[Label|Target]]
                label = p1
                target = p2
            elif norm(p1_page) in page_map:
                # [[Target|Label]]
                target = p1
                label = p2
            else:
                target = p1
                label = p2
        
        if '#' in target:
            target_page, anchor = target.split('#', 1)
        else:
            target_page = target
            
        t_norm = norm(target_page)
        if t_norm in page_map:
            resolved_count += 1
        else:
            unresolved.append((fname, raw, target_page))

print(f"Total resolved wikilinks: {resolved_count}")
print(f"Total unresolved wikilinks: {len(unresolved)}")
for src, raw, tp in unresolved[:20]:
    print(f"  In {src}: [[{raw}]] -> target: '{tp}'")
