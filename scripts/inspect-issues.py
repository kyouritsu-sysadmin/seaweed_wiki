import glob, re, os

wiki_dir = 'seaweedfs.wiki'
files = sorted(glob.glob(f'{wiki_dir}/*.md'))

for f in files:
    fname = os.path.basename(f)
    with open(f, 'r', encoding='utf-8', errors='ignore') as fp:
        lines = fp.readlines()

    # Check fenced blocks
    fence_count = 0
    for idx, l in enumerate(lines):
        if l.strip().startswith('```'):
            fence_count += 1
    if fence_count % 2 != 0:
        print(f"ODD FENCE COUNT in {fname}: {fence_count}")

    content = ''.join(lines)
    # Check for links with backticks
    links_with_code = re.findall(r'\[`[^`]+`\]\([^)]+\)', content)
    if links_with_code:
        print(f"Links with code in {fname}: {links_with_code}")

    # Check for empty code blocks or weird patterns like ```\n# ...\n```
    weird_blocks = re.findall(r'```\s*\n\s*#[^\n]+\n\s*```', content)
    if weird_blocks:
        print(f"Weird blocks in {fname}: {weird_blocks}")
