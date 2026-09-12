# ACE-Step bootstrap evidence

Status: `BOOTSTRAP_PASS`

Observed in the Owner local session on 2026-09-11 (Asia/Bangkok).

## Installed runtime

```text
checkout: /Users/jerson/AI/runtime/music/acestep-1.5
upstream: https://github.com/ACE-Step/ACE-Step-1.5.git
commit: ca1e85fe9430179831e6bc6be790c332190a3866
Python: CPython 3.12.14
uv: 0.12.5
ace-step: 1.5.0
MLX: 0.30.6
mlx-lm: 0.29.1
torch: 2.10.0
```

`uv sync` resolved 176 packages, prepared 125 packages and installed 125 packages into the isolated `.venv` under the ACE-Step runtime.

The bootstrap reported that no existing local-ai-platform service was restarted or modified.

## Interpretation

Dependency/bootstrap stage is complete. Model weights have not yet been proven by a successful full generation. The next useful gate is to prepare the approved reference file, then start the intended high-quality MLX model profile and complete one real generation.

Because the Owner does not currently require simultaneous execution with the older Qwen/model stack, a separate small smoke-model download is optional. Avoid downloading disposable model profiles solely for a smoke test when the intended quality profile can be tested directly.
