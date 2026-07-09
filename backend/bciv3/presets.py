"""Prototype presets — curated 1-invention-per-topic combinations for `bci synthesize --preset`.

Each preset is a hand-picked, internally-coherent selection across the 10 blockers (see PROTOTYPES.md
for the reasoning). The ids are the saved-record ids from the invention library; if an id is not in
the local database, synthesis falls back to the best passing record for that topic, so a preset never
hard-fails — it just degrades to "best available" for any missing pick.
"""

from __future__ import annotations

# name → {topic: invention_id}
PRESETS: dict[str, dict[str, str]] = {
    # ECHO — fully-acoustic coherent flagship (every stage chains through ultrasound / photoacoustic)
    "echo": {
        "in_vivo_readout":        "0f1197e212974511a7bda4ba3a268017",  # FUS-Gas Vesicle Reader
        "multiplexed_reporters":  "86eaca967e384847a3fcb73a705d4f01",  # BrainCode (acoustic_collapse)
        "transsynaptic_pairing":  "48cce68c79e74f3791f17e16eafb07a8",  # TSP — Tokenized Pairing
        "neuron_delivery":        "86b7d686db3843d297a4861f6eb42c0d",  # NeuroTune (BI-hTFR1 + FUS)
        "snr_depth":              "46262b29f6c247ab9f592bbbcc015b62",  # BCCA (photoacoustic bridge)
        "scan_throughput":        "7c936d9d30ca481c8a172f65c9b069cf",  # UHNT-WB (micro-ultrasound array)
        "exabyte_assembly":       "011471303b6c42a4b0910970f41bbd13",  # FlyConnectomeAssembly
        "twin_sim_scale":         "dc016952e7e14dfa98e574b77a4dfc92",  # WBTSS (GPU sparse kernels)
        "behavioral_verification":"f5d5329c708d4298b730299923f2dc15",  # Neural Echo Chamber (10k stimuli)
        "human_safety":           "a8bc6f9ccb2647028ece7e2ecc17c3fa",  # TFUS acoustic-lens (ISPTA 360)
    },
    # LUMEN — optical / highest-resolution (fluorescence paradigm, 5 µm voxels, max signal gain)
    "lumen": {
        "in_vivo_readout":        "e7f51413d1c740a1a4aabb23b00ba447",  # DeepBar (100 mm penetration)
        "multiplexed_reporters":  "6e460af65a44444f9262a588e6166db4",  # Neuromap (spectral_optical)
        "transsynaptic_pairing":  "ad87571b641f49098b4983baff5d23c6",  # SynSeq++ (optogenetic)
        "neuron_delivery":        "86b7d686db3843d297a4861f6eb42c0d",  # NeuroTune
        "snr_depth":              "adb40a36bb624ceca3207bc996954b82",  # DeepBrainBoost (20x gain, 100-avg)
        "scan_throughput":        "82a8b62da31941418e8da599c629eca8",  # BrainMapX (5 µm voxel)
        "exabyte_assembly":       "011471303b6c42a4b0910970f41bbd13",  # FlyConnectomeAssembly
        "twin_sim_scale":         "ec04363570b9457185319d2e76b3bde6",  # WholeBrainTwinSim
        "behavioral_verification":"f5d5329c708d4298b730299923f2dc15",  # Neural Echo Chamber
        "human_safety":           "8594ace0e0174a569b0cf72796ac7c61",  # TFUS-Guided AAV
    },
    # SWIFT — lean / fast / minimal-hardware (fewest reads, least averaging, max scan parallelism)
    "swift": {
        "in_vivo_readout":        "0f1197e212974511a7bda4ba3a268017",  # FUS-Gas Vesicle Reader
        "multiplexed_reporters":  "89a7a50832ba46529f2d4dff5f4b702f",  # Minimum Barcode set (reduction)
        "transsynaptic_pairing":  "ad87571b641f49098b4983baff5d23c6",  # SynSeq++ (7 reads, leanest)
        "neuron_delivery":        "1b05dc26b7fc4b4f97061b8a887e1797",  # NeuroThru (smallest recipe)
        "snr_depth":              "e3d4d2c25303461bb11304d81d12f9c0",  # Neuromap 75k (avg 9, fastest dwell)
        "scan_throughput":        "aa8d0f1af1c4462e9c7205dcecffea05",  # WholeBrainMapper (1e6 channels)
        "exabyte_assembly":       "011471303b6c42a4b0910970f41bbd13",  # FlyConnectomeAssembly
        "twin_sim_scale":         "dc016952e7e14dfa98e574b77a4dfc92",  # WBTSS
        "behavioral_verification":"428e2cf105df4d6c877138ba90b4cdfa",  # BrainMapNet (128 stimuli, leanest)
        "human_safety":           "fe85e96021714693ac5b91ffb5dd4654",  # Acoustic Lens (lowest MI 1.4)
    },
    # GUARDIAN — clinical-safety-first (lowest intensity/dose, minimal cargo, most rigorous verification)
    "guardian": {
        "in_vivo_readout":        "e7f51413d1c740a1a4aabb23b00ba447",  # DeepBar (lowest ISPTA 450)
        "multiplexed_reporters":  "89a7a50832ba46529f2d4dff5f4b702f",  # Minimum Barcode set (least viral cargo)
        "transsynaptic_pairing":  "ad87571b641f49098b4983baff5d23c6",  # SynSeq++ (switchable optogenetic tags)
        "neuron_delivery":        "86b7d686db3843d297a4861f6eb42c0d",  # NeuroTune (dose 1e7 — 6 orders under ceiling)
        "snr_depth":              "46262b29f6c247ab9f592bbbcc015b62",  # BCCA (brighter reporters → less acoustic power)
        "scan_throughput":        "29c0acef6a37441aa3578226508f442b",  # WholeBrainMapper extreme (2,400 channels, low power)
        "exabyte_assembly":       "011471303b6c42a4b0910970f41bbd13",  # FlyConnectomeAssembly
        "twin_sim_scale":         "a9db8d21ba4b460bac105282057fbcf4",  # WholeBrainSim
        "behavioral_verification":"f5d5329c708d4298b730299923f2dc15",  # Neural Echo Chamber (10k stimuli — max rigor)
        "human_safety":           "a8bc6f9ccb2647028ece7e2ecc17c3fa",  # TFUS acoustic-lens (ISPTA 360, best margin)
    },
    # TITAN — maximum performance / brute-force (highest raw scores, most aggressive signal & coverage)
    "titan": {
        "in_vivo_readout":        "0f1197e212974511a7bda4ba3a268017",  # FUS-Gas Vesicle (snr0 50, top score)
        "multiplexed_reporters":  "6e460af65a44444f9262a588e6166db4",  # Neuromap (spectral_optical, 32-ch max codespace)
        "transsynaptic_pairing":  "48cce68c79e74f3791f17e16eafb07a8",  # TSP (highest fidelity 0.970)
        "neuron_delivery":        "86b7d686db3843d297a4861f6eb42c0d",  # NeuroTune
        "snr_depth":              "adb40a36bb624ceca3207bc996954b82",  # DeepBrainBoost (20x gain, 100-avg brute force)
        "scan_throughput":        "aa8d0f1af1c4462e9c7205dcecffea05",  # WholeBrainMapper (1e6 channels, max parallel)
        "exabyte_assembly":       "011471303b6c42a4b0910970f41bbd13",  # FlyConnectomeAssembly
        "twin_sim_scale":         "ec04363570b9457185319d2e76b3bde6",  # WholeBrainTwinSim
        "behavioral_verification":"f5d5329c708d4298b730299923f2dc15",  # Neural Echo Chamber (10k stimuli)
        "human_safety":           "8594ace0e0174a569b0cf72796ac7c61",  # TFUS-Guided AAV (higher power budget, in-limits)
    },
    # VANGUARD — future / most-scalable (2050-forward, headroom-maximizing, novel-modality picks)
    "vanguard": {
        "in_vivo_readout":        "699dc8c80793420cbf9668a4e22ef898",  # DeepBrainEcho (RF-broadcast, novel modality)
        "multiplexed_reporters":  "6e460af65a44444f9262a588e6166db4",  # Neuromap (scaling lens, spectral codebook)
        "transsynaptic_pairing":  "2e82e5e194b84ab4ad50b85dfcfab1c5",  # SynapticEcho (deep 40-read consensus)
        "neuron_delivery":        "90c8fe5c944e44ceaf33ed46b33ba21e",  # Thermal-Triggered AAV (scaling lens)
        "snr_depth":              "adb40a36bb624ceca3207bc996954b82",  # DeepBrainBoost (scale-out averaging)
        "scan_throughput":        "82a8b62da31941418e8da599c629eca8",  # BrainMapX (future lens, 5 µm voxel)
        "exabyte_assembly":       "011471303b6c42a4b0910970f41bbd13",  # FlyConnectomeAssembly
        "twin_sim_scale":         "ec04363570b9457185319d2e76b3bde6",  # WholeBrainTwinSim (future lens, zettascale)
        "behavioral_verification":"f5d5329c708d4298b730299923f2dc15",  # Neural Echo Chamber (10k stimuli)
        "human_safety":           "8594ace0e0174a569b0cf72796ac7c61",  # TFUS-Guided AAV
    },
}

# one-line description per preset (shown in `bci synthesize --list-presets`)
PRESET_INFO: dict[str, str] = {
    "echo":     "fully-acoustic coherent flagship — every stage chains through ultrasound/photoacoustic (recommended)",
    "lumen":    "optical / highest-resolution — fluorescence paradigm, 5 µm voxels, max signal gain",
    "swift":    "lean / fast / minimal-hardware — fewest reads, least averaging, max scan parallelism",
    "guardian": "clinical-safety-first — lowest intensity/dose, minimal cargo, most rigorous verification",
    "titan":    "maximum performance / brute-force — highest raw scores, most aggressive signal & coverage",
    "vanguard": "future / most-scalable — 2050-forward, headroom-maximizing, novel-modality picks",
}


def get(name: str) -> dict[str, str] | None:
    """Return the {topic: id} selection for a preset name (case-insensitive), or None if unknown."""
    return PRESETS.get((name or "").strip().lower())


def names() -> list[str]:
    return list(PRESETS)
