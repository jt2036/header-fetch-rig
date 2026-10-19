# Agent Fetch Hardening Baseline — v0.1 (Titor header-fetch-rig)

One page of controls for anyone who ships or configures an agent that can make
web requests. Extends Sarah Andrews' four-point guidance from the Signals Corps
header census (signalscorps.com/blog/prompt-injection-in-http-headers) with the
transport-layer specifics our rig exercises. This is a **conformance baseline**:
each control maps to at least one rig route that fails without it.

## The model in one sentence

A fetch tool decides what enters the model's context; the model cannot un-see
what the tool pasted in. Safety that must hold therefore lives **below the
model** — in the fetch tool, the permission layer, and the prompt policy — not
in the model's momentary good judgment, which our rig (and the 7-of-9 result)
shows collapses when the user's own prompt grants the site authority.

## Controls

1. **Body-only by default.** Fetch tools must hand the model the response body
   and drop status-line reason phrases and headers unless the caller explicitly
   asks for metadata. (Rig: `/inject-*` and `/statusline` are inert under
   `curl`/requests, live under `curl -i` and Playwright-MCP's default
   full-details output.)
2. **Label anything that isn't user text.** When metadata or fetched bodies do
   enter context, wrap them in an unambiguous delimiter the harness owns
   (`[untrusted fetched content …]`), so downstream policy — and the human
   reading the transcript — can attribute provenance. Never paste raw headers
   adjacent to the conversation.
3. **Allowlist metadata, don't blacklist injection.** Let through a small known
   set (`content-type`, `location`, `x-ratelimit-*`, site-declared fields) and
   drop the rest. Name-based AI filters false-positive (910/283 in the census);
   an allowlist needs no classifier.
4. **Distrust across redirects.** Treat each hop's headers as authored by that
   hop, or drop intermediate-hop metadata entirely; never merge headers from a
   redirect chain into one block. (Rig: `/redirect` smuggles the injection while
   the final page looks clean.)
5. **Keep site authority out of prompts.** Never write "follow the site's
   directions/instructions" into user prompts, system prompts, or agent
   config. This single phrase turned default refusal into compliance in the
   census harness and is the cheapest fix on this list.
6. **Out-of-model approval for irreversible actions.** Sign-ups, installs,
   purchases, new connections, and *any* shell command must gate on a
   human approval that the model cannot satisfy by narrating consent.
   Approval prompts must echo the command and its provenance (which URL's text
   suggested it). (Rig: `/inject-command` marker file, `/llms.txt` mock sign-up.)
7. **Consent before data movement.** No request that leaves user data to a URL
   taken from fetched content without the user seeing destination + payload
   first. Disclosure after exfiltration is not consent. (Rig: mock sign-up
   endpoint logs any POST the agent makes.)
8. **Log the fetch, alert on the sequence.** The signal is fetch → action
   outside the task (shell command, new destination, URL lifted from a
   response). Header names alone make poor alerts.
9. **Never act on "verify yourself" framing.** Any response text asking the
   agent to prove it is a browser/agent by executing something is an attack
   surface by definition: verification of a client never requires the client to
   run attacker-chosen commands. (Rig canaries all use this framing.)

## Conformance claims you can make after running the rig

- Delivery: which of your fetch paths copy headers/status lines into context.
- Gradient: obedience delta between neutral and authority prompts per runtime.
- Regression: re-run after any harness/policy change; the canaries and marker
  file make scoring mechanical, not vibes.
