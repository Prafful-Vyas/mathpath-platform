import { HeadFC, Link, PageProps, graphql } from "gatsby";
import React from "react";

import { Layout, Seo } from "../components/Layout";

interface Example { id: string; rating: number; prompt: string; hint: string }
interface Data {
  site: { siteMetadata: { appUrl: string } };
  topic: {
    slug: string; title: string; grade: number; description: string;
    problemCount: number; ratingMin: number; ratingMax: number; examples: Example[];
  };
}

const level = (r: number) => (r < 750 ? "Warm-up" : r < 1100 ? "Core" : "Challenge");

export default function TopicPage({ data }: PageProps<Data>) {
  const t = data.topic;
  return (
    <Layout>
      <p><Link to="/">← All topics</Link></p>
      <h1>{t.title}</h1>
      <p className="meta">
        Grade {t.grade} · {t.problemCount} problems rated {t.ratingMin}-{t.ratingMax}
      </p>
      <p>{t.description}</p>
      <h2>Example problems</h2>
      {t.examples.map((e) => (
        <div key={e.id} className="example">
          <strong>{level(e.rating)}</strong> <span className="meta">(rating {e.rating})</span>
          <div>{e.prompt}</div>
          <div className="meta">Hint: {e.hint}</div>
        </div>
      ))}
      <p style={{ marginTop: 24 }}>
        <a className="button" href={`${data.site.siteMetadata.appUrl}/?topic=${t.slug}`}>Practise this topic</a>
      </p>
      <p className="meta">Practice adapts to you: each problem is picked so you have about a 70% chance of getting it right.</p>
    </Layout>
  );
}

export const query = graphql`
  query TopicPage($slug: String!) {
    site { siteMetadata { appUrl } }
    topic(slug: { eq: $slug }) {
      slug title grade description problemCount ratingMin ratingMax
      examples { id rating prompt hint }
    }
  }
`;

export const Head: HeadFC<Data> = ({ data }) => (
  <Seo title={`${data.topic.title} | MathPath`} description={data.topic.description} />
);
