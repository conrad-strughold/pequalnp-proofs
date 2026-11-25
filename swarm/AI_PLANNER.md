# Optional model-assisted planning

Configure SWARM_AI_KEY, SWARM_AI_MODEL and optionally SWARM_AI_URL (trusted HTTPS OpenAI-compatible chat completions endpoint). The default endpoint is the OpenAI API. No API credentials are stored in the repository. Model usage can incur costs. The rule-based planner works without credentials.

In /admin choose a project and select Preview AI proposals. Inspect and edit the JSON, then publish reviewed proposals. The API separates preview and apply. A preview sends project scope, bounded task descriptions, and accepted/rejected finding summaries and reviews to the configured provider, not raw evidence or contributor credentials. Use only public, nonconfidential research. The provider has no tools or access to the database.

At most five proposed tasks per request; normalized exact-title deduplication and completed prerequisite checks run again at publication. Semantic duplicates and unsafe suggestions remain possible; operator review is necessary. No unattended scheduling, automated acceptance or external actions are enabled. The adapter is tested for validation without real API calls; live model integration requires credentials.
