---
title: "Kanji mnemonics beat rote memorisation"
domains: [concepts, hobbies]
type: reference
tier: insight
status: ideas
applies_to: personal
relationships:
  - ref: japanese-study
    type: supports
related: [japanese-resources]
created: 2026-03-08
last_updated: 2026-04-12
last_verified: 2026-05-07
confidence: medium
source: manual
tags: [japanese, learning, memory]
---

<!-- EXAMPLE: This article demonstrates a tier:insight article — an observation worth noting, not yet a fully crystallised concept. -->

# Visual mnemonics outperform rote on kanji

After two months of brute-force Anki on N5 kanji, then a switch to mnemonic-
based study for the next batch, retention is visibly different. The insight
is small but actionable.

## The observation

Kanji learned by rote drift in Anki: I get them right at 1-day reviews and
miss them at 3-week reviews. Kanji learned with a one-line visual mnemonic
tied to the components survive 3-week reviews at roughly twice the rate.

Sample size: about 80 kanji per group, single learner — so call it
suggestive, not proven.

## Why I think this works

A mnemonic forces me to **decompose** the kanji into its radicals before I
re-encode the meaning. Decomposition is itself a recall exercise, and it
gives me a graceful failure mode: even if I forget the meaning, I can
reconstruct it from the components I do remember.

Rote review skips that step. If the whole-character recognition fails,
there's nothing to fall back to.

## Caveats

- The mnemonics need to be mine. Borrowed mnemonics from books rarely stick.
- Some characters resist this — abstract or phonetic kanji where the
  components don't carry the meaning.

## Where it lives now

Implemented as the working method in `japanese-study`.
