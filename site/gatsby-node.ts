import fs from "fs";
import path from "path";

import type { GatsbyNode } from "gatsby";

// The site is built from the same seed files the content service loads into DynamoDB,
// so curriculum pages and the practice bank never disagree. Answer keys are not sourced.
const SEED = path.resolve(__dirname, "..", "seed");

interface SeedTopic { slug: string; title: string; grade: number; order: number; description: string }
interface SeedProblem { id: string; topic: string; rating: number; prompt: string; hint: string }

const read = <T,>(file: string): T => JSON.parse(fs.readFileSync(path.join(SEED, file), "utf-8"));

export const sourceNodes: GatsbyNode["sourceNodes"] = ({ actions, createNodeId, createContentDigest }) => {
  const problems = read<SeedProblem[]>("problems.json");
  for (const t of read<SeedTopic[]>("topics.json")) {
    const own = problems.filter((p) => p.topic === t.slug).sort((a, b) => a.rating - b.rating);
    // Three examples across the difficulty range: easiest, middle, hardest.
    const examples = [own[0], own[Math.floor(own.length / 2)], own[own.length - 1]]
      .map(({ id, rating, prompt, hint }) => ({ id, rating, prompt, hint }));
    const node = {
      ...t,
      problemCount: own.length,
      ratingMin: own[0].rating,
      ratingMax: own[own.length - 1].rating,
      examples,
    };
    actions.createNode({
      ...node,
      id: createNodeId(`topic-${t.slug}`),
      internal: { type: "Topic", contentDigest: createContentDigest(node) },
    });
  }
};

export const createPages: GatsbyNode["createPages"] = async ({ graphql, actions, reporter }) => {
  const result = await graphql<{ allTopic: { nodes: { slug: string }[] } }>(`
    { allTopic { nodes { slug } } }
  `);
  if (result.errors || !result.data) {
    reporter.panicOnBuild("Could not query topics", result.errors);
    return;
  }
  for (const { slug } of result.data.allTopic.nodes) {
    actions.createPage({
      path: `/topics/${slug}/`,
      component: path.resolve(__dirname, "src/templates/topic.tsx"),
      context: { slug },
    });
  }
};
