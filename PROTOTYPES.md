# Prototypes — six curated end-to-end builds

Six hand-picked, one-invention-per-topic combinations fused from the invention library (`inventions_export.json`). Each is internally *coherent* — the readout physics chains end-to-end — not just a pile of top scores. Two designs win their category outright and appear in most builds: **NeuroTune** (real BI-hTFR1 capsid + FUS BBB-opening, 0.995 coverage at a dose 6 orders under the ceiling) and **FlyConnectomeAssembly** (genome-assembly + error-correcting codes, the only efficient passing assembler).

Build any of them with a single command:

```bash
bci synthesize --preset echo       # or lumen | swift | guardian | titan | vanguard
bci synthesize --list-presets      # show all six with descriptions
```

The same presets are available in the API (`POST /api/synthesize {"preset":"echo"}`) and resolve to the exact per-topic invention ids below. If an id is missing from your local database, synthesis falls back to the best passing design for that topic, so a preset never hard-fails.

> **Note on the Human-safety score.** It reads low (~0.05–0.21) because it is the *safety margin below the FDA ceilings*, not a pass/fail — every safety pick here PASSES. Higher = more headroom.


## ECHO
*fully-acoustic coherent flagship*

Every stage chains through ultrasound / photoacoustic: the FUS reader reads the gas-vesicle barcodes, BCCA bridges light→sound, and the same acoustic lens both delivers the vector and holds the safety envelope. The strongest *and* most physically-consistent build — synthesize this one first.

| Phase | Topic | Invention | Lens | Score | id |
|---|---|---|---|---|---|
| Label | Neuron delivery | NeuroTune | crossDomain | 0.995 | `86b7d686` |
| Label | Multiplexed reporters | BrainCode | combinatorial | 1.0 | `86eaca96` |
| Read | In-vivo readout | FUS-Gas Vesicle Barcode Reader | crossDomain | 0.9491 | `0f1197e2` |
| Read | SNR at depth | Bioluminescent Cascade Amplification (BCCA) | biomimicry | 1.0 | `46262b29` |
| Read | Scan throughput | Ultra-High-Throughput Non-Invasive Whole-Brain Scanner (UHNT-WB) | scaling | 1.0 | `7c936d9d` |
| Map | Trans-synaptic pairing | Tokenized Synaptic Pairing (TSP) | inversion | 0.9699 | `48cce68c` |
| Map | Exabyte assembly | FlyConnectomeAssembly | crossDomain | 0.9922 | `01147130` |
| Emulate | Twin simulation | Whole-Brain Twin Simulation (WBTSS) | crossDomain | 1.0 | `dc016952` |
| Emulate | Behavioural verification | Neural Echo Chamber | crossDomain | 0.9973 | `f5d5329c` |
| Safety | Human safety | Transcranial Focused Ultrasound-Guided AAV Delivery | reduction | 0.2105 | `a8bc6f9c` |

## LUMEN
*optical / highest-resolution*

The fluorescence paradigm pushed for maximum signal and the finest voxels (5 µm). Deeper-penetration reader, 20× signal gain with heavy averaging, spectral-optical barcodes with 32-channel headroom.

| Phase | Topic | Invention | Lens | Score | id |
|---|---|---|---|---|---|
| Label | Neuron delivery | NeuroTune | crossDomain | 0.995 | `86b7d686` |
| Label | Multiplexed reporters | Neuromap | scaling | 1.0 | `6e460af6` |
| Read | In-vivo readout | DeepBar | extreme | 0.9341 | `e7f51413` |
| Read | SNR at depth | DeepBrainBoost | analogical | 0.9986 | `adb40a36` |
| Read | Scan throughput | BrainMapX | future | 1.0 | `82a8b62d` |
| Map | Trans-synaptic pairing | SynSeq++ | historical | 0.956 | `ad87571b` |
| Map | Exabyte assembly | FlyConnectomeAssembly | crossDomain | 0.9922 | `01147130` |
| Emulate | Twin simulation | WholeBrainTwinSim | future | 1.0 | `ec043635` |
| Emulate | Behavioural verification | Neural Echo Chamber | crossDomain | 0.9973 | `f5d5329c` |
| Safety | Human safety | Transcranial Focused Ultrasound-Guided AAV Delivery | crossDomain | 0.2 | `8594ace0` |

## SWIFT
*lean / fast / minimal-hardware*

The pragmatic first-buildable: fewest reads, least averaging, smallest reporter set, maximum scan parallelism → shortest scan and smallest data footprint. Everything trimmed to the minimum that still passes.

| Phase | Topic | Invention | Lens | Score | id |
|---|---|---|---|---|---|
| Label | Neuron delivery | NeuroThru | reduction | 0.99 | `1b05dc26` |
| Label | Multiplexed reporters | Non-Invasive Brain-Mapping Barcode | reduction | 1.0 | `89a7a508` |
| Read | In-vivo readout | FUS-Gas Vesicle Barcode Reader | crossDomain | 0.9491 | `0f1197e2` |
| Read | SNR at depth | Neuromap 75k | extreme | 0.9635 | `e3d4d2c2` |
| Read | Scan throughput | WholeBrainMapper | scaling | 1.0 | `aa8d0f1a` |
| Map | Trans-synaptic pairing | SynSeq++ | historical | 0.956 | `ad87571b` |
| Map | Exabyte assembly | FlyConnectomeAssembly | crossDomain | 0.9922 | `01147130` |
| Emulate | Twin simulation | Whole-Brain Twin Simulation (WBTSS) | crossDomain | 1.0 | `dc016952` |
| Emulate | Behavioural verification | BrainMapNet | reduction | 0.9969 | `428e2cf1` |
| Safety | Human safety | Acoustic Lens-guided AAV Delivery | extreme | 0.2 | `fe85e960` |

## GUARDIAN
*clinical-safety-first*

Clinical-first: the lowest ultrasound intensity, a delivery dose six orders of magnitude under the toxicity ceiling, the least viral cargo, the simplest scan hardware, and the most demanding 10,000-stimulus verification battery before any human use.

| Phase | Topic | Invention | Lens | Score | id |
|---|---|---|---|---|---|
| Label | Neuron delivery | NeuroTune | crossDomain | 0.995 | `86b7d686` |
| Label | Multiplexed reporters | Non-Invasive Brain-Mapping Barcode | reduction | 1.0 | `89a7a508` |
| Read | In-vivo readout | DeepBar | extreme | 0.9341 | `e7f51413` |
| Read | SNR at depth | Bioluminescent Cascade Amplification (BCCA) | biomimicry | 1.0 | `46262b29` |
| Read | Scan throughput | WholeBrainMapper | extreme | 1.0 | `29c0acef` |
| Map | Trans-synaptic pairing | SynSeq++ | historical | 0.956 | `ad87571b` |
| Map | Exabyte assembly | FlyConnectomeAssembly | crossDomain | 0.9922 | `01147130` |
| Emulate | Twin simulation | WholeBrainSim | scaling | 1.0 | `a9db8d21` |
| Emulate | Behavioural verification | Neural Echo Chamber | crossDomain | 0.9973 | `f5d5329c` |
| Safety | Human safety | Transcranial Focused Ultrasound-Guided AAV Delivery | reduction | 0.2105 | `a8bc6f9c` |

## TITAN
*maximum performance / brute-force*

No compromise: the highest-scoring, most aggressive design in every category — brightest source, richest codebook, highest pairing fidelity, brute-force signal gain and scan parallelism.

| Phase | Topic | Invention | Lens | Score | id |
|---|---|---|---|---|---|
| Label | Neuron delivery | NeuroTune | crossDomain | 0.995 | `86b7d686` |
| Label | Multiplexed reporters | Neuromap | scaling | 1.0 | `6e460af6` |
| Read | In-vivo readout | FUS-Gas Vesicle Barcode Reader | crossDomain | 0.9491 | `0f1197e2` |
| Read | SNR at depth | DeepBrainBoost | analogical | 0.9986 | `adb40a36` |
| Read | Scan throughput | WholeBrainMapper | scaling | 1.0 | `aa8d0f1a` |
| Map | Trans-synaptic pairing | Tokenized Synaptic Pairing (TSP) | inversion | 0.9699 | `48cce68c` |
| Map | Exabyte assembly | FlyConnectomeAssembly | crossDomain | 0.9922 | `01147130` |
| Emulate | Twin simulation | WholeBrainTwinSim | future | 1.0 | `ec043635` |
| Emulate | Behavioural verification | Neural Echo Chamber | crossDomain | 0.9973 | `f5d5329c` |
| Safety | Human safety | Transcranial Focused Ultrasound-Guided AAV Delivery | crossDomain | 0.2 | `8594ace0` |

## VANGUARD
*future / most-scalable*

2050-forward: favours the future/scaling-lens designs and novel modalities (RF-broadcast readout, deep 40-read consensus, zettascale twin) — the headroom-maximizing, scale-out build.

| Phase | Topic | Invention | Lens | Score | id |
|---|---|---|---|---|---|
| Label | Neuron delivery | Thermal-Triggered AAV Delivery | scaling | 0.99 | `90c8fe5c` |
| Label | Multiplexed reporters | Neuromap | scaling | 1.0 | `6e460af6` |
| Read | In-vivo readout | DeepBrainEcho | inversion | 0.9292 | `699dc8c8` |
| Read | SNR at depth | DeepBrainBoost | analogical | 0.9986 | `adb40a36` |
| Read | Scan throughput | BrainMapX | future | 1.0 | `82a8b62d` |
| Map | Trans-synaptic pairing | SynapticEcho | combinatorial | 0.9412 | `2e82e5e1` |
| Map | Exabyte assembly | FlyConnectomeAssembly | crossDomain | 0.9922 | `01147130` |
| Emulate | Twin simulation | WholeBrainTwinSim | future | 1.0 | `ec043635` |
| Emulate | Behavioural verification | Neural Echo Chamber | crossDomain | 0.9973 | `f5d5329c` |
| Safety | Human safety | Transcranial Focused Ultrasound-Guided AAV Delivery | crossDomain | 0.2 | `8594ace0` |

---
_Generated from the invention library; see `inventions_export.json` for the full designs (mechanism, materials, protocol, parts, metrics) behind each id._
