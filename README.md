# polyfin-proxy

> [!WARNING]
> **Archived.** Superseded by [jellyfin-plugin-polyfin](https://github.com/elhlab/jellyfin-plugin-polyfin).
>
> This is an early, in-progress prototype, archived mid-refactor. Parts of it do not work and some code is only placeholders.

## Goal and approach

The goal was to support multiple languages for a Jellyfin library. The approach was to intercept the traffic between the Jellyfin server and your clients, and query metadata on the fly.

## Scope

The scope initially included movies and series, but was soon cut to just movies, as series support added a bunch of complexity that the project was not ready for while the proxy plumbing was still in progress.

## Deployment

The deployment was intended to be behind a reverse proxy that only routes the metadata requests through polyfin, so media requests don't go through the proxy. It was still designed with a full proxy idea in mind.

## Status

Archived mid-refactor; `src/polyfin/server.py` does not run.

The proxy plumbing (streaming and response interception), config loading and locale matching have working first drafts with tests. Fetching translated metadata from a provider was never built, and only movies were in scope.

The tests can be run with `pytest` and should all pass.

## Why it became a plugin

The proxy implementation ended up requiring a significant amount of code for proxying requests, streaming responses, and rewriting raw JSON.

Doing the same work in a Jellyfin plugin allows the implementation to focus on handling the metadata instead of proxying traffic. It also allows the plugin to use Jellyfin's existing metadata providers, so users no longer need to apply for their own provider API token.

In short, the plugin approach was simpler both to develop and to deploy.

## License

MIT, see [LICENSE](LICENSE).
