import React, {useState} from 'react';
import type {ReactNode} from 'react';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import Heading from '@theme/Heading';
import styles from './index.module.css';

const COMMANDS = [
  {
    id: 'secure-docker',
    label: 'Secure Docker',
    comment: '# Start full hardened SeaweedFS cluster with gRPC mTLS, JWT & Nginx SSL:',
    cmd: 'docker compose -f docker-compose.yml up -d',
  },
  {
    id: 'mini',
    label: 'weed mini',
    comment: '# Spin up an all-in-one Master, Volume Server, Filer, and S3 gateway in 1 second:',
    cmd: 'weed mini -dir=/data -s3',
  },
  {
    id: 'docker',
    label: 'Docker Run',
    comment: '# Run SeaweedFS S3 server instantly in Docker:',
    cmd: 'docker run -p 8333:8333 -p 9333:9333 -p 8888:8888 chrislusf/seaweedfs server -s3',
  },
  {
    id: 's3',
    label: 'AWS CLI Test',
    comment: '# Interact using standard AWS S3 CLI:',
    cmd: 'aws --endpoint-url https://localhost:443 --no-verify-ssl s3 ls',
  },
  {
    id: 'mount',
    label: 'FUSE Mount',
    comment: '# Mount your remote SeaweedFS filesystem locally:',
    cmd: 'weed mount -filer=localhost:8888 -dir=/mnt/seaweedfs',
  },
];

const FEATURES = [
  {
    icon: '🛡️',
    title: 'Secure On-Premise Docker',
    description: 'Complete production blueprint with gRPC mutual TLS (mTLS), JWT authorization, Nginx reverse proxy, and zero unauthenticated access.',
    link: '/docs/Secure-On-Premise-Docker-Deployment',
  },
  {
    icon: '⚡',
    title: 'O(1) Blob Storage',
    description: 'Constant-time disk seeks regardless of dataset size. Highly scalable volume servers, cold-data cloud tiering, and active-active replication.',
    link: '/docs/Blob-Store-Architecture',
  },
  {
    icon: '📂',
    title: 'High-Performance Filer',
    description: 'POSIX-like hierarchical filesystem with swappable metadata stores including Redis, Cassandra, PostgreSQL, MySQL, and LevelDB.',
    link: '/docs/Filer-Setup',
  },
  {
    icon: '🪣',
    title: 'Amazon S3 Compatible API',
    description: 'Comprehensive AWS S3 API support with bucket policies, IAM, STS, CORS, multipart uploads, versioning, and retention lock.',
    link: '/docs/Amazon-S3-API',
  },
  {
    icon: '🧊',
    title: 'Iceberg & Lance Lakehouse',
    description: 'Integrated Iceberg REST catalog for Spark, Trino, DuckDB, Doris, and RisingWave to query tables directly with zero external metastore.',
    link: '/docs/S3-Table-Bucket',
  },
  {
    icon: '🖥️',
    title: 'FUSE Mount & Kubernetes',
    description: 'Mount remote SeaweedFS storage directly in user space on Linux, macOS, and Windows. Native CSI driver for Kubernetes PVs.',
    link: '/docs/FUSE-Mount',
  },
];

const QUICKLINKS = [
  {title: '🛡️ Secure On-Premise Docker Guide', to: '/docs/Secure-On-Premise-Docker-Deployment'},
  {title: '🚀 Quick Start with weed mini', to: '/docs/Quick-Start-with-weed-mini'},
  {title: '🪣 Simplest S3 Setup', to: '/docs/Simplest-S3-Bucket-and-User-Setup'},
  {title: '🔒 Security Configuration', to: '/docs/Security-Configuration'},
  {title: '🔌 Master Server API', to: '/docs/Master-Server-API'},
  {title: '🔌 Volume Server API', to: '/docs/Volume-Server-API'},
  {title: '🔌 Filer Server API', to: '/docs/Filer-Server-API'},
  {title: '💾 Choosing a Filer Store', to: '/docs/Choosing-a-Filer-Store'},
  {title: '🚢 Deployment with seaweed-up', to: '/docs/Deployment-with-seaweed-up'},
  {title: '☸️ Kubernetes & Minikube', to: '/docs/Deployment-to-Kubernetes-and-Minikube'},
  {title: '🐚 weed shell Reference', to: '/docs/weed-shell'},
  {title: '☁️ Cloud Drive & Tiering', to: '/docs/Cloud-Drive-Quick-Setup'},
];

function InteractiveTerminal() {
  const [activeTab, setActiveTab] = useState(0);
  const active = COMMANDS[activeTab];

  return (
    <div className={styles.terminalBox}>
      <div className={styles.terminalHeader}>
        <div className={styles.terminalDots}>
          <div className={`${styles.dot} ${styles.dotRed}`} />
          <div className={`${styles.dot} ${styles.dotYellow}`} />
          <div className={`${styles.dot} ${styles.dotGreen}`} />
        </div>
        <div className={styles.terminalTitle}>quick-start.sh</div>
        <div style={{display: 'flex', gap: '0.4rem'}}>
          {COMMANDS.map((tab, idx) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(idx)}
              style={{
                background: activeTab === idx ? '#1e293b' : 'transparent',
                color: activeTab === idx ? '#38bdf8' : '#94a3b8',
                border: '1px solid',
                borderColor: activeTab === idx ? '#38bdf8' : 'rgba(255,255,255,0.1)',
                borderRadius: '4px',
                padding: '2px 8px',
                fontSize: '0.75rem',
                cursor: 'pointer',
              }}>
              {tab.label}
            </button>
          ))}
        </div>
      </div>
      <div className={styles.terminalBody}>
        <div className={styles.terminalComment}>{active.comment}</div>
        <div>
          <span className={styles.terminalPrompt}>$</span>
          <span>{active.cmd}</span>
        </div>
      </div>
    </div>
  );
}

export default function Home(): ReactNode {
  const {siteConfig} = useDocusaurusContext();

  return (
    <Layout
      title="SeaweedFS Wiki & Documentation"
      description="Modern, comprehensive documentation for SeaweedFS - fast distributed object store, filer, and lakehouse">
      <header className={styles.heroBanner}>
        <div className="container">
          <div className={styles.heroBadge}>
            <span>🌊</span>
            <span>Self-Hosted SeaweedFS Knowledge Base</span>
          </div>
          <Heading as="h1" className={styles.heroTitle}>
            Fast, Scalable Storage <br />
            <span className={styles.heroGradientText}>Without the Complexity</span>
          </Heading>
          <p className={styles.heroSubtitle}>
            SeaweedFS is a versatile distributed storage system with constant-time O(1) disk seeks.
            Effortlessly run Blob Storage, POSIX Filer, S3-Compatible Object Store, and Apache Iceberg Lakehouse.
          </p>
          <div className={styles.heroActions}>
            <Link className={styles.primaryBtn} to="/docs/Secure-On-Premise-Docker-Deployment">
              🛡️ Secure Docker Guide
            </Link>
            <Link className={styles.secondaryBtn} to="/docs/Quick-Start-with-weed-mini">
              🚀 Quick Start
            </Link>
            <Link className={styles.secondaryBtn} to="/docs/">
              📚 Browse All Wiki Pages
            </Link>
            <Link
              className={styles.secondaryBtn}
              href="https://github.com/seaweedfs/seaweedfs"
              target="_blank"
              rel="noopener noreferrer">
              ⭐️ GitHub Repo
            </Link>
          </div>
          <InteractiveTerminal />
        </div>
      </header>

      <main>
        <section className={styles.featuresSection}>
          <div className="container">
            <div className={styles.sectionHeading}>
              <Heading as="h2" className={styles.sectionTitle}>
                Core Capabilities & Architecture
              </Heading>
              <p className={styles.sectionSubtitle}>
                Explore the foundational components powering petabyte-scale distributed workloads
              </p>
            </div>
            <div className={styles.grid}>
              {FEATURES.map((item, idx) => (
                <div key={idx} className={styles.card}>
                  <div className={styles.cardIcon}>{item.icon}</div>
                  <Heading as="h3" className={styles.cardTitle}>
                    {item.title}
                  </Heading>
                  <p className={styles.cardDesc}>{item.description}</p>
                  <Link className={styles.cardLink} to={item.link}>
                    Read documentation →
                  </Link>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className={styles.quicklinksSection}>
          <div className="container">
            <div className={styles.sectionHeading} style={{marginBottom: '1.5rem'}}>
              <Heading as="h2" className={styles.sectionTitle} style={{fontSize: '1.75rem'}}>
                Frequently Visited Topics
              </Heading>
              <p className={styles.sectionSubtitle}>
                Jump directly into key architecture guides, operations manuals, and API references
              </p>
            </div>
            <div className={styles.quicklinksGrid}>
              {QUICKLINKS.map((link, idx) => (
                <Link key={idx} to={link.to} className={styles.pillLink}>
                  {link.title}
                </Link>
              ))}
            </div>
          </div>
        </section>
      </main>
    </Layout>
  );
}
