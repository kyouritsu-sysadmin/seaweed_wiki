import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

const config: Config = {
  title: 'SeaweedFS Wiki',
  tagline: 'Fast, Distributed Object Store, Filer & Data Lakehouse',
  favicon: 'img/favicon.ico',

  // GitHub Pages deployment config
  url: process.env.URL || 'https://seaweedfs.github.io',
  baseUrl: process.env.BASE_URL || '/',
  organizationName: process.env.GITHUB_USER || 'seaweedfs',
  projectName: process.env.GITHUB_REPO || 'seaweed_wiki',
  trailingSlash: false,

  onBrokenLinks: 'warn',
  onBrokenAnchors: 'warn',
  onDuplicateRoutes: 'warn',

  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  presets: [
    [
      'classic',
      {
        docs: {
          sidebarPath: './sidebars.ts',
          routeBasePath: '/docs',
          editUrl: 'https://github.com/seaweedfs/seaweedfs/wiki',
        },
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
      } satisfies Preset.Options,
    ],
  ],

  plugins: [
    [
      require.resolve('@easyops-cn/docusaurus-search-local'),
      {
        hashed: true,
        language: ['en'],
        indexDocs: true,
        indexBlog: false,
        indexPages: true,
        docsRouteBasePath: '/docs',
      },
    ],
  ],

  themeConfig: {
    image: 'img/SeaweedFS_Architecture.png',
    colorMode: {
      defaultMode: 'dark',
      respectPrefersColorScheme: true,
    },
    navbar: {
      title: 'SeaweedFS Wiki',
      logo: {
        alt: 'SeaweedFS Logo',
        src: 'img/logo.svg',
      },
      items: [
        {
          type: 'docSidebar',
          sidebarId: 'wikiSidebar',
          position: 'left',
          label: 'Documentation',
        },
        {
          to: '/docs/Blob-Store-Architecture',
          label: 'Architecture',
          position: 'left',
        },
        {
          to: '/docs/Amazon-S3-API',
          label: 'S3 API',
          position: 'left',
        },
        {
          to: '/docs/Filer-Setup',
          label: 'Filer',
          position: 'left',
        },
        {
          to: '/docs/Deployment-with-seaweed-up',
          label: 'Operations',
          position: 'left',
        },
        {
          href: 'https://github.com/seaweedfs/seaweedfs',
          label: 'GitHub',
          position: 'right',
        },
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: 'Getting Started',
          items: [
            {
              label: 'Welcome & Overview',
              to: '/docs/',
            },
            {
              label: 'Quick Start with weed mini',
              to: '/docs/Quick-Start-with-weed-mini',
            },
            {
              label: 'Simplest S3 Bucket Setup',
              to: '/docs/Simplest-S3-Bucket-and-User-Setup',
            },
            {
              label: 'Production Setup',
              to: '/docs/Production-Setup',
            },
          ],
        },
        {
          title: 'Core Systems',
          items: [
            {
              label: 'Blob Store Architecture',
              to: '/docs/Blob-Store-Architecture',
            },
            {
              label: 'Filer Architecture',
              to: '/docs/Filer-Setup',
            },
            {
              label: 'FUSE Mount',
              to: '/docs/FUSE-Mount',
            },
            {
              label: 'S3 Table Bucket & Iceberg',
              to: '/docs/S3-Table-Bucket',
            },
          ],
        },
        {
          title: 'Community & Resources',
          items: [
            {
              label: 'SeaweedFS GitHub',
              href: 'https://github.com/seaweedfs/seaweedfs',
            },
            {
              label: 'Original GitHub Wiki',
              href: 'https://github.com/seaweedfs/seaweedfs/wiki',
            },
            {
              label: 'Architecture White Paper (PDF)',
              href: 'https://raw.githubusercontent.com/seaweedfs/seaweedfs/master/note/SeaweedFS_Architecture.pdf',
            },
          ],
        },
      ],
      copyright: `Copyright © ${new Date().getFullYear()} SeaweedFS Wiki Documentation. Built with Docusaurus.`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
      additionalLanguages: ['bash', 'yaml', 'toml', 'json', 'docker', 'sql', 'python', 'go'],
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
