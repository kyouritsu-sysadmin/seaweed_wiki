# SeaweedFS Wiki — Docusaurus Documentation Site

A clean, modern, and high-performance documentation site for **SeaweedFS**, built with **Docusaurus v3** and ready for self-hosting on **GitHub Pages**.

![SeaweedFS Wiki Preview](./static/img/SeaweedFS_Architecture.png)

---

## 🌟 Key Features

- **Complete Wiki Migration**: 185+ documentation pages converted, indexed, and organized.
- **Hierarchical Navigation**: 23 categories faithfully mapped from SeaweedFS `_Sidebar.md` with collapsible sections and intuitive icons.
- **Offline Full-Text Search**: Powered by `@easyops-cn/docusaurus-search-local` — instant search with autocomplete and zero external dependencies.
- **Oceanic Theme & Dark Mode**: Tailored modern design with glassmorphism navbar, responsive layout, and seamless light/dark mode.
- **Automated Upstream Sync**: Single command (`npm run sync-wiki`) converts wikilinks `[[...]]`, handles images and PDFs, escapes MDX constructs, and auto-generates `sidebars.ts`.
- **Turnkey GitHub Pages Deployment**: GitHub Actions workflow included (`.github/workflows/deploy.yml`) for automated CI/CD builds on push.

---

## 🚀 Quick Start (Local Development)

### 1. Install Dependencies
```bash
npm install
```

### 2. Start the Local Dev Server
```bash
npm start
```
Open [http://localhost:3000](http://localhost:3000) in your browser. Live reloading is enabled.

### 3. Build Static Site for Production
```bash
npm run build
```
The static HTML, JavaScript, and assets are output into the `build/` directory.

### 4. Test Production Build Locally
```bash
npm run serve
```

---

## 🌐 Deploying to GitHub Pages

### Method 1: Automatic Deployment via GitHub Actions (Recommended)

1. Push this repository to your GitHub account (e.g. `https://github.com/<your-username>/seaweed_wiki`).
2. In your GitHub repository:
   - Navigate to **Settings** → **Pages**.
   - Under **Build and deployment** → **Source**, select **GitHub Actions**.
3. Push to `main` or `master`. The workflow in [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml) will automatically build the site and deploy it to:
   ```
   https://<your-username>.github.io/<repo-name>/
   ```

> **Note on Base URL**:
> If deploying to a project page (e.g. `/<repo-name>/`), the workflow automatically sets `BASE_URL=/<repo-name>/`.
> If using a custom domain (e.g. `wiki.seaweedfs.com`), set `BASE_URL=/` in repository variables or `docusaurus.config.ts`.

### Method 2: Manual CLI Deployment
```bash
# For bash / zsh
GIT_USER=<your-github-username> USE_SSH=true npm run deploy
```

---

## 🔄 Updating & Syncing the Wiki

To update docs from the upstream SeaweedFS wiki:

1. Update the wiki source files in `seaweedfs.wiki/`:
   ```bash
   cd seaweedfs.wiki && git pull origin master && cd ..
   ```
2. Run the sync script:
   ```bash
   npm run sync-wiki
   ```
3. Test and build:
   ```bash
   npm run build
   ```

The script ([`scripts/sync-wiki.py`](scripts/sync-wiki.py)) will:
- Parse `_Sidebar.md` and rebuild `sidebars.ts` with clean icons and hierarchy.
- Convert GitHub wikilinks (`[[Doc Name]]` and `[[Label|Doc Target]]`) into valid Docusaurus relative links.
- Copy and link diagrams, images, and whitepaper PDFs.
- Balance code blocks and escape MDX v3 characters outside code fences.

---

## 📁 Repository Structure

```
├── .github/workflows/
│   └── deploy.yml          # Automated GitHub Pages CI/CD workflow
├── docs/                   # Converted Docusaurus documentation markdown files
├── scripts/
│   └── sync-wiki.py        # Automated wiki parser, converter & sidebar generator
├── seaweedfs.wiki/         # Upstream SeaweedFS wiki git submodule/source
├── src/
│   ├── css/custom.css      # Oceanic theme tokens, fonts & styling
│   └── pages/index.tsx     # Homepage with interactive terminal & feature cards
├── static/
│   └── img/                # Architectural diagrams, icons, and PDF whitepaper
├── docusaurus.config.ts    # Docusaurus configuration (search, navbar, GitHub Pages)
├── package.json            # Scripts & dependencies
├── sidebars.ts             # Auto-generated 23-category sidebar configuration
└── tsconfig.json           # TypeScript configuration
```

---

## 📄 License & Attribution

SeaweedFS is created and maintained by Chris Lu and the SeaweedFS open source community.
Wiki documentation content is licensed under the Apache License 2.0.
