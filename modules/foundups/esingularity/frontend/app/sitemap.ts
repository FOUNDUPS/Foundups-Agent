import type { MetadataRoute } from "next";
import { jhrIssues } from "../content/jhr-issues";

export default function sitemap(): MetadataRoute.Sitemap {
  const base = "https://esingularity.ai";
  const publishedJhr = jhrIssues
    .filter((issue) => issue.status === "published")
    .map((issue) => ({
      url: issue.href,
      lastModified: new Date(issue.updatedAt),
      changeFrequency: "daily" as const,
      priority: 1,
    }));

  return [
    {
      url: `${base}/`,
      lastModified: new Date("2026-09-11"),
      changeFrequency: "weekly",
      priority: 0.9,
    },
    {
      url: `${base}/future`,
      lastModified: new Date("2026-09-11"),
      changeFrequency: "weekly",
      priority: 0.8,
    },
    ...publishedJhr,
  ];
}
