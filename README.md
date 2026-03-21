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

<hr>

<div style="background-color: #21262d; border: 1px solid #30363d; border-radius: 10px; padding: 30px; line-height: 1.8; color: #d1d5db; font-family: 'Inter', system-ui, -apple-system, sans-serif;">
  <span style="color: #82a1b1; font-weight: 600; font-size: 14px; letter-spacing: 1px;">The Problem</span>
  <p style="margin-top: 10px;">
    
    On November 30th of 2022 OpenAI launched their large language model (LLM), ChatGPT. It was the starting point of the most interesting and fascinating transformation in the tech industry so far. People started experimenting with artificial intelligence once it became publicly accessible and it wasn't long before major companies like Google and Microsoft caught up and released their own models.
    Since then artificial intelligence has improved significantly and its use-cases have become very diverse. 
    
    Nowadays LLMs are used, among other things, for producing code and developing entire projects. Many of these projects are open-source and freely available on Github.  Github takes a special place in the software developing community as it enables developers from all over the world to share their projects and collaborate with each other. AI lowered the entry barrier for coding and enables everyone to contribute to this large ecosystem. Due to the integration of AI in the coding process, experienced developers got faster and people with no previous coding knowledge could suddenly bring their own innovations to life. This led to an explosion of new input on Github and although the increasing growth of open-source code is something positive, it might also become confusing and harder to navigate.

    That is where my project Gitpulse comes in.

  </p>
</div>



<div style="background-color: #21262d; border: 1px solid #30363d; border-radius: 10px; padding: 30px; line-height: 1.8; color: #d1d5db; font-family: 'Inter', system-ui, -apple-system, sans-serif; margin-top: 10px">
  <span style="color: #82a1b1; font-weight: 600; font-size: 14px; letter-spacing: 1px;">My Project</span>
  <p style="margin-top: 10px;">
    
    Gitpulse is my final project from the data Data Engineering Zoomcamp. It adresses the challenge of orienting in Github's spreading landscape and aims to track developments in the open-source space. It leverages the vast datasets contained in the Github Archive (https://www.gharchive.org/)). Specifically I want to focus on two things:

  <br>
  <b>Underrated Repositories</b>

    With this category I want to find and track repositories that are forked, commited, issued a lot or receive a lot of pull requests but get comparably few stars. It should serve as a detector for finding "rising stars" or projects that deserve more attention, based on their functionality and actuality. 

    I will use following formula to calculate the "underrated_score"(UR) of a repository

  $$
  UR = \frac{\text{Forks} + \text{Commits} + \text{PRs} + \text{Issues}}{\text{Stars} + 1}
  $$
  
    The top 10 underrated repositories are then presented in a pie chart. The bigger the slice the more underrated the is the repository.

  <br>
  <b>Comparing human vs AI activity</b>

    On Github humans can push their code but also bots. I want to investigate the development of human vs bot contribution over time. This should give an overview on how much on Github is already automated and how much AI affects the open-source landscape. For representation of the automation score I will choose a line chart.
    

    

    
  </p>
</div>


<div style="background-color: #21262d; border: 1px solid #30363d; border-radius: 10px; padding: 30px; line-height: 1.8; color: #d1d5db; font-family: 'Inter', system-ui, -apple-system, sans-serif; margin-top: 10px">
  <span style="color: #82a1b1; font-weight: 600; font-size: 14px; letter-spacing: 1px;">Project Structure</span>
  <p style="margin-top: 10px;">

    The project is structured like this:


  ![Project Structure Image](/Images/image-1.png)

    ingestion
      - ingest.py: ingests data from gharchive.org and transmits it into a GCS Bucket
    
    dbt
      - dbt_project.yml
      - profiles.yml
        models
          staging
          - stg_events.sql: Parses raw JSON
          marts
            - fct_underrated_repos.sql: Filters data for Tile 1
            - fct_ huma_vs_bot.sql: Filters data for Tile 2
      - sources.yml
    
    dashboard
      - app.py: contains the streamlit dashboard
    


    Down below I documented the whole progress of my project. If you want to know how, why and when I did a particular step, just scroll down.

  </p>
</div>


<br>
<br>

<div style="background-color: #21262d; border: 1px solid #30363d; border-radius: 10px; padding: 30px; line-height: 1.8; color: #d1d5db; font-family: 'Inter', system-ui, -apple-system, sans-serif; margin-top: 10px">
  <span style="color: #82a1b1; font-weight: 600; font-size: 14px; letter-spacing: 1px;">Progress Report</span>
  <p style="margin-top: 10px;">

  <ol>
    <li> I started off my work by creating a new project on Google Cloud</li>
    <li> Next I installed uv in the codespace I was using and created the environment</li>
    <li> Next I created a Service Account on my Project (Storage Admin, BigQuery Admin roles selected)</li>
    <li> The fourth thing I did was creating the three files main.tf, variables.tf and output.tf to set up my GCP bucket.
    
  </ol>


  </p>
</div>