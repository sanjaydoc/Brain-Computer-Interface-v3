// Law simulator — browser port of backend/bciv3/laws (physics · biophysics · electronics).
// Same formulas as the Python engine, so the cockpit grades designs live, client-side.

// ---- physics ----
export const MODALITIES = {
  fus:  { label: 'focused ultrasound', penetration: 80000, wavelength: 300 },
  mri:  { label: 'MRI',                penetration: 1e9,   wavelength: 1e5 },
  pet:  { label: 'PET',                penetration: 1e9,   wavelength: 1e6 },
  nirs: { label: 'near-infrared',      penetration: 3000,  wavelength: 0.9 },
};
export const requiredBits = (synPerVoxel, eps = 0.01) => {
  const k = Math.max(synPerVoxel, 1);
  return Math.ceil(Math.log2(Math.max((k * k) / (2 * Math.max(eps, 1e-9)), 2)));
};
export const snrAtDepth = (snr0, depthUm, penUm) => snr0 * Math.exp(-depthUm / Math.max(penUm, 1e-9));
export const pDetect = (snr, thr = 1) => snr / (snr + Math.max(thr, 1e-9));
export const averagingGain = (n) => Math.sqrt(Math.max(n, 1));
export const channelInfoBits = (ch) => Math.log2(Math.max(ch, 1));

// ---- biophysics ----
export const FDA_ISPTA = 720, FDA_MI = 1.9, AAV_CEIL = 1e14;
export const blindFraction = (frac) => 1 - Math.min(Math.max(frac, 0), 1);
export const thermalOk = (ispta) => ispta <= FDA_ISPTA;
export const miOk = (mi) => mi <= FDA_MI;
export const aavOk = (vg) => vg <= AAV_CEIL;
export const safetyMargin = (ispta, mi, vg) => {
  const m = Math.min(1 - ispta / FDA_ISPTA, 1 - mi / FDA_MI, 1 - vg / AAV_CEIL);
  return Math.max(0, Math.min(1, m));
};

// ---- electronics ----
export const CHANNEL_CEILING = {
  acoustic_collapse: 16, mri_relaxation: 8, pet_tracer: 6, spectral_optical: 32, sequencing: 1e6,
};
export const channelsFeasible = (ch, tech) => ch <= (CHANNEL_CEILING[tech] ?? 8);
export const scanTimeS = (volMm3, voxelUm, dwellS, parallel) => {
  const voxelMm3 = Math.pow(voxelUm / 1000, 3);
  const nVox = volMm3 / Math.max(voxelMm3, 1e-12);
  return (nVox * dwellS) / Math.max(parallel, 1);
};

export const clip01 = (x) => Math.max(0, Math.min(1, x));
