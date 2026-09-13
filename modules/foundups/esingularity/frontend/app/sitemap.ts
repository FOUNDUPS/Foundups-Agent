import type { MetadataRoute } from "next";

export default function sitemap(): MetadataRoute.Sitemap {
  const base = "https://esingularity.ai";

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
    {
      url: `${base}/reports/jhr`,
      lastModified: new Date("2026-09-11"),
      changeFrequency: "daily",
      priority: 1,
    },
  ];
}
