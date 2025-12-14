import sys
import matplotlib.pyplot as plt

# --- Data Loading Functions ---

def load_qrels(filename="qrels.txt"):
    """
    Loads a qrels file (TREC format) into a nested dictionary.
    Format: {q_id: {doc_id: relevance, ...}, ...}
    """
    qrels_data = {}
    try:
        with open(filename, 'r') as f:
            for line in f:
                if line.startswith('#') or not line.strip():
                    continue
                parts = line.strip().split()
                if len(parts) != 4:
                    continue
                q_id, _, doc_id, relevance = parts
                if q_id not in qrels_data:
                    qrels_data[q_id] = {}
                try:
                    qrels_data[q_id][doc_id] = int(relevance)
                except ValueError:
                    qrels_data[q_id][doc_id] = 0
    except FileNotFoundError:
        print(f"Error: Qrels file not found at {filename}.", file=sys.stderr)
        return None
    return qrels_data

def load_run(filename):
    """
    Loads a run file (TREC format) into a nested dictionary.
    Format: {q_id: [doc_id_rank_1, doc_id_rank_2, ...], ...}
    """
    run_data_sorted = {}
    run_data_with_ranks = {}
    try:
        with open(filename, 'r') as f:
            for line in f:
                if line.startswith('#') or not line.strip():
                    continue
                parts = line.strip().split()
                if len(parts) != 6:
                    continue
                q_id, _, doc_id, rank, _, _ = parts

                if q_id not in run_data_with_ranks:
                    run_data_with_ranks[q_id] = []
                try:
                    run_data_with_ranks[q_id].append((int(rank), doc_id))
                except ValueError:
                     pass

        # Sort by rank
        for q_id, doc_list in run_data_with_ranks.items():
            doc_list.sort(key=lambda x: x[0])
            run_data_sorted[q_id] = [doc_id for rank, doc_id in doc_list]

    except FileNotFoundError:
        print(f"Warning: Run file not found at {filename}.", file=sys.stderr)
        return None
    return run_data_sorted

# --- Metric Calculation Functions ---

def calculate_precision_at_k(qrels_for_query, run_for_query, k):
    """Calculates Precision@k."""
    if not run_for_query: return 0.0
    top_k_docs = run_for_query[:k]
    relevant_found = sum(1 for doc_id in top_k_docs if qrels_for_query.get(doc_id, 0) > 0)
    return relevant_found / k if k > 0 else 0.0

def calculate_average_precision(qrels_for_query, run_for_query):
    """Calculates Average Precision (AP)."""
    total_relevant_docs = sum(1 for rel in qrels_for_query.values() if rel > 0)
    if total_relevant_docs == 0 or not run_for_query:
        return 0.0

    sum_of_precisions = 0.0
    relevant_found_so_far = 0

    for rank, doc_id in enumerate(run_for_query, start=1):
        if qrels_for_query.get(doc_id, 0) > 0:
            relevant_found_so_far += 1
            sum_of_precisions += (relevant_found_so_far / rank)

    return sum_of_precisions / total_relevant_docs

def calculate_interpolated_pr(qrels_for_query, run_for_query):
    """
    Calculates interpolated Precision-Recall data points for plotting.
    Returns: (recalls_list, precisions_list)
    """
    total_relevant = sum(1 for rel in qrels_for_query.values() if rel > 0)
    if total_relevant == 0:
        return [0, 1], [0, 0]

    # 1. Calculate raw (Recall, Precision) points
    raw_points = []
    relevant_found = 0

    for rank, doc_id in enumerate(run_for_query, start=1):
        if qrels_for_query.get(doc_id, 0) > 0:
            relevant_found += 1
            precision = relevant_found / rank
            recall = relevant_found / total_relevant
            raw_points.append((recall, precision))

    if not raw_points:
        return [0, 1], [0, 0]

    # 2. Add start point (Recall=0) and sort
    raw_points.append((0, raw_points[0][1]))
    raw_points.sort(key=lambda x: x[0])

    recalls = [p[0] for p in raw_points]
    precisions = [p[1] for p in raw_points]

    # 3. Interpolation: P(r) = max(P(r')) for all r' >= r
    running_max = 0
    for i in range(len(precisions) - 1, -1, -1):
        if precisions[i] > running_max:
            running_max = precisions[i]
        else:
            precisions[i] = running_max

    return recalls, precisions

# --- Main Execution ---

def main():
    # Configuration
    QRELS_FILE = "qrels.txt"
    RUN_FILES = {
        "Setup 1 (Baseline)": "setup1_run.txt",
        "Setup 2 (Advanced)": "setup2_run.txt"
    }

    # Load Qrels
    print(f"--- Loading Qrels: {QRELS_FILE} ---")
    all_qrels = load_qrels(QRELS_FILE)
    if not all_qrels: return

    # Load Runs
    all_runs = {}
    for sys_name, f_name in RUN_FILES.items():
        run_data = load_run(f_name)
        if run_data: all_runs[sys_name] = run_data

    if not all_runs:
        print("No valid run files found.")
        return

    # Initialize accumulators for MAP (Mean Average Precision)
    system_ap_accumulators = {sys_name: [] for sys_name in all_runs}

    # Identify all unique queries present in the runs
    all_queries = set()
    for r_data in all_runs.values():
        all_queries.update(r_data.keys())
    sorted_queries = sorted(list(all_queries))

    print("\n" + "="*60)
    print("--- Evaluation Results & Plots ---")
    print("="*60)

    # Iterate OVER QUERIES first (to compare systems side-by-side)
    for q_id in sorted_queries:
        if q_id not in all_qrels:
            print(f"\n[Skipping {q_id}]: No judgments in qrels file.")
            continue

        print(f"\nQuery: {q_id}")
        print("-" * 60)
        print(f"{'System':<25} | {'P@5':<8} | {'P@10':<8} | {'AP':<8}")
        print("-" * 60)

        # Prepare plot for this query
        plt.figure(figsize=(8, 6))

        qrels_q = all_qrels[q_id]

        # Iterate over systems for this specific query
        for sys_name, run_data in all_runs.items():
            run_q = run_data.get(q_id, [])

            # 1. Calculate Metrics
            p5 = calculate_precision_at_k(qrels_q, run_q, 5)
            p10 = calculate_precision_at_k(qrels_q, run_q, 10)
            ap = calculate_average_precision(qrels_q, run_q)

            # Print Metrics Table Row
            print(f"{sys_name:<25} | {p5:.4f}   | {p10:.4f}   | {ap:.4f}")

            # Store AP for MAP calculation later
            system_ap_accumulators[sys_name].append(ap)

            # 2. Calculate and Plot PR Curve
            recalls, precisions = calculate_interpolated_pr(qrels_q, run_q)
            plt.plot(recalls, precisions, label=f"{sys_name} (AP={ap:.2f})", linewidth=2)

        # Finalize and Save Plot
        plt.xlabel('Recall')
        plt.ylabel('Precision')
        plt.title(f'Interpolated Precision-Recall Curve - {q_id}')
        plt.legend(loc='best')
        plt.grid(True, linestyle='--', alpha=0.6)
        plt.xlim([0.0, 1.0])
        plt.ylim([0.0, 1.05])

        plot_filename = f"pr_curve_{q_id}.png"
        plt.savefig(plot_filename)
        plt.close()
        print(f"\n✅ Comparison plot saved to: {plot_filename}")

if __name__ == "__main__":
    main()
