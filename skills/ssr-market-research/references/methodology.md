# SSR methodology (deep reference)

Source: Maier, Aslak, Fiaschi, Rismal, Fletcher, Luhmann, Dow, Pappas, Wiecki (2025),
*"LLMs Reproduce Human Purchase Intent via Semantic Similarity Elicitation of Likert
Ratings"*, arXiv:2510.08338.

## The problem
Synthetic respondents are attractive (surveys are slow, expensive, sampling-biased), but
LLMs asked for a **numeric** Likert rating collapse to the center of the scale — they output
mostly "3", with unrealistically low variance and weak correlation to humans (~50% of the
human reliability ceiling). The information is in the model; the numeric channel destroys it.

## The SSR fix, step by step

### 1. Persona conditioning
Each synthetic respondent gets a system prompt impersonating a real consumer with demographic
attributes (age, gender, income, location, ethnicity) matched to the real survey panel, then
sees the product concept. **Ablation:** removing persona detail dropped correlation attainment
92% → 50%. Detailed framing is what forces the model to actually use the concept's information.
Age and income tracked human patterns well; gender and region less so.

### 2. Free-text elicitation
Ask an open question ("How likely are you to purchase the product?") and capture a
natural-language answer. The variance lives in the language, not in a forced number.

### 3. Reference (anchor) statements
- **6 sets × 5 statements** = one statement anchoring each Likert point, in 6 stylistic
  variants. Statements are "short, generic, and domain-independent ... such that they could
  plausibly apply to any consumer product concept." Multiple sets capture how differently
  people phrase the same intent.

### 4. Embedding → distribution
- Embed the response `t` and each reference `sigma_r` with `text-embedding-3-small`
  (text-embedding-3-large gave virtually identical results — embedding choice wasn't critical).
- Cosine similarity: `gamma(sigma_r, t) = (v_sigma_r . v_t) / (|v_sigma_r| |v_t|)`.
- Map to a PMF over points by subtracting the minimum-similarity reference, then normalizing:
  `p'(r) ∝ gamma(sigma_r, t) - gamma(sigma_l, t) + eps*delta_{l,r}`, with `l = argmin`,
  `eps = 0` in their implementation. The subtraction prevents the near-flat distributions you
  get from raw cosine similarities (which sit in a narrow high band).
- Optional temperature smoothing: `p'(r, T) ∝ p'(r)^(1/T)`, default `T = 1`. Higher T smears
  the distribution; they note tuning potential but didn't rely on it.

### 5. Aggregation
- Average the PMF across the 6 anchor sets → one PMF per respondent.
- Generate one response per real participant (match the panel size), then average individual
  PMFs into a survey-level distribution: `p_s(i) = (1/N_s) * sum_c p'_c(i)`.

## Results / validation
- Benchmark: 9,300 human responses across 57 personal-care product surveys.
- SSR reached ~**90%** of the human **test–retest reliability** ceiling (estimated via 2,000
  Monte-Carlo split-half correlations), with realistic distributions (KS similarity > 0.85).
- Beat a supervised LightGBM baseline (88% vs 65% correlation attainment) with **zero
  fine-tuning**. Also yields qualitative explanations alongside each rating.

## Metric they report
"Correlation attainment" `rho = E[R^xy] / E[R^xx]` — model-vs-human correlation normalized by
the human self-correlation ceiling. 100% would mean indistinguishable from a re-run of the
human survey.

## Fidelity caveats when reusing this
- Validated at the **aggregate** level on consumer-goods purchase intent. Individual Likerts
  are noisy; trust distributions, not single respondents.
- Out-of-domain (B2B software adoption, WTP for a SaaS feature, etc.) is **not** validated by
  the paper — treat outputs as a structured prior / hypothesis generator, not measurement.
- Respondent **independence** matters: generate each persona's reaction in its own context
  (separate agent) rather than many in one chat, which homogenizes answers and shrinks variance.
- The impersonating model's biases ride along. Use SSR to rank, contrast segments, and falsify
  hypotheses cheaply; validate the winners with real users before betting on absolute numbers.
