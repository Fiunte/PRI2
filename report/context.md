# Project Context: Information Processing and Retrieval (PRI) M.EIC 2025/26

## 1. Project Overview
[cite_start]**Course:** Information Processing and Retrieval (PRI) - Master in Informatics Engineering and Computation (M.EIC), FEUP, U.Porto[cite: 16, 17].
[cite_start]**Goal:** Develop a complete information search system, including data collection/preparation, querying/retrieval, and retrieval evaluation[cite: 20].
[cite_start]**Team Structure:** Groups of 4 students[cite: 21].
[cite_start]**Topic Selection:** * Topics are free but must be unique within the class[cite: 23].
* [cite_start]Data must be mostly unstructured and rich in text (long text fields, not just labels)[cite: 24, 74].
* [cite_start]Must combine a minimum of two distinct datasets if using prepared sources[cite: 75].

## 2. General Deliverables & Policies
**Submission Pipeline:**
* [cite_start]**Format:** Reports must use the ACM `sigconf` two-column template (available on Overleaf)[cite: 48, 49].
* **Length:** Max 4 pages for M1/M2; [cite_start]Max 12 pages for the final M3 report[cite: 45].
* [cite_start]**Submission Time:** Up to 18:00 on the day *before* the presentation[cite: 51].
* [cite_start]**Files:** PDF Slides (`demo-gg.pdf`), PDF Report (`report-gg.pdf`), Code (`code-gg.zip`) submitted via Moodle [cite: 51-54].
* [cite_start]**Penalty:** Delayed submission incurs a -10% penalty[cite: 3].

**Grading Scheme:**
* [cite_start]**Presentation:** 15% of the grade for each milestone[cite: 28, 3].
* [cite_start]**Report & Work Developed:** 85% of the grade for each milestone[cite: 3].
* [cite_start]**Individual Component:** Grades can vary by ±3 points within a group based on contribution and peer/teacher assessment[cite: 41].

---

## 3. Milestone 1: Data Preparation (M1)
[cite_start]**Objective:** Prepare and characterize datasets to serve as the foundation for the project[cite: 68, 72].

### Requirements
* [cite_start]Search and select convenient data subsets[cite: 77, 78].
* [cite_start]Assess data authority and quality[cite: 79].
* [cite_start]Perform exploratory data analysis (EDA)[cite: 80].
* [cite_start]Create a reproducible data processing pipeline[cite: 72, 81].
* [cite_start]Define the conceptual data model[cite: 83].
* [cite_start]Define prospective search tasks/information needs[cite: 140].

### Evaluation Criteria (Report/Work Component)
* **1. [cite_start]Document Summary (10%):** Front matter, abstract, format, structure, writing, references[cite: 140].
* **2. [cite_start]Topic (5%):** Context and presentation[cite: 140].
* **3. [cite_start]Data Sources (20%):** Identification, description, reference, formats, volume, license[cite: 140].
* **4. [cite_start]Collection & Preparation (30%):** Pipeline description/diagram, collection/processing operations, conceptual model, reproducibility[cite: 140].
* **5. [cite_start]Characterization (25%):** Collection stats, document presentation, descriptive/exploratory statistics (multivariate), text analysis (NER, keywords)[cite: 140].
* **6. [cite_start]Prospective Search Tasks (10%):** Description and defined information needs[cite: 140].

---

## 4. Milestone 2: Information Retrieval (M2)
[cite_start]**Objective:** Implement Solr indexing, configure free-text queries, and evaluate retrieval performance[cite: 95, 96].

### Requirements
* [cite_start]Use **Solr** as the retrieval platform[cite: 99].
* [cite_start]Identify indexable components and build indexes[cite: 100, 101].
* [cite_start]Explore retrieval ideas: Field boosts, term boosts, phrase matching (slop), wildcards/fuzziness, proximity searches[cite: 3].
* [cite_start]Implement and compare two distinct retrieval setups[cite: 104].
* [cite_start]Manually evaluate results and calculate precision metrics (P@, MAP, P-R Curve)[cite: 105, 3].

### Evaluation Criteria (Report/Work Component)
* **1. [cite_start]Manuscript (20%):** Abstract, format, structure, writing, references, improvements over M1[cite: 3].
* **2. [cite_start]Collection + Indexing (20%):** Document definition, indexing process, fields/processing, schema details[cite: 3].
* **3. [cite_start]Retrieval (30%):** Retrieval process, ideas explored (boosts, fuzziness, proximity), demo with defined info needs[cite: 3].
* **4. [cite_start]Evaluation (30%):** Review info needs, compare setups, manual evaluation process, Precision metrics (P@, MAP), P-R curve, discussion[cite: 3].

---

## 5. Milestone 3: Search System (M3)
[cite_start]**Objective:** Develop the final search system with major improvements (semantic search, UI, etc.) and extended evaluation[cite: 109, 121].

### Requirements
* [cite_start]**Improvements:** Explore one central idea in depth or multiple smaller improvements[cite: 133].
    * [cite_start]*Examples:* Semantic search (embeddings), Query rewriting/relevance feedback, Result clustering, Snippet generation, New data signals, UI development (if approved)[cite: 123, 126, 128, 133].
* [cite_start]**Evaluation:** Individual assessments, comparison of setups, P-R curves with multiple setups, extensive discussion[cite: 133].
* [cite_start]**Video:** A video presentation of the project is required[cite: 133].

### Evaluation Criteria (Report/Work Component)
* **1. [cite_start]Manuscript (20%):** Standard formatting/structure, plus improvements over M1/M2 text, and the video presentation[cite: 133].
* **2. Improvements (40%):** * Hypothesis/Idea definition.
    * [cite_start]Exploration of ideas (Semantic search, Additional sources, Query processing, Solr features like "More like this", GUI)[cite: 133].
* **3. Evaluation (40%):**
    * Individual assessments (RNRRR...).
    * Comparison of different setups.
    * Manual evaluation description.
    * Precision metrics (P@, MAP) and P-R curves.
    * [cite_start]Discussion of results[cite: 133].

---

## 6. Current Implementation Status (as of Dec 15)

### Completed / Implemented
#### Milestone 1 (Data Prep)
*   **Data Pipeline:** Complete pipeline for OpenFDA and DrugBank data.
*   **Report:** `sections/content_preparation.tex` covers Data Sources, Collection, Characterization.

#### Milestone 2 (Retrieval)
*   **Solr Indexing:** Standard fields indexed.
*   **Retrieval Setups:** Analyzed and implemented.
*   **Report:** `sections/content_retrieval.tex` covers Indexing and Basic Retrieval.

#### Milestone 3 (Advanced Search & UI)
*   **Evaluation Framework:** Automated evaluation using `DeepSeek-R1` (via Ollama) acting as a judge ("Generous Relevance").
*   **Embeddings & Hybrid Search:**
    *   **Phase 1:** Evaluated 6 dense models (SBERT, Bio_ClinicalBERT, PubMedBERT, etc.).
    *   **Selection:** PubMedBERT selected (Highest MAP).
    *   **Phase 2:** Hybrid Search (PubMedBERT + BM25) with Reciprocal Rank Fusion (RRF).
    *   **Tuning:** Alpha=0.5 selected as optimal.
*   **Frontend (UI):**
    *   **Stack:** React/Vite (likely, based on file structure).
    *   **Features:** SearchBar, SearchResults, DetailModal.
    *   **Smart Filtering:** Client-side query rewriting (Route, Therapeutic Class, Product Type) with alias handling.
    *   **Clustering:** Result clustering by UNII (Active Ingredient).
    *   **Semantic Snippets:** SBERT-based snippet generation for explanation.
*   **Report:** `sections/content_advanced.tex` details Hybrid Search, Methodology, and Frontend features.

### Missing / To Do
*   **Global Conclusion:** `main.tex` and included files lack a final Conclusion section summarizing the whole project.
*   **Abstract Update:** The abstract in `main.tex` currently focuses on M1/M2. Needs update to mention Hybrid Search and UI.
*   **Video Presentation:** "A video presentation of the project is required" (Not found in files).
*   **Submission Packaging:** Need to generate `demo-gg.pdf` (Slides?), `report-gg.pdf`, and `code-gg.zip`.
*   **Final Review:** Verification of page limits (Max 12 pages) and formatting.