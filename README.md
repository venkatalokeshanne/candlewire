# Candlewire pipeline (Claude Code routines)

Setup, in order:
1. Create a PUBLIC GitHub repo named `candlewire`; upload everything in this folder, including the hidden `.claude` folder.
2. Edit `.claude/skills/candlewire-daily-post/config.json`: set `"media_repo": "<your-github-username>/candlewire"`.
3. claude.ai/code: connect GitHub, allow the repo. Create an environment `candlewire`: Network access = Full (tighten later),
   Setup script = contents of `setup.sh`, Network secret: host `graph.facebook.com`, type Bearer, value = your Instagram token.
4. Create three routines at claude.ai/code/routines (prompts in routine_prompts.md). Run each once on demand before trusting the schedule.
5. To publish an approved post, open that run's session and reply: `publish <date> <slot>`.

Each run writes one small `data.json`; code does layout, checks and rendering.

6. Inspiration inbox: add links or screenshot names of posts you like to `inspiration/notes.md` (what you liked, structure only). Routines read it every run.
7. In each routine's connectors, keep Stocktwits included (trend scan). Optional later: Alpha Vantage (structured market data), Metricool (analytics).
