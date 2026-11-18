# Build and maintenance contract

- Entry: `frontend/build.py`; run with Python 3.12+ and `-B`.
- Inputs: `frontend/seo.py`, sanitized `frontend/videos.json`, CSS/JS and public
  image manifest. No secret inputs are required to render the website.
- Output: 17 content pages, a 404 document, robots.txt and sitemap.xml in
  `frontend/dist/`.
- `HORNET_SITE_URL`: canonical origin; defaults to `https://hornethunter.com`.
- `HORNET_PUBLIC=0`: private-review noindex/disallow build. Default public build
  is indexable; this flag is metadata, not authentication or access control.
- Google Forms responder URLs are already public page inputs, not credentials.
  Form editors, responses and admin state remain outside this repository.
- The public-assets restore command downloads only allowlisted HTTPS URLs from
  hornethunter.com, refuses redirects, verifies size and SHA-256 before replacing
  a local image. It never uploads or publishes.

## Publication ownership

1. Retrieve the current source and access configuration of the existing site
   through the authenticated Sites workflow. Do not use cached source as proof
   that the live site is unchanged.
2. Compare the current source with the imported revision recorded in README.
   Reconcile only the intended public files; never copy this entire directory
   over a newer checkout.
3. Build, check links, titles, JSON-LD/CSP, form destinations and relevant layouts.
4. Push, save and deploy through Sites using the existing project manifest.
   Credentials stay in the authenticated tool session, never in Git or logs.
5. Verify the production URL and record the actual source revision and outcome.
6. Refresh this allowlisted snapshot and its handoff through normal Git review.

A repository merge is not a website deployment. No deployment workflow or
automatic social post is introduced by this import.
