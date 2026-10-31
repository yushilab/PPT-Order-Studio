---
name: ppt-order-design
description: Select and switch design engines for a PPT Order Studio order, route optional PPTAgent authoring, and import reviewed sample or full-deck results. Use for this project's design rounds, not unrelated slide creation.
---

# PPT order design

Locate the repository containing `AI_START_HERE.md` and use its CLI as the state interface. Repository paths below are relative to that root. Read `docs/design-engines.md` only for the route needed now.

## Select the current route

- Existing order: run `status ORDER` and `design ORDER`; inspect the current engine, round, confirmations and manual baseline before authoring.
- New order: `init ORDER ... --engine builtin|pptagent` overrides the project default. `configure --default-engine ...` affects future orders only. The default is `builtin`.
- `builtin`: use the existing order workflow and native layouts. Do not load or install PPTAgent for this route.
- `pptagent`: check `design-doctor`. A missing runtime does not authorize system installation, model configuration or silent fallback. Report the missing capability and follow the documented opt-in setup or the operator's selected alternative.

The upstream source is bundled at `third_party/pptagent/`; read its `SKILL.md` only when this order uses that engine. Resolve upstream paths and interpreter to that directory. Use the pinned source and preserve its license; do not register its broad trigger globally as part of a default order.

## Author and import PPTAgent results

Use `sample ORDER --slides ...` after the real outline confirmation, or `build ORDER` after the real design confirmation. In PPTAgent mode these prepare a fresh handoff and return `needs_authoring`, not a finished PPTX.

Read the returned request and selected source material. Follow the upstream Skill to author in the returned workspace, inspect actual slide and exported-deck renders, and complete its strict finalization. Keep sources local as required by its task contract. Only record visual passes after the images have actually been inspected.

External pages may use `layout: custom`; preserve their title, core message, source references and selected page IDs. Native detailed layout fields need not be invented for the external authoring route. Before switching such pages to `builtin`, convert them to supported native layouts and complete their required fields.

Import with `design-import ORDER --workspace PATH`; then inspect the current sample/full QA. Import validates current-round and source/evidence binding; it does not provide customer approval. Keep the operator's outline, design and final confirmations separate from upstream rendering evidence. Never edit either tool's managed state or fabricate a final report.

For a full-deck handoff, preserve the accepted sample's visual specification and components. Keep all requested pages and traceable facts. Use actual rendered PPTX pages to judge export fidelity, especially Chinese font metrics and complex decorations.

## Change a design round

On an explicit request to try another method, use `design ORDER --engine ... --label ...`. This archives the current round before starting a new one. Engine-only changes retain an unchanged content plan but require the new design and final version to be confirmed.

Use `design ORDER --restore ID` only when the operator wants that saved round; it restores its page/style snapshot subject to provenance and file checks. After any switch or restore, reread `status` rather than assuming approval remained valid. An active manual baseline blocks switching and restore; preserve that PPTX and use a separate order for a major rebuild.

## Report what happened

Return the actual engine, round, artifact or handoff paths, completed checks, unresolved requirements, and next operator action. Distinguish a prepared workspace, an imported PPTX, visual review and customer acceptance. Keep context limited to the active round; log actual usage or unknown values, not guessed savings.
