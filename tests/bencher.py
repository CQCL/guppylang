import sys
import json


def create_bencher_BMF(pytest_benchmark_file: str, bencher_file: str) -> None:
    """Creates a BMF json file by parsing the results from a pytest-benchmark run,
    including custom metrics."""

    with open(pytest_benchmark_file) as results_file:
        results_json = json.load(results_file)

    BMF = {}
    for benchmark in results_json["benchmarks"]:
        name = benchmark["fullname"]
        BMF[name] = {}

        extra_info = benchmark["extra_info"]
        bytes_info = None
        nodes_info = None

        if extra_info:
            if extra_info.get("bytes"):
                bytes_info = extra_info["bytes"]
                BMF[name]["hugr_bytes"] = {"value": bytes_info}
            if extra_info.get("nodes"):
                nodes_info = extra_info["nodes"]
                BMF[name]["hugr_nodes"] = {"value": nodes_info}

    with open(bencher_file, "w") as bmf_file:
        json.dump(BMF, bmf_file)


if __name__ == "__main__":
    create_bencher_BMF(sys.argv[1], sys.argv[2])
