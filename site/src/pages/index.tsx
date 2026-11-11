import { HeadFC, Link, PageProps, graphql } from "gatsby";
import React from "react";

import { Layout, Seo } from "../components/Layout";

interface Data {
  site: { siteMetadata: { title: string; description: string } };
  allTopic: { nodes: { slug: string; title: string; grade: number; description: string; problemCount: number }[] };
}

export default function Index({ data }: PageProps<Data>) {
  return (
    <Layout>
      <h1>Maths, one right-sized step at a time</h1>
      <p className="meta">{data.site.siteMetadata.description}</p>
      <div className="grid">
        {data.allTopic.nodes.map((t) => (
          <Link key={t.slug} to={`/topics/${t.slug}/`} className="card" style={{ textDecoration: "none", color: "inherit" }}>
            <h2>{t.title}</h2>
            <div className="meta">Grade {t.grade} · {t.problemCount} practice problems</div>
            <p>{t.description}</p>
          </Link>
        ))}
      </div>
    </Layout>
  );
}

export const query = graphql`
  query IndexPage {
    site { siteMetadata { title description } }
    allTopic(sort: { order: ASC }) { nodes { slug title grade description problemCount } }
  }
`;

export const Head: HeadFC<Data> = ({ data }) => (
  <Seo title={`${data.site.siteMetadata.title} | Curriculum`} description={data.site.siteMetadata.description} />
);
