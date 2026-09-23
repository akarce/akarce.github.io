# akarce.github.io

Source of my site, [akarce.github.io](https://akarce.github.io), and my CV.

I'm a data engineer in Istanbul. I build the secure, multi-tenant analytics layer and the pipelines that feed it: ClickHouse with row-level security, FastAPI and SSO on top, Airflow, Spark, Kafka and Flink underneath, all on Kubernetes. My work at Mediastream AG lives in private repositories, so the site describes it instead.

## What's here

| Path | What it is |
|---|---|
| `index.html`, `assets/` | The site: plain HTML, CSS and a little JavaScript, no framework, no analytics. Videos play in place from youtube-nocookie.com, and only after a click |
| `data/site.json` | The projects, and which repo, articles and videos belong to each |
| `scripts/build_content.py` | Renders the Projects and Writing blocks of `index.html` from `data/`. `--fetch` refreshes `data/feeds.json` (Medium, YouTube, GitHub stars) first; `--check` fails if the page is out of date |
| `cv/index.html` | CV source. `./cv/build.sh` renders it to `Ceyhun_Akar_CV.pdf` with headless Chrome |
| `.github/workflows/site.yml` | Runs the script with `--fetch` every day, commits if anything changed, then deploys to GitHub Pages |

The CV is one column with real text and embedded TrueType fonts, so ATS parsers read it top to bottom.

- [Download the CV (PDF)](https://akarce.github.io/Ceyhun_Akar_CV.pdf)
- [LinkedIn](https://www.linkedin.com/in/akarce/)
