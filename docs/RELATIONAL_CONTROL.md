# Relational Control and Adaptation

## Core idea

Elite midfield play is relational. A player changes what teammates can do, where opponents move, and how quickly the collective advances or pauses.

Version 0.5 introduces geometry-based proxies for that interaction.

## Frame-level signals

- pressure attraction: nearby opponents and closing movement toward the subject;
- support reactivity: how strongly nearby teammate movement changes around the subject;
- option enablement: the strongest modeled creation of a teammate option;
- network brokerage: breadth and diversity of pass access;
- progressive access: the best current progression opportunity;
- action diversity: whether pass, carry, and hold remain available;
- role adaptability: action diversity plus relational support;
- directive influence: a composite display signal for the current frame.

## Sequence-level signals

- co-adaptation lag in frames and seconds;
- co-adaptation correlation;
- mean and peak directive influence;
- temporal change in support reactivity;
- pressure attraction and release;
- option emergence after teammate movement.

## Guardrail

These metrics can reveal movement relationships and response timing. They cannot by themselves establish communication, leadership, tactical intent, or causality.

Causal evaluation should use:

- repeated comparable situations;
- teammate and opponent fixed effects;
- tactical-role controls;
- intervention or counterfactual models;
- annotation from qualified coaches or analysts;
- uncertainty and sensitivity analysis.

## Frontend experience

The `/orchestration` route should show:

- the subject at the center of a dynamic relationship graph;
- teammate support links;
- opponent attraction links;
- option enablement over time;
- co-adaptation lag;
- a synchronized action-menu timeline;
- counterfactual teammate movements;
- a clear `geometry proxy` evidence badge.
