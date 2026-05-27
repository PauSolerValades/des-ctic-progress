"""Quick analysis queries using DuckDB on the output Parquet files."""
import duckdb

for size in ["1M", "500K"]:
    c = f"output/{size}/out_cascades.parquet"
    p = f"output/{size}/out_posts.parquet"
    s = f"output/{size}/out_run_summary.parquet"

    print(f"{'='*60}")
    print(f"  {size}")
    print(f"{'='*60}")

    # --- Virality distribution ---
    print("\n--- struct_virality overall ---")
    duckdb.sql(f"""
        SELECT
            COUNT(*) as n,
            MIN(struct_virality) as min_v,
            AVG(struct_virality)::FLOAT as mean_v,
            MEDIAN(struct_virality) as med_v,
            MAX(struct_virality) as max_v,
            (SUM(CASE WHEN struct_virality <= 1.34 THEN 1 ELSE 0 END)::FLOAT / COUNT(*) * 100)::FLOAT as pct_minimal
        FROM '{c}'
    """).show()

    # --- Virality by cascade size bucket ---
    print("\n  Virality by cascade size bucket:")
    duckdb.sql(f"""
        SELECT
            CASE
                WHEN cascade_size < 5 THEN '3-4'
                WHEN cascade_size < 10 THEN '5-9'
                WHEN cascade_size < 20 THEN '10-19'
                WHEN cascade_size < 50 THEN '20-49'
                WHEN cascade_size < 100 THEN '50-99'
                ELSE '100+'
            END as size_bucket,
            COUNT(*) as n,
            AVG(struct_virality)::FLOAT as mean_virality,
            AVG(cascade_depth)::FLOAT as mean_depth,
            AVG(max_out_degree)::FLOAT as mean_max_out
        FROM '{c}'
        GROUP BY size_bucket
        ORDER BY MIN(cascade_size)
    """).show()

    # --- Virality by author degree ---
    print("\n  Virality by author degree bucket:")
    duckdb.sql(f"""
        SELECT
            CASE
                WHEN author_degree = 0 THEN 'zero'
                WHEN author_degree < 100 THEN '1-99'
                WHEN author_degree < 1000 THEN '100-999'
                WHEN author_degree < 10000 THEN '1K-10K'
                ELSE '10K+'
            END as degree_bucket,
            COUNT(*) as n,
            AVG(struct_virality)::FLOAT as mean_v,
            AVG(cascade_size)::FLOAT as mean_size,
            AVG(cascade_depth)::FLOAT as mean_depth
        FROM '{c}'
        GROUP BY degree_bucket
        ORDER BY MIN(author_degree)
    """).show()

    # --- Cascade size distribution (log buckets) ---
    print("\n  Cascade size distribution (log10 buckets):")
    duckdb.sql(f"""
        SELECT
            FLOOR(LOG10(cascade_size)) as log_size,
            COUNT(*) as n,
            AVG(struct_virality)::FLOAT as mean_v,
            AVG(cascade_depth)::FLOAT as mean_depth,
            MAX(cascade_size) as max_in_bucket
        FROM '{c}'
        GROUP BY log_size
        ORDER BY log_size
    """).show()

    # --- Content starvation: posts with reposts=0 vs posts with reposts>0 ---
    print("\n--- Content starvation indicators ---")
    duckdb.sql(f"""
        SELECT
            CASE WHEN total_reposts = 0 THEN 'zero_reposts' ELSE 'has_reposts' END as category,
            COUNT(*) as n,
            AVG(lifetime_raw)::FLOAT as mean_lifetime,
            AVG(time_to_peak_50)::FLOAT as mean_ttp50,
            AVG(burstiness_B)::FLOAT as mean_burstiness
        FROM '{p}'
        GROUP BY category
    """).show()

    # --- Posts that got likes but no reposts (engagement without virality) ---
    print("\n  Posts with likes but zero reposts vs lifetime:")
    duckdb.sql(f"""
        SELECT
            CASE
                WHEN lifetime_raw = 0 THEN 'no_engagement'
                WHEN lifetime_raw < 10 THEN '<10'
                WHEN lifetime_raw < 100 THEN '10-100'
                WHEN lifetime_raw < 500 THEN '100-500'
                WHEN lifetime_raw < 1000 THEN '500-1000'
                ELSE '1000+'
            END as lifetime_bucket,
            COUNT(*) as n
        FROM '{p}'
        WHERE total_reposts = 0
        GROUP BY lifetime_bucket
        ORDER BY MIN(lifetime_raw)
    """).show()

    print()
