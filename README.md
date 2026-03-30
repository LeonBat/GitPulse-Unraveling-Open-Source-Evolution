<div style = "text-align: center">
  <div style="background-color: #282a2d; border: 1px solid #3f444a; border-radius: 12px; padding: 24px; margin-bottom: 25px;">
    <h2 style="color: #e0e0e0; border-bottom: none; margin: 0; font-family: 'Georgia', serif; letter-spacing: 1px; font-weight: 400;">
      GitPulse: Unraveling Open-Source Evolution
    </h2>
    <p style="color: #82a1b1; margin-top: 8px; font-size: 0.9em; text-transform: uppercase; letter-spacing: 2px;">
      Data Engineering • Trends • Development
    </p>
  </div>
</div>

    
On November 30th of 2022 OpenAI launched their large language model (LLM), ChatGPT. It was the starting point of the most interesting and fascinating transformation in the tech industry so far. People started experimenting with artificial intelligence once it became publicly accessible and it wasn't long before major companies like Google and Microsoft caught up and released their own models.
Since then artificial intelligence has improved significantly and its use-cases have become very diverse. 
    
Nowadays LLMs are used, among other things, for producing code and developing entire projects. Many of these projects are open-source and freely available on Github.  Github takes a special place in the software developing community as it enables developers from all over the world to share their projects and collaborate with each other. AI lowered the entry barrier for coding and enables everyone to contribute to this large ecosystem. Due to the integration of AI in the coding process, experienced developers got faster and people with no previous coding knowledge could suddenly bring their own innovations to life. This led to an explosion of new input on Github and although the increasing growth of open-source code is something positive, it might also become confusing and harder to navigate.




    
Gitpulse is my final project from the data Data Engineering Zoomcamp. It adresses the challenge of orienting in Github's spreading landscape and aims to track developments in the open-source space. It leverages the vast datasets contained in the Github Archive (https://www.gharchive.org/). Specifically I want to focus on two things:

<br>
<b>Repositories with most activity</b>

With this category I want to find and track repositories that are forked, commited, issued a lot or receive a lot of pull requests. It should serve as a detector for finding "developing hubs" and possibly as a guide for new interesting repositories that are still in their creation phase.

I will use following formula to calculate the "Acitivity Score"(AR) of a repository

<b>Forks + Commits + PRs + Issues</b>

These events are weighted so that a realistic picture of activity is created.

  
The top 10 most active repositories are then presented in a pie chart. The bigger the slice the more active is the repository.

<br>
<b>Comparing human vs Bot activity</b>

On Github humans can push their code but also bots. I want to investigate the development of human vs bot contribution over time. This should give an overview on how much on Github is already automated and how much bot activity affects the open-source landscape. For representation of the automation score I will choose a line chart.
    




<div style="background-color: #21262d; border: 1px solid #30363d; border-radius: 10px; padding: 30px; line-height: 1.8; color: #d1d5db; font-family: 'Inter', system-ui, -apple-system, sans-serif; margin-top: 10px">
  <span style="color: #82a1b1; font-weight: 600; font-size: 14px; letter-spacing: 1px;">Project Structure</span>
  <p style="margin-top: 10px;">

    The project is structured like this:


  ![Project Structure Image](/Images/image.png)


Down below the different folders of the repository are further explained:

### Directory Overview

- **`ingestion/`** — Contains the ETL pipeline that fetches raw data from the GitHub Archive. The `ingest.py` script queries and processes GitHub events (pushes, pull requests, issues, forks) and loads them into BigQuery.

- **`bigquery/`** — Defines the BigQuery schema (`schema.sql`) that structures the raw GitHub events data. This is where all ingested data is stored before transformation.

- **`dbt/`** — The data transformation layer. Contains dbt models that clean, aggregate, and create analytical views from raw GitHub data. Includes staging models (`stg_github_events.sql`) and mart models for specific analyses (`human_vs_bot_activity.sql`, `most_active_repos.sql`).

- **`dashboard/`** — A Streamlit-based interactive dashboard (`streamlit_dashboard.py`) that visualizes the analysis results, including activity trends and human vs bot contribution patterns.

- **`terraform/`** — Infrastructure as code for provisioning cloud resources required to run the pipeline (databases, storage, compute).


### Key Files

- **`main.py`** — Entry point for running the complete pipeline orchestration
- **`run_pipeline.sh`** — Shell script to execute the entire data pipeline
- **`setup.sh`** — Setup script for initializing the project environment



Reproduction:

There are two documentation files available:

docs.md provides extensive background to this project and allows profound insights in it
quickstart.md just tells you the essential stuff you need to know to get the pipeline running

Both files can be found in the docs folder
