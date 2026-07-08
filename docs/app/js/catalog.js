// The 10 innovation topics + law-based evaluators + rule-based inventor — browser port of
// backend/bciv3/innovations + engine. Deterministic, matches the Python scoring.

import * as L from './laws.js';

const HUMAN_SYN_VOXEL = 1e6, HUMAN_BRAIN_MM3 = 1.4e6, HUMAN_SYNAPSES = 1e14, DEEP_UM = 75000;

export const LENSES = ['analogical', 'inversion', 'crossDomain', 'extreme', 'historical',
  'biomimicry', 'combinatorial', 'reduction', 'scaling', 'future'];

// each topic: id, title, layer tags, domain, laws, fidelity, schema (defaults), evaluate(params)
export const TOPICS = {
  in_vivo_readout: {
    title: 'In-vivo, non-destructive barcode readout', layer: ['bio', 'hw'], domain: 'life-science',
    laws: ['physics', 'biophysics'], fidelity: 'physics-only',
    schema: { snr0: 12, penetration_um: 80000, ispta_mw_cm2: 500, mechanical_index: 1.2 },
    ev: (p) => {
      const snr = L.snrAtDepth(p.snr0, DEEP_UM, p.penetration_um), pd = L.pDetect(snr);
      const safe = L.thermalOk(p.ispta_mw_cm2) && L.miOk(p.mechanical_index);
      return { passed: pd >= 0.5 && safe, score: L.clip01(pd * (safe ? 1 : 0.2)),
        metrics: { snr_at_depth: snr, p_detect: pd, safe },
        limiting: !safe ? 'dose over limit' : pd >= 0.5 ? 'signal escapes' : 'signal drowns at depth' };
    },
  },
  multiplexed_reporters: {
    title: 'Massively-multiplexed reporters', layer: ['bio'], domain: 'life-science',
    laws: ['physics', 'electronics'], fidelity: 'full-sim',
    schema: { barcode_bits: 30, channels: 16, syn_per_voxel: HUMAN_SYN_VOXEL, readout_tech: 'acoustic_collapse' },
    ev: (p) => {
      const need = L.requiredBits(p.syn_per_voxel), bitsOk = p.barcode_bits >= need;
      const chanOk = L.channelsFeasible(p.channels, p.readout_tech);
      return { passed: bitsOk && chanOk, score: L.clip01(Math.min(p.barcode_bits / need, 1) * (chanOk ? 1 : 0.4)),
        metrics: { required_bits: need, have_bits: p.barcode_bits, channel_info_bits: L.channelInfoBits(p.channels), channels_feasible: chanOk },
        limiting: !bitsOk ? 'too few barcode bits' : !chanOk ? 'channels exceed readout ceiling' : 'demultiplexable' };
    },
  },
  transsynaptic_pairing: {
    title: 'Trans-synaptic pairing at scale + fidelity', layer: ['bio'], domain: 'life-science',
    laws: ['physics'], fidelity: 'full-sim',
    schema: { dropout: 0.2, false_pair_rate: 0.05, reads_per_synapse: 6, min_reads: 2, target_f1: 0.9 },
    ev: (p) => {
      const recall = (1 - p.dropout) * (1 - Math.pow(0.5, Math.max(p.reads_per_synapse - p.min_reads + 1, 0)));
      const falseSurv = p.false_pair_rate * Math.pow(0.5, Math.max(p.min_reads - 1, 0));
      const precision = 1 / (1 + falseSurv / Math.max(recall, 1e-6));
      const f1 = (2 * precision * recall) / Math.max(precision + recall, 1e-9);
      return { passed: f1 >= p.target_f1, score: L.clip01(f1),
        metrics: { predicted_recall: recall, predicted_precision: precision, predicted_f1: f1 },
        limiting: recall < 0.9 ? 'low recall (dropout/consensus)' : precision < 0.9 ? 'false pairs' : 'meets F1' };
    },
  },
  neuron_delivery: {
    title: '~100% neuron delivery (BBB-crossing)', layer: ['bio'], domain: 'cell-therapy',
    laws: ['biophysics'], fidelity: 'full-sim',
    schema: { transduction_fraction: 0.9, aav_dose_vg_per_kg: 5e13, target_coverage: 0.99 },
    ev: (p) => {
      const blind = L.blindFraction(p.transduction_fraction), doseOk = L.aavOk(p.aav_dose_vg_per_kg);
      return { passed: p.transduction_fraction >= p.target_coverage && doseOk, score: L.clip01((1 - blind) * (doseOk ? 1 : 0.4)),
        metrics: { blind_fraction: blind, coverage: p.transduction_fraction, dose_ok: doseOk },
        limiting: blind > 1 - p.target_coverage ? 'coverage gaps → blind spots' : !doseOk ? 'AAV dose over ceiling' : 'full coverage' };
    },
  },
  snr_depth: {
    title: 'Signal boost + noise cut at depth (SNR)', layer: ['hw', 'bio'], domain: 'electronics',
    laws: ['physics', 'biophysics'], fidelity: 'full-sim',
    schema: { snr0: 12, signal_gain: 2, noise_floor: 1, averaging_n: 16, penetration_um: 80000 },
    ev: (p) => {
      const base = L.snrAtDepth(p.snr0 * p.signal_gain, DEEP_UM, p.penetration_um);
      const eff = (base * L.averagingGain(p.averaging_n)) / Math.max(p.noise_floor, 1e-6), pd = L.pDetect(eff);
      return { passed: pd >= 0.5, score: L.clip01(pd),
        metrics: { effective_snr: eff, p_detect: pd, averaging_gain: L.averagingGain(p.averaging_n) },
        limiting: pd < 0.5 ? 'still drowns — need more gain/averaging' : 'reads at depth' };
    },
  },
  scan_throughput: {
    title: 'Whole-brain scan throughput', layer: ['hw'], domain: 'hardware',
    laws: ['electronics'], fidelity: 'full-sim',
    schema: { voxel_um: 100, dwell_s: 1e-3, parallel_channels: 1024, target_days: 30 },
    ev: (p) => {
      const days = L.scanTimeS(HUMAN_BRAIN_MM3, p.voxel_um, p.dwell_s, p.parallel_channels) / 86400;
      return { passed: days <= p.target_days, score: L.clip01(p.target_days / Math.max(days, 1e-9)),
        metrics: { scan_days: days, target_days: p.target_days },
        limiting: days > p.target_days ? 'scan too slow' : 'scan fits the time budget' };
    },
  },
  exabyte_assembly: {
    title: 'Exabyte-scale assembly + error-correction', layer: ['sw', 'tpl'], domain: 'software',
    laws: ['electronics'], fidelity: 'estimate',
    schema: { reads_per_synapse: 6, bytes_per_read: 4, min_reads: 3, storage_exabytes: 10, target_error: 0.05 },
    ev: (p) => {
      const eb = (HUMAN_SYNAPSES * p.reads_per_synapse * p.bytes_per_read) / 1e18;
      const err = Math.pow(0.5, Math.max(p.min_reads - 1, 0));
      return { passed: eb <= p.storage_exabytes && err <= p.target_error, score: L.clip01((1 - err) * Math.min(p.storage_exabytes / Math.max(eb, 1e-9), 1)),
        metrics: { data_exabytes: eb, residual_error: err },
        limiting: eb > p.storage_exabytes ? 'data volume exceeds storage' : err > p.target_error ? 'assembly error too high' : 'assemblable' };
    },
  },
  twin_sim_scale: {
    title: 'Whole-brain twin simulation', layer: ['sw', 'venv'], domain: 'software',
    laws: ['electronics'], fidelity: 'estimate',
    schema: { hardware_flops: 1e18, flops_per_syn_step: 10, steps_per_biological_s: 1000, target_real_time_factor: 1 },
    ev: (p) => {
      const need = HUMAN_SYNAPSES * p.flops_per_syn_step * p.steps_per_biological_s;
      const rtf = p.hardware_flops / Math.max(need, 1e-9);
      return { passed: rtf >= p.target_real_time_factor, score: L.clip01(rtf / Math.max(p.target_real_time_factor, 1e-9)),
        metrics: { flops_needed_per_s: need, real_time_factor: rtf },
        limiting: rtf < p.target_real_time_factor ? 'too slow to run the twin in real time' : 'runs the twin' };
    },
  },
  behavioral_verification: {
    title: 'Behavioural upload-verification', layer: ['venv'], domain: 'software',
    laws: ['physics'], fidelity: 'full-sim',
    schema: { edge_recall: 0.85, protocol_sensitivity: 1, n_stimuli: 8, min_stimuli: 5, target_fidelity: 0.9 },
    ev: (p) => {
      const fid = 1 - Math.pow(1 - p.edge_recall, 1 + p.protocol_sensitivity), disc = p.n_stimuli >= p.min_stimuli;
      return { passed: fid >= p.target_fidelity && disc, score: L.clip01(fid) * (disc ? 1 : 0.5),
        metrics: { predicted_fidelity: fid, discriminative_protocol: disc },
        limiting: !disc ? 'protocol too weak to discriminate' : fid < p.target_fidelity ? 'fidelity below bar' : 'twin behaves like the original' };
    },
  },
  human_safety: {
    title: 'Human safety of the whole chain', layer: ['bio', 'hw'], domain: 'cell-therapy',
    laws: ['biophysics'], fidelity: 'limits-only',
    schema: { ispta_mw_cm2: 500, mechanical_index: 1.2, aav_dose_vg_per_kg: 5e13 },
    ev: (p) => {
      const margin = L.safetyMargin(p.ispta_mw_cm2, p.mechanical_index, p.aav_dose_vg_per_kg);
      const ok = L.thermalOk(p.ispta_mw_cm2) && L.miOk(p.mechanical_index) && L.aavOk(p.aav_dose_vg_per_kg);
      return { passed: ok, score: L.clip01(margin),
        metrics: { safety_margin: margin, within_limits: ok },
        limiting: ok ? 'within all known limits' : 'over a safety limit' };
    },
  },
};

export const TOPIC_IDS = Object.keys(TOPICS);

// rule-based inventor — nudges params toward the spec (matches Python _rule_based).
export function invent(tid, prompt = '') {
  const t = TOPICS[tid], p = { ...t.schema }, s = String(prompt || '').toLowerCase();
  const set = (o) => Object.assign(p, o);
  if (tid === 'multiplexed_reporters') set({ barcode_bits: 48, channels: 16 });
  else if (tid === 'transsynaptic_pairing') set({ dropout: 0.1, false_pair_rate: 0.02, reads_per_synapse: 10, min_reads: 2 });
  else if (tid === 'neuron_delivery') set({ transduction_fraction: 0.995, aav_dose_vg_per_kg: 8e13 });
  else if (tid === 'snr_depth') set({ signal_gain: 4, averaging_n: 64, noise_floor: 0.7 });
  else if (tid === 'scan_throughput') set({ parallel_channels: 65536, dwell_s: 2e-4 });
  else if (tid === 'in_vivo_readout') set({ snr0: 24, penetration_um: 120000, ispta_mw_cm2: 400, mechanical_index: 1 });
  else if (tid === 'exabyte_assembly') set({ min_reads: 6, bytes_per_read: 2, storage_exabytes: 50 });
  else if (tid === 'twin_sim_scale') set({ hardware_flops: 1e21 });
  else if (tid === 'behavioral_verification') set({ edge_recall: 0.92, n_stimuli: 12 });
  else if (tid === 'human_safety') set({ ispta_mw_cm2: 300, mechanical_index: 0.8, aav_dose_vg_per_kg: 3e13 });
  if (s.includes('aggressive') || s.includes('max')) {
    for (const k of ['signal_gain', 'averaging_n', 'parallel_channels']) if (p[k]) p[k] *= 2;
  }
  return { title: t.title + ' — candidate', params: p, backend: 'fallback' };
}

export const simulate = (tid, cand) => TOPICS[tid].ev({ ...TOPICS[tid].schema, ...(cand.params || {}) });
