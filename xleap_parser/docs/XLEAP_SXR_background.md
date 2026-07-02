# XLEAP on the LCLS SXR line — physics & engineering background

*Synthesized from a fan-out deep-research pass (web search → fetch → 3-vote adversarial
verification → synthesis). Every load-bearing statement below survived verification against a
primary source; claims that were refuted or only weakly sourced are flagged as such. Scope:
**SXR (soft X-ray) line only**, per project decision.*

---

## 0. TL;DR for this codebase

- **XLEAP** = *X-ray Laser-Enhanced Attosecond Pulse generation*: an LCLS operating mode that
  produces isolated **soft X-ray attosecond pulses** (~200–500 as, tens of GW, tens of µJ) in
  the **400–1000 eV** band. Our ~530 eV working point sits inside this band.
- The "hockey-stick" **K-taper** the detector looks for is the physical mechanism that keeps the
  FEL **resonant with the energy-chirped current spike** as radiation slips ahead of the
  electrons. This is textbook chirp-taper matching, and it is exactly the resonance condition
  `λ_r = (λ_u/2γ²)(1 + K²/2)` the notebook derives.
- **Two undulator generations exist and must not be conflated** (this bit the research pass):
  - *Original LCLS* undulators: **3 cm period, fixed-gap-ish, K ≈ 3.44–3.51** — used in the
    **2020 Duris XLEAP demonstration**.
  - *Current LCLS-II SXR line*: **39 mm period, variable-gap, K up to ~5.3–5.48**, **21 segments**,
    **3.4 m** each — this is what our archived `USEG:UNDS:*:KAct` snapshots and `L_u = 3.4 m`
    correspond to. The notebook's K≈5.3 ramps are consistent with this line.

---

## 1. The XLEAP scheme

**Goal.** XLEAP aims to generate sub-fs pulses in **400–1000 eV**
(Cryan/Marinelli et al., *Phil. Trans. R. Soc. A* 2019, PMC6452055 — verified verbatim).

**Mechanism (ESASE / current spike).** From Duris et al., *Nature Photonics* **14**, 30 (2020)
(DOI 10.1038/s41566-019-0549-5, "Tunable isolated attosecond X-ray pulses with gigawatt peak
power"), verified verbatim:

1. The electron beam's **energy distribution is modulated** by resonant interaction with a
   high-power infrared field in a **long-period wiggler**.
2. A **magnetic chicane** converts that energy modulation into one or more **high-current
   (~10 kA) spikes**.
3. The spike **lases in the undulator** → short X-ray pulse. This is **ESASE** (enhanced SASE).

**The key twist actually demonstrated.** Rather than an *external* IR laser (Zholents's original
proposal), the 2020 demo used the **coherent IR radiation emitted by the tail ("horn") of the
beam itself** in the wiggler to modulate the core. This produces a **phase-stable,
quasi-single-cycle** modulation and **naturally a single** high-current spike → an **isolated**
attosecond pulse. Corroborated by the companion paper MacArthur et al., *PRL* **123**, 214801
(2019) ("Phase-stable self-modulation of an electron beam in a magnetic wiggler"), which
describes a six-period CEP-stable IR field producing a few-MeV phase-stable core modulation.

> ⚠️ **Verification catch:** the wiggler period is **35 cm** in the Duris 2020 paper (Fig. 1),
> *not* 32 cm — the 32 cm figure comes from a separate variable-gap-wiggler design description
> (K up to ~52, 2 µm Ho:YLF option). Both float around the literature; don't mix them.

**Modulation can be driven two ways** (Cryan/Lutman review, verified): a **2 µm Ho:YLF laser**,
*or* **self-modulation** by the beam's own coherent undulator radiation.

**Demonstrated performance (Duris 2020, verified):** median **284 as at 905 eV**, **476 as at
570 eV**; tens of GW peak power (peaks >100 GW); tens of µJ (highest median ~50 µJ); pulse energy
~**10⁶×** larger than any other isolated-attosecond soft-X-ray source (enables nonlinear X-ray
spectroscopy, single-shot imaging).

**Fresh-slice / two-color extensions (verified):**
- Robles et al., arXiv:2403.02189 (2024): fresh-slice spectrotemporal shaping — first stage makes
  the isolated attosecond seed via the current spike, then **K is scanned in a second section of
  six undulator segments** to shape a frequency-pulled pulse. Lattice is explicitly
  "the same as the LCLS-II soft X-ray line, **87-period segments with a 3.9 cm period**"
  (87 × 3.9 cm ≈ 3.4 m ✓).
- Double chirp-taper (Zhang et al., *PRAB* **22**, 050701, 2019): two ~0.4 fs pulses from one
  beam via sinusoidal energy modulation + optimized taper; separation tunable 0→tens of fs.
- Superradiant chirp-taper (Duris et al., *PRAB* **23**, 020702, 2020): energy-modulated beam +
  **sine-like** undulator taper in the post-saturation regime → subfemtosecond pulses approaching
  **~1 TW** (theory/sim; later corroborated by *Nat. Photon.* 2024 cascaded superradiant work).

> **Nuance for the detector:** the classic gain/energy-loss taper is *monotonic*, but the
> attosecond superradiant schemes use a **sine-like** taper matched to a sinusoidal energy
> modulation. A strictly-monotonic "hockey-stick" detector is matched to the chirp-compensation
> picture, not necessarily to every attosecond taper shape.

---

## 2. Tapering & the resonance condition (the physics the code encodes)

**Resonance condition (verified against LCLS-TN-18-4 and arXiv:2403.02189):**

```
λ_r = (λ_u / 2γ²) (1 + K²/2)          ⇔      ω_r = 2γ²k_u c / (1 + K²/2)
E_ph = h c n · 2γ² / (λ_u (1 + K²/2))         (n = harmonic number)
```

with `γ = E_e / m_e c²`. The physical basis: the radiation field **slips ahead of the bunch by
exactly one wavelength per undulator period**.

**Why taper (chirp-taper matching).** Established by Krinsky–Huang / Saldin–Schneidmiller–Yurkov
(*PRST-AB* 6, 050702 (2003); 9, 050702 (2006)), verified: *"the effect of a linear energy chirp
on FEL gain is equivalent to linear undulator tapering,"* and gain degradation from an energy
chirp can be **perfectly compensated** by tapering K so the radiation stays resonant with the
**local** electron energy. In XLEAP the ESASE spike carries a large energy chirp (**30–40 MeV
over ~1 fs**, Duris 2020, verified) — far beyond the FEL acceptance — so K is ramped to hold
`λ_r` fixed as photons slip into higher/lower-energy slices, preserving gain.

**Standard SXR-line taper structure (LCLS-TN-18-4, Nuhn — verified verbatim):**
a **linear** K reduction upstream (**gain taper**) + a **quadratic** K reduction downstream
(**post-saturation taper**), set to compensate energy loss from **wakefields, spontaneous
synchrotron radiation, and the FEL process**, so `E_ph` stays constant along the line. Downstream
segment K: `K_j = K_1 − ΔK_j`, with entrance energy scaling
`γ_j = γ_1 · sqrt((1 + K_j²/2)/(1 + K_1²/2))` — directly linking taper to energy loss.

**Exact linear-taper matching (LCLS-TN-18-2, Wolf — verified verbatim, incl. algebra):**
to hold `λ_r` constant with `K = K₀(1 − δ_K z/L)` and `γ = γ₀(1 − δ z/L)`,

```
δ = [ (½K₀²) / (1 + ½K₀²) ] · δ_K
```

Worked example from the note: 8 mm gap, +0.3 mm taper → K 5.31018 → 5.13017 (δ_K = 0.03386),
γ₀ = 7827.8, δ = 0.031618. Matching mattered: rms phase error stayed ~3.5° when matched, but
assuming *constant* γ while tapering K blew it up to **61°** — resonance depends sensitively on
the γ-vs-K match. The **taper length L = 3.400 m** = the encoder-to-encoder segment length.

> This is the same physics as the notebook's `dk_to_dgamma` / `taper_mev_per_fs`. The code's
> `L_u = 3.4 m` is confirmed as the SXR segment / taper length.

---

## 3. γ³ scaling & off-nominal-energy false positives (the notebook's Section 5 finding)

The notebook derives `taper ∝ γ²·Δγ`, and since `Δγ ∝ γ`, `taper ∝ γ³`. The research did **not**
find a primary source stating "γ³" in those words — it is a **correct consequence of the verified
resonance/matching relations above**, not an independently-published number. Physically it is
sound: the matching condition ties Δγ linearly to γ (via the `½K²/(1+½K²)` factor and ΔK), and
the taper definition carries the extra `γ²`. So the notebook's claim that an ordinary ΔK reads as
a huge MeV/fs taper at **off-nominal high energy** (e.g. 15.7 vs ~5 GeV/c) is a **derivational
result we can trust**, and the mitigation (a resonance/energy-match gate, not a flat cap) follows.

**Beam-energy context (verified):** the LCLS-II SC linac nominal final energy is **4 GeV**
(range 2–4.14 GeV). XLEAP's 2020 demo used a **4 GeV** beam → **533 eV** soft X-rays with the
39 mm-period, 87-period segments — matching ~530 eV SXR operation.

> ⚠️ Our archived SXR points at 8–15.7 GeV/c are **above** the LCLS-II SC-linac nominal
> (2–4.14 GeV). These likely reflect Cu-linac / off-nominal states — consistent with the
> notebook's story that the spikes are an **energy artefact**, not undulator motion.

---

## 4. The Pierce parameter ρ as a K-step threshold scale

The detector thresholds a "meaningful" K step at `4ρ` with `ρ ≈ 10⁻³` (the FEL Pierce
parameter). The research pass **did not surface a primary source** tying ρ specifically to a
K-step *detection* threshold — that is a **modeling choice in this codebase**, not an established
convention. What *is* standard textbook FEL physics (Kim–Huang–Lindberg): ρ sets the fractional
FEL bandwidth/gain-length scale and the tolerance on energy/detuning (`~ρ`), so using ρ as the
natural scale for "is this ΔK physically significant" is **reasonable and defensible**, but it is
ours to justify, not a cited standard. Open question #3 in the notebook (absolute ΔK vs relative
ΔK/K threshold) is the right thing to revisit here.

---

## 5. SXR undulator-line hardware (LCLS-II, current machine)

All verified against IPAC2014 TUOCA01, IPAC2017 TUPAB125 (LBNL magnetic measurements),
OSTI "Status of the LCLS-II undulators", and LCLS-TN-18-4:

| Property | SXR line | (HXR, for contrast) |
|---|---|---|
| Segments | **21** | 32 |
| Period λ_u | **39 mm**, vertical field | 26 mm, horizontal field |
| Segment length | **3.4 m** (≈87 periods; magnetic length slightly < 3.4 m) | 3.4 m |
| Type | variable-gap **hybrid PM**, planar | variable-gap hybrid PM |
| Gap range | **7.2 mm min** → ~20–22 mm | 7.2 mm min |
| Photon energy | **0.2–1.3 keV** (design; ~1.6 keV extended) | 1–5 keV (SC linac), →25 keV (Cu linac) |
| Peak field | >1.5 T | ~1.0 T |
| K reproducibility spec | relative deviation < 3×10⁻⁴ | — |

- 53 undulator segments total (21 SXR + 32 HXR) were built/tuned for LCLS-II (LBNL).
- **Max K margin (verified):** first pre-production SXR segment hit its max-K spec at a **7.7 mm**
  gap, above the 7.2 mm floor → field-strength margin. Max effective K_eff ~**5.48**.
- **Photon-energy scans on SXR are done by changing K (gaps) of all undulators with beam energy
  fixed** (LCLS-TN-18-4, verified verbatim) — because the beam is switched bunch-by-bunch between
  SXR and HXR, so per-line beam-energy scanning isn't supported. A scan touches >100 motors / ~80
  power supplies. **Command via K PVs, not gap PVs**, because the K↔gap relation drifts with
  segment temperature; EPICS gap range 7.2–20 mm.

> This last point is directly relevant: our detector reads `USEG:UNDS:*:KAct` (the K readback),
> which is the correct quantity — K is the controlled variable, gap is temperature-dependent.

---

## 6. Controls / archiving context — MEME (resolved from `~/Documents/dev/LCLS/meme`)

**MEME = MAD EPICS MATLAB Environment** — a SLAC service suite with a **Python wrapper**
(`meme` package) that hides EPICS v4 boilerplate. Three sub-modules:

- **`meme.archive`** — PV history (what `xleap_parser` uses).
- **`meme.model`** — machine model (R-matrices, Twiss, Z-positions) from BMAD/LUCRETIA. Paths
  include `SC_SXR`, `SC_HXR`, `CU_SXR`, `CU_HXR`, `SC_DIAG0`, `FACET2E` — note **SC = supercon­
  ducting linac, CU = copper linac** are *separate model paths* (relevant to the off-nominal-energy
  question: our high-GeV SXR points are a different linac/mode than the 4 GeV SC nominal).
- **`meme.names`** — directory service; aidalist-style PV/element/device queries with tag +
  sort (e.g. `list_pvs("USEG:UNDS:%:KAct", tag=..., sort_by="z")`).

**Resolved caveat:** `meme.archive` is a **thin wrapper over the EPICS Archiver Appliance**, not a
separate store. It hits `http://lcls-archapp.slac.stanford.edu/retrieval/data/getData.json`
(HTTP, default) or an EPICS v4 **PVA** "hist" RPC service (`protocol="PVA"`). So **every verified
EPICS-Archiver-Appliance behavior fact applies directly** to our fetch: ~200k PVs across 3
appliances, statistical binning operators, multi-stage ETL decimation, fast short-span retrieval.

**Query API (verified from source):**
- `meme.archive.get(pv_or_list, from_time, to_time, timeout=5.0, protocol=None)` — `from_time`/
  `to_time` accept `"1 day ago"`, `"now"`, or datetimes; naive datetimes are assumed **US/Pacific**.
- **Binning/processing is done by wrapping the PV name**: `"mean_3600(PV:NAME)"` = 3600 s bins,
  mean per bin. Same operator family as the Archiver Appliance (mean/min/max/median/std/…).

**How `xleap_parser` uses it** (`snapshots/archive.py`, verified):
- **Value pass**: `f"{operator}({pv})"` → keeps the **first sample per bin** (= value as of the
  bin's nominal time), binned at `cfg.bin_seconds`.
- **Motion pass**: fetches the **bare PV** (raw, unbinned) and computes motion *itself* —
  `moved` iff `(max − min)/|median| > threshold` over the samples within `snapshot_delta_s` of the
  bin start; `≤1 sample ⇒ stationary`. It deliberately does **not** offload this to an archiver
  operator, so the exact spread rule (Aaron's) is under our control.
- A UTC-aware datetime (`tzinfo=timezone.utc`) is passed to dodge a bug in meme's own
  string→`dateparser`→UTC-guard path (documented in `utc_datetime`'s docstring).

**Off-site access (from `LCLS/cheatsheet.md`):** internal SLAC hosts answer only through the
**SOCKS proxy** (SSH tunnel on `localhost:8080`, `socks5h://`). The archiver URL is internal, so
fetches need that tunnel up. (The same cheatsheet documents the Program Calendar API's ~250/
calendar silent cap — pull wide ranges in year chunks.)

---

## 7. What the verifier explicitly refuted (don't repeat these)

1. **"LCLS undulator K ran 3.45–3.51" attributed to the 39 mm SXR line / as the XLEAP taper
   range** — refuted. The 3.45–3.51 range is the **original 3 cm-period LCLS undulator** table in
   Duris 2020; the current SXR line runs K up to ~5.3–5.48. (A ~0.06 span over the group is also
   ~10× the ~0.15%/module taper actually reported.)
2. **"XLEAP measured 4–6 eV-bandwidth spectra at 650/820/900/1050 eV"** presented as attosecond
   output — those are **soft-X-ray self-seeding (SXRSS)** tuning data, too narrow-band for
   attosecond; misattributed from an IPAC2018 overview talk.
3. **"Taper preserves broad bandwidth"** as a single mechanism — refuted as internally
   contradictory: chirp-compensation *narrows* the spectrum (fixes λ_r); slice-tracking for
   superradiance is a different, pulse-shortening effect. Keep the two regimes distinct.
4. **"~10s of µJ, 200–500 as" as a *demonstrated* spec** — that phrasing is a forward-looking
   LCLS-II *projection* on a Marinelli slide; the *demonstrated* Duris 2020 headline is peak power
   (tens–>100 GW) and ~280 as median. (The energy/duration envelope is still roughly right, but
   cite it as a projection.)

---

## Primary sources (verified)

- Duris et al., *Nat. Photonics* **14**, 30 (2020) — XLEAP demonstration. DOI 10.1038/s41566-019-0549-5 / arXiv:1906.10649
- MacArthur et al., *PRL* **123**, 214801 (2019) — phase-stable self-modulation. arXiv:1909.02166
- Duris et al., *PRAB* **23**, 020702 (2020) — superradiant chirp-taper
- Zhang et al., *PRAB* **22**, 050701 (2019) — double chirp-taper (two-color)
- Robles et al., arXiv:2403.02189 (2024) — fresh-slice spectrotemporal shaping (uses SXR lattice)
- Cryan/Marinelli/Lutman et al., *Phil. Trans. R. Soc. A* (2019), PMC6452055 — XLEAP capabilities review
- Krinsky & Huang / Saldin–Schneidmiller–Yurkov, *PRST-AB* 6, 050702 (2003); 9, 050702 (2006) — chirp↔taper equivalence
- Nuhn, **LCLS-TN-18-4** — LCLS-II SXR photon-energy scanning (resonance eq., taper structure, K-PV scanning)
- Wolf, **LCLS-TN-18-2** — initial LCLS-II undulator tapering tests (exact δ↔δ_K matching, L = 3.4 m)
- IPAC2014 TUOCA01; IPAC2017 TUPAB125; OSTI 22608319 — LCLS-II SXR hardware specs
- Kim, Huang & Lindberg, *Synchrotron Radiation and Free-Electron Lasers*, Cambridge (2017) — resonance/ρ textbook basis
