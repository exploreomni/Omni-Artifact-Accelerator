# Provenance of the bounded Topic modeler

The source review used the public Data Model Accelerator checkout at commit `593bd2117ba99fb34bdd7ce5b2f97510c13384e7`. The OAA implementation adapts DMA's original scoped modeling guidance for existing physical bindings, Topic-scoped measures, explicit join paths, access policy, and candidate-bound validation. Its Python implementation and synthetic order/account fixture are written for OAA. Updating this reference requires reviewing the applicable object shapes and rerunning the scoped tests. [Pinned DMA source](https://github.com/exploreomni/Data-Model-Accelerator/tree/593bd2117ba99fb34bdd7ce5b2f97510c13384e7)

| Reviewed DMA path | SHA-256 of its bytes |
|---|---|
| `skills/data-model-semantic/SKILL.md` | `b25bd61f8dcf9c37b7edd5f1c9624b51047390b587e42cb8531b0421e46f5ff1` |
| `skills/data-model-accelerator/references/omni-modeler-joins-topics.md` | `d8eb6881a7f8413c3727ec109cd6ea316942426767f18265fc954b2992f1ee72` |
| `skills/data-model-accelerator/references/omni-modeler-fields.md` | `de4dd5355344d9c388fc9515f20e9d7f7871b7fa4fabce51b203f0cb403deaf8` |
| `skills/data-model-accelerator/examples/looker-omni-e2e/target/omni/billing.topic` | `8778b851ec7ea7c8dc532571d5a5979746c49261e162df0c55d27b5b7a2bb1e0` |
| `skills/data-model-accelerator/examples/looker-omni-e2e/target/omni/relationships` | `f85bd6a245b4aab2b729d4f243d156a5d6b43573ac0e019d7208698f13da2c29` |
| `docs/adr/omni-modeler-composition.md` | `3f46ae12703a991605064a415f090527489c95d001767a6282078f484d295ceb` |
| `LICENSE` | `8d3d8a26428a9e1a7d39b7d56b16135f3162df8f01b0aa6b4e6c0fe2a8731413` |

Retain the [DMA MIT permission and copyright notice](LICENSE-DMA.txt) with redistributions of the adapted material. DMA's pinned Apache-licensed external agent manuals, third-party schemas and datasets are outside this adaptation. The OAA converter uses the Python standard library and the existing OAA translator's emitted inventory interface. Source checks establish local compatibility only. The selected native branch and effective viewer roles require independent verification.
