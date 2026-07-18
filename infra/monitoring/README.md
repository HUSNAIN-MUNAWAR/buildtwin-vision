# Monitoring adapter

The API emits correlation IDs, response timing headers, job metrics, camera last-seen values, `/health`, and `/ready`. A Prometheus adapter can expose counters and histograms without changing the domain services. The initial release deliberately avoids pretending that a Prometheus stack was operated during local verification.
