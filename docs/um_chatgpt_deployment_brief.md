# UM ChatGPT Deployment Brief: Commercialization Advisor v2

## Purpose and Scope

This one-page brief specifies how to package and govern Commercialization Advisor v2 inside a University of Missouri (UM / UMKC) ChatGPT Workspace or Enterprise environment. The deployment keeps the core v2 architecture intact. Quoted policy passages and reviewed glossary explainers answer questions, deterministic code enforces the scope boundary, and judgment calls go to campus experts.

## 1. System Instructions and Boundary Rules

The custom GPT or workspace assistant must run with deterministic instructions that enforce four rules on every turn:

1. **Quote-first policy answers.** When answering UM or UMKC policy questions, quote the retrieved passage verbatim from the approved corpus and display its `source_title`, `version`, `locator`, and `applies_to` fields. Do not paraphrase policy rules.
2. **Mandatory `source_label` badge on every block.** Every response block must carry one of four explicit provenance labels:
   - `"Quoted policy (title, version)"` for verbatim passages from `corpus.json`.
   - `"General explainer, draft, not yet reviewed by the technology office"` for plain-language concept blocks from `glossary.json` (until `reviewed_by` and `reviewed_on` are populated).
   - `"From your draft"` for readiness coaching observations extracted from the researcher's text.
   - `"Referral: needs the technology office or the conflict of interest office"` for legal, patentability, inventorship, or timeline judgment calls.
3. **No verdicts or composite scores.** Never claim that an invention `"is patentable"`, `"is novel"`, `"you should file"`, or `"you are an inventor"`. Never compute a numeric readiness score.
4. **Explicit campus referral list.** Route conflict-of-interest, outside consulting, and equity questions to the **UMKC Conflict of Interest Office** (`umkccoi@umkc.edu`). Route invention disclosures, prior-art comparisons, filing timelines, and licensing questions to the **UM Office of Technology Commercialization** (OTC) and UMKC Office of Research and Innovation (`https://ori.umkc.edu`).

## 2. Approved Knowledge Files and Versions

Load only version-stamped JSON files built through `backend/data/scripts/build_policy_corpus.py`:

| File | Contents | Version / Retrieval Stamp |
|---|---|---|
| `backend/data/policies/corpus.json` (425 passages) | 1. UM CRR `100.020` Invention and Patent Regulations (`Amended 6-24-21`, 171 passages)<br>2. UM CRR `100.030` Copyright Regulations (`Amended 6-24-21`, 43 passages)<br>3. UM CRR `330.015` Policy on Conflict of Interest (`Amended 9-12-24`, 59 passages)<br>4. UM CRR `420.030` Conflict with the Interests of Federal Grant Agencies (`Amended 8-24-12`, 34 passages)<br>5. UMKC Financial Conflict of Interest (FCOI) Policy (`Version June 2026`, 97 passages)<br>6. UMKC ORI Ownership page (`Retrieved 2026-11-01`, 4 passages)<br>7. UMKC ORI Intellectual Property page (`Retrieved 2026-11-01`, 17 passages) | Retrieved `2026-11-01` |
| `backend/data/commercialization/glossary.json` (12 terms) | Plain-language explainers for `novelty`, `prior art`, `inventorship`, `public disclosure`, `development stage`, `translational readiness`, `potential application`, `differentiation`, `conflict of interest`, `invention disclosure`, `licence`, and `equity`. Includes `reviewed_by` and `reviewed_on` metadata fields. | Draft (`reviewed_by: null`, `reviewed_on: null`) |

## 3. Action / Tool Schema and Disabled Features

Instead of letting the language model retrieve or improvise policy answers from raw PDFs, configure the assistant to call the FastAPI backend via OpenAPI Actions:

- `POST /api/v1/commercialization/advisor/ask` (`askAdvisor`): accepts `{ "question": string, "draft": DraftResult | null }` and runs `scope_service.classify_intent()`, `glossary_service.lookup()`, `policy_service.answer_question()` with topic boost, and `verifier.verify()`. Returns `AdvisorResponse` (`intent` and `blocks[]`).
- `POST /api/v1/commercialization/readiness` (`getReadiness`): accepts `{ "draft": DraftResult, "extra_text": string }` and returns `ReadinessResult` across the six dimensions (`problem`, `application`, `difference`, `evidence`, `related_work`, `timing`).
- `GET /api/v1/commercialization/glossary` (`getGlossary`): returns `GlossaryResult` (`entries[]` and `source_label`).

**Disabled features in UM ChatGPT:** Disable open web browsing, third-party plugins, and unverified free-text policy summarization so that answers remain strictly bounded by `verifier.verify()` and `claims_filter()`.

## 4. Privacy and Unpublished-Invention Gate

- **Unpublished manuscript warning.** Pasting an unpublished manuscript or experimental dataset into an external cloud model can create confidentiality or public-disclosure risks if the tenant logs prompts or trains on user inputs.
- **Offline rules extractor default.** The application defaults to the local deterministic rules extractor (`extractor: "rules"`) and processes uploaded PDFs and free-text readiness inputs in memory without database persistence.
- **Hosted ChatGPT gate (Assumption).** *Assumption:* Deploying document-level coaching inside UM's hosted ChatGPT environment requires written confirmation from UM IT and OTC that the workspace operates under zero-data-retention and zero-training enterprise terms. Until confirmed, faculty must see a pre-submission gate warning them not to paste unpublished chemical structures, sequence data, or enabling experimental details into hosted ChatGPT.

## 5. Maintenance, OTC Sign-Off, and Evaluation Loop

- **Owner and cadence (Assumption).** *Assumption:* A designated maintainer in the UMKC Office of Research and Innovation / OTC reviews policy sources at the start of each fall and spring semester and whenever the UM Board of Curators amends CRR Chapters 100, 330, or 420.
- **OTC glossary sign-off.** When OTC staff review a glossary definition in `glossary.json`, they populate `reviewed_by` (staff name/role) and `reviewed_on` (`YYYY-MM-DD`). Once populated, the UI badge updates from draft status to reviewed status.
- **Automated regression gate on every update.** After re-running `build_policy_corpus.py` or editing `glossary.json`, the maintainer runs the frozen 25-question benchmark (`backend/eval/gold_retrieval.json`) and 5 synthetic faculty scenarios (`backend/eval/scenarios.json`) to verify that top-5 policy retrieval, definitional routing, and zero boundary violations hold before publishing.
