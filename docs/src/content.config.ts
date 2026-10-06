import { defineCollection } from 'astro:content';
import { docsLoader } from '@astrojs/starlight/loaders';
import { docsSchema } from '@astrojs/starlight/schema';

// `_generated/` is produced by `pnpm sync` (tools/docs.py) from books/*/book.json.
// It is a build artifact and is gitignored — never edit it by hand.
export const collections = {
  docs: defineCollection({ loader: docsLoader(), schema: docsSchema() }),
};