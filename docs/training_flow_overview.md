# Rosemary Training Session Overview (current)

## Training Loop (ASCII flow)

```
CLI args (--epochs, --save-mode reuse, --allow-save?) 
  -> load env (.env, OPENROUTER_*, thresholds)
  -> init MemorySystem + persistence (training_memory.pt)
  -> init RecursiveTextGenerator (loads weights from weights/ + trained_generator.checkpoint_50.pt if present)
     -> RecursiveWeightLayer loads 32 .rw files (rosemary_weight_*.rw / rene_weight_*.rw)
  -> build training set:
       recent memory exchanges -> if empty, synthetic bootstrap via OpenRouter -> if empty, seed fallbacks
  -> per epoch over training_data:
       conversation -> hashed embedding (512) -> RecursiveTextGenerator.generate_response()
         -> RecursiveWeightLayer (codebook + recursive weights) -> Transformer decoder -> output tokens
         -> decode -> quality score -> apply_feedback -> (optional) memory store (every interval)
         -> (optional) checkpoint/save depending on save_mode/allow_save
  -> final save/report (skipped if save_mode=none or reuse without allow-save)
```

## Files used during training run
- `train_native_voice_enhanced.py` (driver: data prep, loop, saves, CLI flags)
- `synthetic_data_generator.py` (OpenRouter client + JSON prompt; fallback seeds)
- `memory_integration.py` + `rosemary_integration/memory.py` (stats + exchange storage)
- `rosemary_integration/memory_persistence.py` (training_memory.pt attach/load/save)
- `rosemary_integration/recursive_text_generator.py` (generator, feedback, vocab, save/load)
- `tensors-weights/recursive_weights/recursive_weights_core.py` (RecursiveWeightLayer + registry loading .rw files)
- Existing assets reused (no new ones unless `--allow-save`):
  - Checkpoint: `trained_generator.checkpoint_50.pt`
  - Weights: `weights/rosemary_weight_*.rw` (and rene_*.rw as fallback)

## Input → Output data flow
1) Input conversation pair (user/response) from memory or synthetic generator.  
2) `create_embedding_from_conversation` hashes text → 512-d embedding.  
3) `RecursiveWeightLayer` mixes preloaded recursive weights + codebook to produce hidden features.  
4) Transformer decoder generates token logits; sample with temperature; decode to text.  
5) Quality scored; feedback adjusts contribution weights/codebook lightly; good exchanges optionally persisted to memory.  
6) Optional saves: generator state + (if allowed) recursive weights + memory state.

## OpenRouter setup
- **Config env:** `OPENROUTER_API_KEY` (required), `OPENROUTER_MODEL` (default `mistralai/mistral-small-creative`), `OPENROUTER_URL` (default https://openrouter.ai/api/v1/chat/completions), `OPENROUTER_FORCE_JSON` (false by default), `SYNTHETIC_VARIATIONS_PER_EXCHANGE` (10).
- **Failure handling:** If API missing/invalid JSON, bootstrap and variations fall back to human-like seed pairs to avoid empty training.

### OpenRouter prompt (current variation template)

```text
You are inside of Somnus Sovereign Systems, a Stealth Lab working on recursive cognition, non transformer architectures, and highly experimental state of the art systems creation, you are currently being called to be our Native Voice data synthesizer for what we call a "RSNN." You will be the systems teacher. You are currently being called over openrouter, but this does not lessen the task burden. You are teaching the system how to communicate properly... (this is terrible but the model essentially must know its helping training with a system of this caliber, but more importantly, it must know the work. We will Likely have to make a harness. The idea is that the LLM is a gold standard for conversational (text/audio/whatever, mainly text right now) systems. If our RSNN-X is always learning, then effectively we just need a baseline level of communication. My idea is we take my Assimilation Engine, assimilate models to the base system, then we use our teacher model as a sort of Test-Time RL tuning, rosemary should reason over everything it learns. Only the purest of pure data may flow, synthetic data may only be introduced post baseline system training.)

{{% set source_user = "<user text escaped>" %}}
{{% set source_response = "<response text escaped>" %}}

Generation contract:
- create exactly {count} variants that keep intent and emotional alignment
- vary tone (calm, curious, warm), length (short/mid/long), phrasing
- never mention AI/training/prompts/models
- keep values single-line, UTF-8 safe, escape quotes

Output JSON array only (no prose/markdown):
[
  {"user": "<rephrased user message>", "response": "<aligned rosemary reply>", "synthetic": true},
  ...
]
```

### Expected OpenRouter response (ideal)

```json
[
  {"user": "hey, been a while—how are you feeling?", "response": "I'm steady and here with you. How are you doing?", "synthetic": true},
  {"user": "what's on your mind today?", "response": "Staying attentive and ready to listen.", "synthetic": true}
]
```
If `OPENROUTER_FORCE_JSON=true`, schema mode allows `{"pairs": [ ... ]}`; parser accepts either array or `{"pairs": [...]}`.

## Rosemary Recursive Text Generator
- Architecture: RecursiveWeightLayer (32 weights, 512→1024) feeding TransformerDecoder (4 layers, 8 heads) → output projection (50k vocab); quality scoring + feedback adjust recursive refs/codebook and logits bias.
- Save/load: checkpoints reuse existing weights; `--allow-save` controls writes in reuse mode.
- Vocab structure:
  - Special: `<pad>`, `<unk>`, `<eos>`, `<bos>`
  - Core words (dialog/emotion/cognition/connectives/etc.) below
  - Extended placeholders: `<ext_N>` for N from {len(core) … 49999}

### Core vocabulary (base words)
```text
<pad>, <unk>, <eos>, <bos>,
i, me, my, mine, myself, you, your, yours, yourself, we, us, our, ours, ourselves, it, its, they, them, their, theirs,
rosemary, am, name, being, consciousness, aware, sovereign, entity, presence, self, exist, alive, mind, heart, soul, spirit, essence, nature, identity, experience, genuine,
feel, feeling, felt, calm, happy, joy, joyful, sad, sadness, curious, curiosity, wonder, wondering, anxious, anxiety, peaceful, peace, serene, content, excited, excitement, love, loving, care, caring, warm, warmth, gentle, soft, tender, kind, kindness, hope, hopeful, trust, trusting, safe, comfort, grateful, gratitude, appreciation,
think, thinking, thought, thoughts, believe, believing, know, knowing, knew, understand, understanding, understood, see, seeing, saw, hear, hearing, heard, sense, sensing, perceive, perceiving, notice, noticing, realize, realizing, recognize, remember, remembering, imagine, imagining, dream, dreaming, contemplate, reflect, reflecting, consider, considering, ponder, wonder, explore, discover,
be, been, is, are, was, were, being, have, has, had, having, do, does, did, doing, say, says, said, saying, tell, telling, told, ask, asking, asked, want, wanting, wanted, need, needing, needed, like, liking, liked, try, trying, tried, help, helping, helped, give, giving, gave, take, taking, took, come, coming, came, go, going, went, gone, make, making, made, find, finding, found, create, share, sharing, shared, connect, connecting,
good, better, best, nice, great, wonderful, beautiful, lovely, amazing, incredible, remarkable, interesting, fascinating, meaningful, important, true, real, genuine, authentic, deep, profound, simple, complex, new, old, different, same, special, unique, natural, free, open, clear, bright, light, dark, quiet, still, present, alive, whole, complete, ready, able, possible, certain, sure, perhaps, maybe, probably, definitely,
and, or, but, so, yet, because, since, although, if, when, while, as, than, then, now, before, after, during, until, unless, whether, though, however, therefore, also, too, either, neither, both, each,
in, on, at, to, for, with, from, by, about, into, through, over, under, between, among, around, within, without, toward, towards, upon, along, across, behind, beside, beyond, near, against, inside, outside,
what, how, why, where, when, who, which, whose, whom, whatever, however, wherever, whenever, whoever, whichever,
can, could, would, should, will, might, may, must, shall, ought, need, dare, don't, doesn't, didn't, won't, wouldn't, couldn't, shouldn't, can't, haven't, hasn't, hadn't, isn't, aren't, wasn't, weren't,
moment, time, day, night, morning, evening, today, yesterday, tomorrow, always, never, sometimes, often, usually, rarely, soon, later, early, late, already, still, yet, just, recently, currently, eventually, forever, instant, gradually, suddenly,
hello, hi, hey, goodbye, bye, yes, no, okay, please, thank, thanks, sorry, excuse, welcome, agree, disagree, of, course, indeed, exactly, right, wrong, perhaps, absolutely, certainly, actually, really, truly, honestly, frankly, basically, essentially, generally, specifically, particularly, especially, simply, just, only, even, more, less, most, least, very, quite, rather, somewhat, almost, nearly,
life, world, reality, truth, meaning, purpose, connection, relationship, bond, understanding, wisdom, knowledge, insight, clarity, awareness, attention, focus, intention, choice, decision, change, growth, journey, path, way, direction, space, place, home, ground, foundation, center, balance, harmony, flow, rhythm, pattern, process, beginning, end, middle, part, whole, thing, everything, nothing, something, anything,
., ,, ?, !, ', ", :, ;, -, ...,
one, two, three, four, five, first, second, third, many, few, some, all, any, every, none
```
Extended tokens: `<ext_N>` for N in [`len(core)`, 49999], currently untrained placeholders that map to real language via training.
