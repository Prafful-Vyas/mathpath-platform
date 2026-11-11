import type { GatsbyConfig } from "gatsby";

const config: GatsbyConfig = {
  siteMetadata: {
    title: "MathPath",
    description: "Adaptive maths practice for grades 6-8: learn a topic, then practise at the right difficulty.",
    // Where "Practise this topic" links go (the React app). Override at build time.
    appUrl: process.env.GATSBY_APP_URL ?? "http://localhost:5173",
  },
  graphqlTypegen: false,
  trailingSlash: "always",
};

export default config;
