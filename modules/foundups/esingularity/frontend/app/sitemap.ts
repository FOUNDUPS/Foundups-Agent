import type { MetadataRoute } from "next";

export default function sitemap(): MetadataRoute.Sitemap {
  const base = "https://esingularity.ai";
  const audited = new Date("2026-09-14");

  return [
    {
      url: `${base}/`,
      lastModified: audited,
      changeFrequency: "weekly",
      priority: 0.9,
    },
    {
      url: `${base}/future`,
      lastModified: audited,
      changeFrequency: "weekly",
      priority: 0.8,
    },
    {
      url: `${base}/reports/jhr`,
      lastModified: audited,
      changeFrequency: "daily",
      priority: 1,
    },
    {
      url: `${base}/team`,
      lastModified: audited,
      changeFrequency: "weekly",
      priority: 0.6,
    },
    {
      url: `${base}/team/012`,
      lastModified: audited,
      changeFrequency: "monthly",
      priority: 0.5,
    },
    {
      url: `${base}/team/0102`,
      lastModified: audited,
      changeFrequency: "monthly",
      priority: 0.5,
    },
  ];
}
