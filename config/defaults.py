DEFAULTS = {
    "data": {
        "historical_path": "data/historical.csv",
        "upcoming_path": "",
        "latest_path": "data/latest_draw.csv",
        "stats_dir": "data/stats/",
        "results_dir": "data/results/",
        "merge_upcoming": True,
        "archive_upcoming": True,
        "has_header": False,
        "date_format": "%m/%d/%y"
    },
    "strategy": {
        "number_pool": 55,
        "numbers_to_select": 6,
        "frequency_weight": 0.4,
        "recent_weight": 0.2,
        "random_weight": 0.4,
        "low_number_max": 10,
        "low_number_chance": 0.7,
        "high_prime_min": 35,
        "high_prime_chance": 0.25,
        "cold_threshold": 50,
        "resurgence_threshold": 3,
        "gap_threshold": 1.5
    },
    "validation": {
        "mode": "none",
        "test_draws": 120,
        "alert_threshold": 4,
        "save_report": True
    },
    "analysis": {
        "default_match_threshold": 4,
        "default_show_top": 5,
        "min_display_matches": 1,
        "recency_units": "draws",
        "recency_bins": {
            "hot": 3,
            "warm": 10,
            "cold": 30
        },
        "show_combined_stats": True,
        "top_range": 10,
        "combination_analysis": {
            "pairs": True,
            "triplets": True,
            "quadruplets": False,
            "quintuplets": False,
            "sixtuplets": False
        },
        "min_combination_count": 2,
        "gap_analysis": {
            "enabled": True,
            "threshold": 5
        },
        "odd_even": {
            "min_odds": 2,
            "max_odds": 4
        },
        "sum_range": {
            "min": 100,
            "max": 200
        }
    },
    "output": {
        "sets_to_generate": 4,
        "save_analysis": True,
        "verbose": True
    }
}