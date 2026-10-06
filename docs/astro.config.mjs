import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import sitemap from '@astrojs/sitemap';

// GitHub Pages project site: https://caizongyuan.github.io/pi-lessons/
// `base` must be set, and every internal link must be written relative or base-aware —
// nothing may assume the site is served from the domain root.
const BASE = '/pi-lessons';

export default defineConfig({
  site: 'https://caizongyuan.github.io',
  base: BASE,
  trailingSlash: 'always',
  build: { format: 'directory' },
  integrations: [
    starlight({
      title: 'Pi 技术手册',
      description:
        'Pi 的中文技术手册。把英文技术手册翻译成适合在线阅读和检索的中文版，并保留关键代码、图表与原始结构。',
      // Both books come from books/<id>/book.json via `pnpm sync`; the sidebar groups below
      // mirror that order so navigation stays generated, never hand-maintained.
      sidebar: [
        { label: '首页', slug: '' },
        {
          label: 'Pi 技术手册',
          collapsed: false,
          items: [
            { label: '01 模型', slug: 'pi-manual/01-model' },
            { label: '02 供应商层', slug: 'pi-manual/02-provider' },
            { label: '03 智能体循环', slug: 'pi-manual/03-agent-loop' },
            { label: '04 编码智能体', slug: 'pi-manual/04-coding-agent' },
            { label: '05 配置与扩展性', slug: 'pi-manual/05-config' },
            { label: '06 集成与界面', slug: 'pi-manual/06-integrations' },
            { label: '07 实验特性与运维', slug: 'pi-manual/07-operations' },
            { label: '08 参考', slug: 'pi-manual/08-reference' },
          ],
        },
        {
          label: 'Pi Durable 技术手册',
          collapsed: false,
          items: [
            { label: '01 模型', slug: 'pi-durable/01-model' },
            { label: '02 Session 与提交', slug: 'pi-durable/02-sessions' },
            { label: '03 会话与上下文', slug: 'pi-durable/03-conversations' },
            { label: '04 文档', slug: 'pi-durable/04-documents' },
            { label: '05 任务', slug: 'pi-durable/05-tasks' },
            { label: '06 运行', slug: 'pi-durable/06-runs' },
            { label: '07 扩展与 Agent', slug: 'pi-durable/07-extensions' },
            { label: '08 观察', slug: 'pi-durable/08-watching' },
            { label: '09 存储与环境', slug: 'pi-durable/09-storage' },
            { label: '10 实践', slug: 'pi-durable/10-practice' },
            { label: '11 参考', slug: 'pi-durable/11-reference' },
          ],
        },
      ],
      customCss: ['./src/styles/custom.css'],
      head: [
        // Astro does not emit these by default, and a docs site without a favicon or a
        // sitemap is an easy thing to notice.
        { tag: 'link', attrs: { rel: 'icon', type: 'image/svg+xml', href: `${BASE}/favicon.svg` } },
        { tag: 'link', attrs: { rel: 'sitemap', href: `${BASE}/sitemap-index.xml` } },
        { tag: 'meta', attrs: { name: 'theme-color', content: '#2a5f88' } },
      ],
      components: {
        // The homepage is a real page (src/content/docs/index.mdx), not a generated one.
        PageTitle: './src/components/PageTitle.astro',
      },
      pagination: true,
      lastUpdated: false,
      credits: false,
      social: {
        github: 'https://github.com/CaiZongyuan/pi-lessons',
      },
    }),
  ],
});