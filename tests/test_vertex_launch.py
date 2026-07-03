from agorasim.infra.vertex_launch import VertexJobSpec


def test_vertex_job_spec_sets_spot_and_redacts_env():
    spec = VertexJobSpec(
        project="p",
        region="us-central1",
        display_name="job",
        image_uri="us-docker.pkg.dev/p/r/i:tag",
        args=["scripts/model_cache.py"],
        env={"HF_TOKEN": "secret"},
    )
    body = spec.request_body()
    assert body["jobSpec"]["scheduling"]["strategy"] == "SPOT"
    assert body["jobSpec"]["workerPoolSpecs"][0]["containerSpec"]["env"][0]["value"] == "secret"
    redacted = spec.request_body(redact_env=True)
    assert redacted["jobSpec"]["workerPoolSpecs"][0]["containerSpec"]["env"][0]["value"] == "<redacted>"


def test_vertex_job_spec_uses_t4_worker_defaults():
    spec = VertexJobSpec(project="p", region="r", display_name="d", image_uri="i", args=[])
    pool = spec.request_body()["jobSpec"]["workerPoolSpecs"][0]
    assert pool["machineSpec"]["machineType"] == "n1-standard-8"
    assert pool["machineSpec"]["acceleratorType"] == "NVIDIA_TESLA_T4"
    assert pool["machineSpec"]["acceleratorCount"] == 1
    assert pool["diskSpec"]["bootDiskSizeGb"] >= 100
