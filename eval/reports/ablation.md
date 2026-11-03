# Coverage pipeline ablation

English/coverage pipeline ablation, NOT ISL accuracy or a live-model benchmark

simulated_api is an SDK transport fixture, using the demo glossary and real deterministic lookup in input order. No live model calls/numbers. mock ignores LLM_ORDERING; model ordering in simulated_api is a fixture, not model reasoning.

Gloss agreement/accuracy is not comprehension accuracy, naturalness, or verified ISL quality. Repository coverage includes unverified demos; verified asset coverage is separate.

Coverage here is 1 − FS-token rate (repository membership, including demos), not verified-asset coverage. Content coverage uses the documented English function-word heuristic.

| Path | Ordering | Synonyms | Language | Tokens | Coverage | FS rate | Content coverage | Verified metrics |
|---|---|---|---|---:|---:|---:|---:|---|
| mock | code | False | en-IN | 275 | 97.09% | 2.91% | 95.07% | NO_VERIFIED_ROWS |
| mock | code | False | hi-IN | 436 | 38.07% | 61.93% | 29.43% | NO_VERIFIED_ROWS |
| mock | code | False | kn-IN | 308 | 42.21% | 57.79% | 27.94% | NO_VERIFIED_ROWS |
| mock | code | True | en-IN | 275 | 98.55% | 1.45% | 98.03% | NO_VERIFIED_ROWS |
| mock | code | True | hi-IN | 436 | 38.07% | 61.93% | 29.43% | NO_VERIFIED_ROWS |
| mock | code | True | kn-IN | 308 | 42.21% | 57.79% | 27.94% | NO_VERIFIED_ROWS |
| mock | model | False | en-IN | 275 | 97.09% | 2.91% | 95.07% | NO_VERIFIED_ROWS |
| mock | model | False | hi-IN | 436 | 38.07% | 61.93% | 29.43% | NO_VERIFIED_ROWS |
| mock | model | False | kn-IN | 308 | 42.21% | 57.79% | 27.94% | NO_VERIFIED_ROWS |
| mock | model | True | en-IN | 275 | 98.55% | 1.45% | 98.03% | NO_VERIFIED_ROWS |
| mock | model | True | hi-IN | 436 | 38.07% | 61.93% | 29.43% | NO_VERIFIED_ROWS |
| mock | model | True | kn-IN | 308 | 42.21% | 57.79% | 27.94% | NO_VERIFIED_ROWS |
| simulated_api | code | False | en-IN | 275 | 97.09% | 2.91% | 95.07% | NO_VERIFIED_ROWS |
| simulated_api | code | False | hi-IN | 436 | 38.07% | 61.93% | 29.43% | NO_VERIFIED_ROWS |
| simulated_api | code | False | kn-IN | 308 | 42.21% | 57.79% | 27.94% | NO_VERIFIED_ROWS |
| simulated_api | code | True | en-IN | 298 | 89.60% | 10.40% | 98.03% | NO_VERIFIED_ROWS |
| simulated_api | code | True | hi-IN | 436 | 38.07% | 61.93% | 29.43% | NO_VERIFIED_ROWS |
| simulated_api | code | True | kn-IN | 308 | 42.21% | 57.79% | 27.94% | NO_VERIFIED_ROWS |
| simulated_api | model | False | en-IN | 394 | 67.77% | 32.23% | 95.07% | NO_VERIFIED_ROWS |
| simulated_api | model | False | hi-IN | 437 | 37.99% | 62.01% | 29.43% | NO_VERIFIED_ROWS |
| simulated_api | model | False | kn-IN | 308 | 42.21% | 57.79% | 27.94% | NO_VERIFIED_ROWS |
| simulated_api | model | True | en-IN | 394 | 67.77% | 32.23% | 98.03% | NO_VERIFIED_ROWS |
| simulated_api | model | True | hi-IN | 437 | 37.99% | 62.01% | 29.43% | NO_VERIFIED_ROWS |
| simulated_api | model | True | kn-IN | 308 | 42.21% | 57.79% | 27.94% | NO_VERIFIED_ROWS |

Environment (configured model ID is not a called model):
```json
{
  "python": "3.11.8",
  "node": "v24.13.0",
  "platform": "Windows-10-10.0.26300-SP0",
  "packages": {
    "nltk": "3.9.1",
    "pydantic": "2.9.2",
    "anthropic": "0.75.0",
    "matplotlib": "3.10.7"
  },
  "model_id_configured_not_called": "claude-sonnet-5-5",
  "seed": 20261103,
  "wordnet_zip_sha256": "cbda5ea6eef7f36a97a43d4a75f85e07fccbb4f23657d27b4ccbc93e2646ab59"
}
```
