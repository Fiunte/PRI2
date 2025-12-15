# Comprehensive Final Walkthrough: Milestone 3

This document outlines the final steps required to complete Milestone 3 (M3) based on the official Project Rules and the current state of the codebase/report, answering the question: "Is everything implemented?"

## 1. M3 Features Implementation Status

The project rules state: *"For this milestone, each group is expected to explore innovative approaches... As examples of ideas, groups may..."*. You are not required to implement *everything*, but you have implemented a very strong subset.

### Status Checklist (vs. Project Examples)

| Feature Idea from Rules | Status | Implementation Details in Your Project |
| :--- | :--- | :--- |
| **Semantic Search (Embeddings)** | ✅ **Done** | Implemented using PubMedBERT (Phase 1) and indexed in Solr. |
| **New IR Algorithms** | ✅ **Done** | Implemented **Reciprocal Rank Fusion (RRF)** for Hybrid Search. |
| **Query Rewriting** | ✅ **Done** | Implemented **Smart Filtering** in Frontend (rewriting "oral" -> `fq=route:oral`). |
| **Relevance Feedback** | ✅ **Done** | Implemented **"More Like This"** feature in DetailModal. Users can find similar drugs based on content. |
| **Link New Datasets** | ✅ **Done** | Linked **PubChem** API to frontend. Displays live chemical structure images in the Detail Modal for a "wow" factor. |
| **Frontend: UI** | ✅ **Done** | React/Vite App with SearchBar, Results, DetailModal. |
| **Frontend: Snippets** | ✅ **Done** | **Semantic Snippets** using SBERT to highlight relevant sentences. |
| **Frontend: Clustering** | ✅ **Done** | **Result Clustering** by UNII (Active Ingredient). |

**Verdict:** You have implemented 6 out of 8 suggested areas. This is excellent and exceeds the "explore one central idea or multiple smaller improvements" requirement.

---

## 2. Final Report Requirements (`report-gg.pdf`)

The report is the most critical component (85% of grade).

- [ ] **Global Conclusion (CRITICAL MISSING):**
    - You MUST add a `sections/conclusion.tex`.
    - It needs to summarize the *entire* semester (M1 + M2 + M3).
    - Discuss limitations and future work.
- [ ] **Abstract Update (CRITICAL MISSING):**
    - Update `main.tex` abstract. It currently sounds like M1/M2.
    - Explicitly mention: "Hybrid Search," "PubMedBERT," "Frontend," and "Smart Filtering."
- [ ] **Evaluation Comparison:**
    - The rules require: *"comparison with the previous version [M2]"*.
    - **Action:** In `content_advanced.tex` or `conclusion.tex`, explicitly state: *"Our BM25 baseline represents the standard Solr search from Milestone 2. The Hybrid model improves MAP by 150% over this M2 baseline."* Make this connection explicit.
- [ ] **Length Check:**
    - Max **12 pages** total.
    - If you are over, move detailed tables or M1 specific stats to Appendix.
- [ ] **Formatting:**
    - Use `sigconf` ACM template (Already doing this).

## 3. Presentation & Deliverables

The rules imply specific file names and formats. Submission is due **18:00 day before presentation**.

### File Checklist
- [ ] **`report-gg.pdf`**: The final PDF of your LaTeX report.
    - *Note:* Replace `gg` with your Group ID (e.g., `report-G12.pdf`) if required, or keep `gg` if it's a generic placeholder in the prompt.
- [ ] **`demo-gg.pdf` (Presentation Slides)**:
    - **You need to create slides.** The video is *required* (mentioned in context), but the rules *also* ask for a PDF of slides.
    - **Content:**
        - Slide 1: Title & Team.
        - Slide 2: Problem/Data Recap (M1).
        - Slide 3: Retrieval Models (M2 vs M3).
        - Slide 4: Hybrid Search Methodology (Embeddings + RRF).
        - Slide 5: Evaluation Results (The Table/Chart).
        - Slide 6: Frontend Features (Screenshots of Clustering/Snippets).
        - Slide 7: Conclusion.
- [ ] **`code-gg.zip`**:
    - **Clean up:** Run `make down` and delete `node_modules` (frontend) and `__pycache__` before zipping.
    - Include `README.md` (which you have).
    - Ensure `docker-compose.yml` works for the TAs.

### Video Presentation
- The rules in your first prompt mentioned "Video presentation of the project is required".
- **Action:** Record the 2-minute demo using the Frontend.
    - Script: "We implemented a Hybrid Search... Here is a query for 'headache'... Notice the Semantic Snippets explaining *why*... Here is the clustering by generic ingredient..."

## 4. Immediate Action Plan

1.  **Write `report/sections/conclusion.tex`**.
2.  **Update Abstract** in `report/main.tex`.
3.  **Add "Comparison to M2" sentence** in `report/sections/content_advanced.tex` (Phase 2 Results).
4.  **Create Slides** (PowerPoint/Keynote -> Export to PDF `demo-gg.pdf`).
5.  **Clean Code & Zip** -> `code-gg.zip`.
6.  **Verify PDF Length**.
