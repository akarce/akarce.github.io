# akarce.github.io

Source of my site, [akarce.github.io](https://akarce.github.io), and my CV.

I'm a data engineer in Istanbul. I build the secure, multi-tenant analytics layer and the pipelines that feed it: ClickHouse with row-level security, FastAPI and SSO on top, Airflow, Spark, Kafka and Flink underneath, all on Kubernetes. My work at Mediastream AG lives in private repositories, so the site describes it instead.

## What's here

| Path | What it is |
|---|---|
| `index.html`, `assets/` | The site: plain HTML, CSS and a little JavaScript, no framework, no analytics, no third-party requests |
| `cv/index.html` | CV source. `./cv/build.sh` renders it to `Ceyhun_Akar_CV.pdf` with headless Chrome |
| `.github/workflows/site.yml` | Pulls my latest Medium posts and YouTube videos into the page every day, then deploys to GitHub Pages |

The CV is one column with real text and embedded TrueType fonts, so ATS parsers read it top to bottom.

- [Download the CV (PDF)](https://akarce.github.io/Ceyhun_Akar_CV.pdf)
- [LinkedIn](https://www.linkedin.com/in/akarce/)
