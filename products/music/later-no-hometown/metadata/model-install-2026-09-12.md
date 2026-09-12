# ACE-Step quality model installation evidence

Date: 2026-09-12
Host: Apple Silicon MacBook Pro, 48 GiB unified memory
Runtime: `/Users/jerson/AI/runtime/music/acestep-1.5`
Pinned upstream commit: `ca1e85fe9430179831e6bc6be790c332190a3866`
Backend: MLX
Service bind: `127.0.0.1:8215`

## Result

Quality profile initialization reached a successful running state:

```text
MLX model loaded successfully
5Hz LM initialized successfully
Service initialization completed successfully
Running on local URL: http://127.0.0.1:8215
```

## Installed checkpoint inventory

Observed checkpoint root after cleanup:

```text
36G  /Users/jerson/AI/runtime/music/acestep-1.5/checkpoints
```

Observed component sizes:

```text
337M  vae
1.1G  Qwen3-Embedding-0.6B
3.5G  acestep-5Hz-lm-1.7B
4.5G  acestep-v15-turbo
7.9G  acestep-5Hz-lm-4B
19G   acestep-v15-xl-sft
```

A direct safetensors audit before the final 4B completion verified the following components as readable and complete:

```text
Qwen3-Embedding-0.6B
acestep-5Hz-lm-1.7B
acestep-v15-turbo
acestep-v15-xl-sft
vae
```

The XL SFT model had all four expected shards present and readable, totaling about 18.58 GiB. The final launch log subsequently showed the 4B LM loading successfully through MLX, confirming that the preferred quality profile was available to the service.

## Cleanup evidence

Old Hugging Face `.incomplete` files from an interrupted earlier download were identified as closed and redundant after their corresponding final model files had validated successfully. They were deleted. Empty ModelScope temporary directories under `acestep-v15-xl-sft` and `acestep-5Hz-lm-4B` were also removed.

The remaining checkpoint root was approximately 36G and consisted of the intended model/component directories plus tiny configuration files. A top-level hidden `._____temp` directory may still exist and should only be removed after confirming it is empty or contains no open files.

## Next gate

Run one real short Chinese music generation through the quality profile and verify:

1. generation completes without runtime errors;
2. output audio is playable;
3. output can be saved as WAV;
4. MLX stays active and the service remains responsive;
5. no unexpected temporary duplication is left after generation.

Only after this generation gate passes should the workflow proceed to full-song reference reproduction and later Codex automation.
