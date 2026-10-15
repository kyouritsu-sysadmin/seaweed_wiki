#!/usr/bin/env python3
import os
import re
import glob
import shutil

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WIKI_DIR = os.path.join(REPO_ROOT, 'seaweedfs.wiki')
DOCS_DIR = os.path.join(REPO_ROOT, 'docs')
STATIC_IMG_DIR = os.path.join(REPO_ROOT, 'static', 'img')

# Docs that are hand-authored in docs/ and must NOT be overwritten by the wiki sync.
# These are custom guides that may share a filename with a wiki page.
PROTECTED_DOCS = {
    'Secure-On-Premise-Docker-Deployment.md',
}

# Known aliases mapping
ALIASES = {
    'erasure-coding': 'Erasure-Coding-for-warm-storage',
    'master-server': 'Master-Server-API',
    'volume-server': 'Volume-Server-API',
    'weed-admin': 'Admin-UI',
    's3-tables': 'S3-Table-Bucket',
    'add-new-filer-store': 'Customize-Filer-Store',
}

def norm_name(s):
    s = re.sub(r'[\s\-_‐]+', '-', s.strip()).lower()
    return s

def clean_title(name):
    # Convert hyphens/underscores to spaces for human-readable title
    name = os.path.splitext(name)[0]
    # Replace non-standard hyphens
    name = name.replace('‐', '-')
    title = name.replace('-', ' ').replace('_', ' ')
    # Clean up double spaces
    title = re.sub(r'\s+', ' ', title).strip()
    return title

def parse_sidebar_file(sidebar_path, all_md_map):
    with open(sidebar_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    categories = []
    current_cat = None
    current_subcat = None

    for line in lines:
        raw_line = line.rstrip()
        stripped = raw_line.strip()
        if not stripped:
            continue

        # Header 3: ### Category Name or ### [[Category Name]]
        if stripped.startswith('###'):
            cat_header = stripped.lstrip('#').strip()
            # If header is a wikilink like ### [[Filer Stores]]
            header_link_m = re.match(r'\[\[(.*?)\]\]', cat_header)
            target_doc = None
            if header_link_m:
                cat_text = header_link_m.group(1).strip()
                norm_cat = norm_name(cat_text)
                if norm_cat in all_md_map:
                    target_doc = all_md_map[norm_cat]
                elif norm_cat in ALIASES:
                    target_doc = ALIASES[norm_cat]
                cat_title = cat_text
            else:
                cat_title = cat_header

            current_cat = {
                'title': cat_title,
                'target_doc': target_doc,
                'items': []
            }
            categories.append(current_cat)
            current_subcat = None
            continue

        # Sub-item: 4 spaces or 2 spaces or tab indentation
        indent = len(raw_line) - len(raw_line.lstrip())
        link_m = re.search(r'\[\[(.*?)\]\]', stripped)
        if link_m and current_cat:
            link_text = link_m.group(1).strip()
            # Check for label|target or target|label
            target = link_text
            label = link_text
            if '|' in link_text:
                parts = link_text.split('|', 1)
                p1, p2 = parts[0].strip(), parts[1].strip()
                if norm_name(p2) in all_md_map or norm_name(p2) in ALIASES:
                    label, target = p1, p2
                elif norm_name(p1) in all_md_map or norm_name(p1) in ALIASES:
                    target, label = p1, p2
                else:
                    label, target = p1, p2

            norm_t = norm_name(target.split('#')[0])
            doc_file = None
            if norm_t in all_md_map:
                doc_file = all_md_map[norm_t]
            elif norm_t in ALIASES:
                doc_file = ALIASES[norm_t]
            else:
                print(f"Warning: Sidebar link '{link_text}' not resolved to file")
                continue

            item = {
                'label': label,
                'doc_file': doc_file,
                'is_sub': indent >= 2
            }

            if indent >= 2 and len(current_cat['items']) > 0:
                last_item = current_cat['items'][-1]
                if isinstance(last_item, dict) and 'sub_items' in last_item:
                    last_item['sub_items'].append(item)
                else:
                    # Upgrade last item to have sub_items
                    last_item['sub_items'] = [item]
            else:
                current_cat['items'].append(item)

    return categories

def escape_mdx_content(text):
    # Pre-clean known wiki formatting errors:
    # 1. Hadoop-Compatible-File-System.md broken fence around header
    text = re.sub(
        r'```\s*\n# Deploy the SeaweedFS HDFS client jar\s*\n```',
        '### Deploy the SeaweedFS HDFS client jar\n\n```bash',
        text
    )

    # 2. Check if code fences are balanced
    fences = len(re.findall(r'^```', text, flags=re.MULTILINE))
    if fences % 2 != 0:
        text = text + "\n```\n"

    # Split text into fenced code blocks and non-code prose
    # We only protect fenced code blocks so inline links with backticks like [`weed master`](...) can be processed
    tokens = []
    code_pattern = re.compile(r'(```[\s\S]*?```)')
    last_idx = 0

    for m in code_pattern.finditer(text):
        non_code = text[last_idx:m.start()]
        tokens.append(('prose', non_code))
        tokens.append(('code', m.group(0)))
        last_idx = m.end()
    tokens.append(('prose', text[last_idx:]))

    allowed_tag_pattern = re.compile(
        r'^/?(?:a|b|i|strong|em|p|span|div|code|pre|table|thead|tbody|tfoot|tr|th|td|ul|ol|li|details|summary|img|br|hr|sub|sup|blockquote|font)(?:[\s>/]|$)',
        re.IGNORECASE
    )

    out_chunks = []
    for kind, val in tokens:
        if kind == 'code':
            out_chunks.append(val)
        else:
            p = val
            # Replace unescaped void tags
            p = re.sub(r'<br\s*>', '<br/>', p, flags=re.IGNORECASE)
            p = re.sub(r'<hr\s*>', '<hr/>', p, flags=re.IGNORECASE)

            # Match any < in prose and check if it's an allowed HTML tag or autolink
            def repl_tag(m):
                full_tag = m.group(0)
                inner = m.group(1).strip()
                if inner.startswith('http://') or inner.startswith('https://') or inner.startswith('mailto:'):
                    return full_tag
                if allowed_tag_pattern.match(inner):
                    return full_tag
                return '&lt;' + inner + '&gt;'

            p = re.sub(r'<([^<>\n]+)>', repl_tag, p)

            # Escape any lone or mathematical < (e.g. <=, <==, < 10, < val)
            def repl_lone_lt(m):
                after = m.group(1)
                if allowed_tag_pattern.match(after) or after.startswith('http://') or after.startswith('https://'):
                    return m.group(0)
                return '&lt;' + after

            p = re.sub(r'<([^\s<>\n]*)', repl_lone_lt, p)

            # Replace ${var} with &#36;&#123;var&#125; in prose so React does not evaluate it as JS
            p = re.sub(r'\$\{([^}]+)\}', r'&#36;&#123;\1&#125;', p)

            # Replace any other curly braces in prose outside backticks
            def repl_curlies(match):
                # Don't touch inline code
                s = match.group(0)
                if s.startswith('`') and s.endswith('`'):
                    return s
                return s.replace('{', '&#123;').replace('}', '&#125;')

            p = re.sub(r'(`[^`\n]*`|[^`]+)', repl_curlies, p)

            out_chunks.append(p)

    return ''.join(out_chunks)

def transform_links(text, all_md_map, current_file):
    # Convert wikilinks [[...]] and relative links
    # Only protect fenced code blocks so inline links like [`weed master`](...) stay in prose
    tokens = []
    code_pattern = re.compile(r'(```[\s\S]*?```)')
    last_idx = 0
    for m in code_pattern.finditer(text):
        tokens.append(('prose', text[last_idx:m.start()]))
        tokens.append(('code', m.group(0)))
        last_idx = m.end()
    tokens.append(('prose', text[last_idx:]))

    out_chunks = []
    for kind, val in tokens:
        if kind == 'code':
            out_chunks.append(val)
        else:
            p = val
            # Wikilink regex: [[...]]
            def repl_wikilink(m):
                raw = m.group(1).strip()
                if not raw:
                    return ''
                target = raw
                label = raw
                if '|' in raw:
                    parts = raw.split('|', 1)
                    p1, p2 = parts[0].strip(), parts[1].strip()
                    if p2.startswith('http://') or p2.startswith('https://'):
                        return f'[{p1}]({p2})'
                    if p1.startswith('http://') or p1.startswith('https://'):
                        return f'[{p2}]({p1})'
                    if norm_name(p2) in all_md_map or norm_name(p2) in ALIASES:
                        label, target = p1, p2
                    elif norm_name(p1) in all_md_map or norm_name(p1) in ALIASES:
                        target, label = p1, p2
                    else:
                        label, target = p1, p2

                anchor = ''
                if '#' in target:
                    target_page, anchor = target.split('#', 1)
                    anchor = '#' + anchor
                else:
                    target_page = target

                norm_t = norm_name(target_page)
                resolved_file = None
                if norm_t in all_md_map:
                    resolved_file = all_md_map[norm_t]
                elif norm_t in ALIASES:
                    resolved_file = ALIASES[norm_t]

                if resolved_file:
                    target_filename = resolved_file if resolved_file.endswith('.md') else f"{resolved_file}.md"
                    return f'[{label}](./{target_filename}{anchor})'
                else:
                    return f'**{label}**'

            p = re.sub(r'\[\[(.*?)\]\]', repl_wikilink, p)

            # Fix relative markdown links: [text](Doc-Name) -> [text](./Doc-Name.md)
            def repl_mdlink(m):
                link_text = m.group(1)
                target_url = m.group(2).strip()

                if target_url.startswith('http://') or target_url.startswith('https://') or target_url.startswith('#') or target_url.startswith('mailto:'):
                    return m.group(0)

                # Images and PDF assets
                if target_url.endswith('.png') or target_url.endswith('.jpg') or target_url.endswith('.svg') or target_url.endswith('.pdf'):
                    base_asset = os.path.basename(target_url)
                    return f'[{link_text}](./{base_asset})'

                anchor = ''
                target_base = target_url
                if '#' in target_base:
                    target_base, anchor = target_base.split('#', 1)
                    anchor = '#' + anchor

                if target_base.endswith('.md'):
                    target_base = target_base[:-3]

                norm_b = norm_name(target_base)
                resolved = None
                if norm_b in all_md_map:
                    resolved = all_md_map[norm_b]
                elif norm_b in ALIASES:
                    resolved = ALIASES[norm_b]

                if resolved:
                    resolved_fn = resolved if resolved.endswith('.md') else f"{resolved}.md"
                    return f'[{link_text}](./{resolved_fn}{anchor})'

                return m.group(0)

            p = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', repl_mdlink, p)
            out_chunks.append(p)

    return ''.join(out_chunks)


def main():
    print(f"Syncing wiki from: {WIKI_DIR}")
    print(f"Target docs dir: {DOCS_DIR}")

    # Ensure directories exist
    os.makedirs(DOCS_DIR, exist_ok=True)
    os.makedirs(STATIC_IMG_DIR, exist_ok=True)

    # 1. Collect all MD files from wiki
    all_raw_files = os.listdir(WIKI_DIR)
    md_files = [f for f in all_raw_files if f.endswith('.md')]
    asset_files = [f for f in all_raw_files if f.endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg', '.pdf', '.txt'))]

    print(f"Found {len(md_files)} markdown files and {len(asset_files)} asset files.")

    # Copy assets to static/img and docs/
    for a in asset_files:
        src = os.path.join(WIKI_DIR, a)
        shutil.copy2(src, os.path.join(STATIC_IMG_DIR, a))
        shutil.copy2(src, os.path.join(DOCS_DIR, a))
    print(f"Assets copied to {STATIC_IMG_DIR} and {DOCS_DIR}.")

    # Build lookup map: norm_name(base) -> actual filename without .md
    all_md_map = {}
    for f in md_files:
        base = os.path.splitext(f)[0]
        all_md_map[norm_name(base)] = base

    # 2. Parse _Sidebar.md
    sidebar_path = os.path.join(WIKI_DIR, '_Sidebar.md')
    categories = parse_sidebar_file(sidebar_path, all_md_map)

    # 3. Process every MD file
    processed_count = 0
    in_sidebar_docs = set()
    for cat in categories:
        if cat.get('target_doc'):
            in_sidebar_docs.add(cat['target_doc'])
        for item in cat['items']:
            in_sidebar_docs.add(item['doc_file'])
            if 'sub_items' in item:
                for sub in item['sub_items']:
                    in_sidebar_docs.add(sub['doc_file'])

    for mf in md_files:
        if mf == '_Sidebar.md':
            continue

        # Skip protected custom docs - do not overwrite hand-authored guides
        if mf in PROTECTED_DOCS:
            print(f"Skipping protected doc: {mf}")
            continue

        base_name = os.path.splitext(mf)[0]
        # Clean doc ID
        doc_id = base_name

        src_path = os.path.join(WIKI_DIR, mf)
        with open(src_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Is this the home page?
        is_home = (mf == 'Home.md')
        out_filename = 'index.md' if is_home else mf
        dest_path = os.path.join(DOCS_DIR, out_filename)

        title = "SeaweedFS Wiki" if is_home else clean_title(base_name)
        sidebar_label = "Welcome" if is_home else clean_title(base_name)

        # Escape MDX problematic constructs outside code blocks
        content = escape_mdx_content(content)
        # Transform wikilinks and markdown links
        content = transform_links(content, all_md_map, mf)

        # Prepend YAML frontmatter
        frontmatter = [
            "---",
            f"id: {out_filename[:-3] if not is_home else 'index'}",
            f"title: \"{title}\"",
            f"sidebar_label: \"{sidebar_label}\"",
        ]
        if is_home:
            frontmatter.append("slug: /")
        frontmatter.append("---\n\n")

        full_content = "\n".join(frontmatter) + content

        with open(dest_path, 'w', encoding='utf-8') as f:
            f.write(full_content)
        processed_count += 1

    print(f"Processed and wrote {processed_count} docs into {DOCS_DIR}.")

    # 4. Generate sidebars.ts
    # Category icons / styling mapping
    cat_icons = {
        'Introduction': '🚀 Introduction',
        'API': '🔌 API Reference',
        'Configuration': '⚙️ Configuration',
        'Filer': '📁 Filer',
        'Filer Stores': '💾 Filer Stores',
        'Management': '🎛️ Management & Admin',
        'Advanced Filer Configurations': '🔧 Advanced Filer Configurations',
        'FUSE Mount': '🖥️ FUSE Mount',
        'WebDAV': '🌐 WebDAV',
        'SFTP Server': '🔒 SFTP Server',
        'Cloud Drive': '☁️ Cloud Drive',
        'AWS S3 API': '🪣 AWS S3 API',
        'S3 Table Bucket': '📊 S3 Table Bucket & Lakehouse',
        'Iceberg Integrations': '🧊 Apache Iceberg Integrations',
        'Lance Integrations': '⚡ Lance Integrations',
        'S3 Authentication & IAM': '🔐 S3 Authentication & IAM',
        'Server-Side Encryption': '🛡️ Server-Side Encryption',
        'S3 Client Tools': '🛠️ S3 Client Tools',
        'Machine Learning': '🤖 Machine Learning',
        'HDFS': '🐘 HDFS & Big Data',
        'Replication and Backup': '🔄 Replication & Backup',
        'Metadata Change Events': '📡 Metadata Change Events',
        'Messaging': '📨 Messaging & SMQ',
        'Use Cases': '💡 Use Cases',
        'Operations': '🚢 Operations & Deployment',
        'Rust Volume Server': '🦀 Rust Volume Server',
        'Advanced': '⚡ Advanced & Optimization',
        'Security': '🔒 Security & FIPS',
        'Misc Use Case Examples': '📦 Examples & Benchmarks',
    }

    # Identify orphans (files not in _Sidebar.md)
    orphan_map = {
        'Benchmark-SeaweedFS-as-a-GlusterFS-replacement': 'Misc Use Case Examples',
        'Benchmarks-from-jinleileiking': 'Introduction',
        'Error-reporting-to-sentry': 'Configuration',
        'Hobbyest-Tinkerer-scale-on-premises-tutorial': 'Use Cases',
        'Migrate-Maintenance-Scripts-to-Admin-Script-Plugin': 'Management',
        'SeaweedFS-Architecture': 'Introduction',
    }

    sidebar_lines = [
        "import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';",
        "",
        "/**",
        " * SeaweedFS Wiki Sidebar Configuration",
        " * Generated from seaweedfs.wiki/_Sidebar.md",
        " */",
        "const sidebars: SidebarsConfig = {",
        "  wikiSidebar: [",
        "    {",
        "      type: 'doc',",
        "      id: 'index',",
        "      label: '🏠 Welcome to Wiki',",
        "    },",
        "    {",
        "      type: 'doc',",
        "      id: 'Secure-On-Premise-Docker-Deployment',",
        "      label: '🛡️ Secure On-Premise Docker Guide',",
        "    },",
    ]

    for cat in categories:
        cat_title = cat['title']
        display_label = cat_icons.get(cat_title, cat_title)
        is_intro = (cat_title == 'Introduction')
        sidebar_lines.append("    {")
        sidebar_lines.append("      type: 'category',")
        sidebar_lines.append(f"      label: {repr(display_label)},")
        sidebar_lines.append(f"      collapsible: true,")
        sidebar_lines.append(f"      collapsed: {'false' if is_intro else 'true'},")

        if cat.get('target_doc'):
            # If the category itself is a doc (like ### [[Filer Stores]])
            sidebar_lines.append("      link: {")
            sidebar_lines.append("        type: 'doc',")
            sidebar_lines.append(f"        id: {repr(cat['target_doc'])},")
            sidebar_lines.append("      },")

        sidebar_lines.append("      items: [")

        # Collect items
        for item in cat['items']:
            doc_id = item['doc_file']
            if 'sub_items' in item and item['sub_items']:
                # Nested category
                sub_label = clean_title(doc_id)
                sidebar_lines.append("        {")
                sidebar_lines.append("          type: 'category',")
                sidebar_lines.append(f"          label: {repr(sub_label)},")
                sidebar_lines.append("          collapsible: true,")
                sidebar_lines.append("          collapsed: true,")
                sidebar_lines.append("          link: {")
                sidebar_lines.append("            type: 'doc',")
                sidebar_lines.append(f"            id: {repr(doc_id)},")
                sidebar_lines.append("          },")
                sidebar_lines.append("          items: [")
                for sub in item['sub_items']:
                    sidebar_lines.append(f"            {repr(sub['doc_file'])},")
                sidebar_lines.append("          ],")
                sidebar_lines.append("        },")
            else:
                sidebar_lines.append(f"        {repr(doc_id)},")

        # Add orphans belonging to this category
        for orph_id, orph_cat in orphan_map.items():
            if orph_cat == cat_title:
                sidebar_lines.append(f"        {repr(orph_id)},")

        sidebar_lines.append("      ],")
        sidebar_lines.append("    },")

    sidebar_lines.append("  ],")
    sidebar_lines.append("};")
    sidebar_lines.append("")
    sidebar_lines.append("export default sidebars;")
    sidebar_lines.append("")

    sidebars_ts_path = os.path.join(REPO_ROOT, 'sidebars.ts')
    with open(sidebars_ts_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(sidebar_lines))

    print(f"Wrote generated sidebar config to {sidebars_ts_path}.")

if __name__ == '__main__':
    main()
