import duckdb

for size in ["1M", "500K"]:
    c = f"output/{size}/out_cascades.parquet"
    print(f"=== {size} — raw cascade tree stats ===")
    duckdb.sql(f"""
        SELECT
            COUNT(*) as n_cascades,
            AVG(cascade_size)::FLOAT as avg_nodes,
            AVG(cascade_depth)::FLOAT as avg_depth,
            SUM(CASE WHEN cascade_depth >= 2 THEN 1 ELSE 0 END)::FLOAT / COUNT(*) * 100 as pct_d_ge2,
            SUM(CASE WHEN cascade_depth >= 3 THEN 1 ELSE 0 END)::FLOAT / COUNT(*) * 100 as pct_d_ge3,
            SUM(CASE WHEN cascade_depth >= 5 THEN 1 ELSE 0 END)::FLOAT / COUNT(*) * 100 as pct_d_ge5,
            SUM(CASE WHEN cascade_depth >= 10 THEN 1 ELSE 0 END)::FLOAT / COUNT(*) * 100 as pct_d_ge10,
            SUM(CASE WHEN cascade_depth = 1 THEN 1 ELSE 0 END)::FLOAT / COUNT(*) * 100 as pct_depth1,
            SUM(CASE WHEN max_out_degree >= 2 THEN 1 ELSE 0 END)::FLOAT / COUNT(*) * 100 as pct_branch,
            SUM(CASE WHEN max_out_degree >= 5 THEN 1 ELSE 0 END)::FLOAT / COUNT(*) * 100 as pct_branch5,
            SUM(CASE WHEN max_out_degree >= 10 THEN 1 ELSE 0 END)::FLOAT / COUNT(*) * 100 as pct_branch10,
            AVG(max_out_degree)::FLOAT as avg_max_children,
            MAX(max_out_degree) as max_children
        FROM '{c}'
    """).show()
    print()

print("=== Virality for non-trivial cascades (size >= 10) ===")
for size in ["1M", "500K"]:
    c = f"output/{size}/out_cascades.parquet"
    duckdb.sql(f"""
        SELECT '{size}' as network,
            COUNT(*) as n,
            AVG(struct_virality)::FLOAT as mean_v,
            MEDIAN(struct_virality) as med_v,
            AVG(cascade_size)::FLOAT as mean_size,
            AVG(cascade_depth)::FLOAT as mean_depth,
            AVG(max_out_degree)::FLOAT as mean_max_out
        FROM '{c}'
        WHERE cascade_size >= 10
    """).show()

print("\n=== Virality for cascades with actual branching (max_out >= 2) ===")
for size in ["1M", "500K"]:
    c = f"output/{size}/out_cascades.parquet"
    duckdb.sql(f"""
        SELECT '{size}' as network,
            COUNT(*) as n,
            AVG(struct_virality)::FLOAT as mean_v,
            AVG(cascade_size)::FLOAT as mean_size,
            AVG(cascade_depth)::FLOAT as mean_depth,
            AVG(max_out_degree)::FLOAT as mean_max_out
        FROM '{c}'
        WHERE max_out_degree >= 2
    """).show()

print("\n=== Top 10 most viral cascades ===")
for size in ["1M", "500K"]:
    c = f"output/{size}/out_cascades.parquet"
    print(f"\n--- {size} ---")
    duckdb.sql(f"""
        SELECT post_id, cascade_size, cascade_depth, struct_virality, max_out_degree, author_degree
        FROM '{c}'
        ORDER BY struct_virality DESC
        LIMIT 10
    """).show()
