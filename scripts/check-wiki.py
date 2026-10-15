import os
import re
import glob

wiki_dir = 'seaweedfs.wiki'
md_files = sorted(glob.glob(f'{wiki_dir}/*.md'))

def strip_code(text):
    # remove fenced code blocks (```...```)
    text = re.sub(r'```[\s\S]*?```', '', text)
    # remove inline code (`...`)
    text = re.sub(r'`[^`\n]*`', '', text)
    return text

jsx_like = []
curly_braces = []
html_comments = []

for mf in md_files:
    fname = os.path.basename(mf)
    with open(mf, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    stripped = strip_code(content)
    # Check for <something> not starting with http or mailto
    matches = re.findall(r'<([a-zA-Z_0-9\-:\s]+)>', stripped)
    for m in matches:
        if not m.startswith('http') and not m.startswith('mailto') and m not in ['b', 'i', 'p', 'br', 'hr', 'strong', 'em', 'span', 'div', 'code', 'pre']:
            jsx_like.append((fname, m))
    # Check for {something}
    curlies = re.findall(r'(\{[^{}\n]+\})', stripped)
    for c in curlies:
        curly_braces.append((fname, c))
    # Check for HTML comments
    comments = re.findall(r'(<!--[\s\S]*?-->)', stripped)
    for comm in comments:
        html_comments.append((fname, comm))

print(f"Total MD files: {len(md_files)}")
print(f"Found {len(jsx_like)} potential JSX-like tags outside code blocks")
if jsx_like:
    print("Sample JSX-like tags:")
    for fn, tag in jsx_like[:10]:
        print(f"  {fn}: <{tag}>")

print(f"Found {len(curly_braces)} curly braces outside code blocks")
if curly_braces:
    print("Sample curlies:")
    for fn, c in curly_braces[:10]:
        print(f"  {fn}: {c}")

print(f"Found {len(html_comments)} HTML comments outside code blocks")
if html_comments:
    print("Sample comments:")
    for fn, c in html_comments[:5]:
        print(f"  {fn}: {c[:40]}")
