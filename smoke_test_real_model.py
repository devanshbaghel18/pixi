#!/usr/bin/env python3
"""
smoke_test_real_model.py — Real Hardware Benchmark and Smoke Test Suite

Runs live open-domain inference against the local Ollama engine on the
NVIDIA GeForce RTX 4050 Laptop GPU (with CUDA acceleration).

Measures and reports:
  - Model loading latency
  - Time to first token (TTFT)
  - Total generation time
  - Tokens per second (TPS)
  - GPU VRAM consumption (via nvidia-smi)
  - Multi-turn context understanding & persistent SQLite memory
"""

import os
import sys
import time
import json
import subprocess
import urllib.request
import urllib.error

# Ensure workspace root is in path
_root = os.path.dirname(os.path.abspath(__file__))
if _root not in sys.path:
    sys.path.insert(0, _root)

from companion_db import init_db, clear_db, get_memory_facts, get_conversation_context
from dialogue_engine import DialogueEngine
from local_llm import LocalLLM, DEFAULT_MODEL_NAME, DEFAULT_OLLAMA_HOST


def get_gpu_vram():
    """Queries current GPU VRAM utilization via nvidia-smi."""
    try:
        cmd = ["nvidia-smi", "--query-gpu=name,memory.used,memory.total,utilization.gpu", "--format=csv,noheader,nounits"]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=3)
        if res.returncode == 0 and res.stdout.strip():
            parts = [p.strip() for p in res.stdout.strip().split(",")]
            if len(parts) >= 4:
                return {
                    "name": parts[0],
                    "used_mb": float(parts[1]),
                    "total_mb": float(parts[2]),
                    "util_pct": float(parts[3]),
                }
    except Exception:
        pass
    return {"name": "Unknown", "used_mb": 0.0, "total_mb": 0.0, "util_pct": 0.0}


def run_smoke_test():
    print("=" * 70)
    print("  PRINCESS MIA — OPEN-DOMAIN GENERATIVE ENGINE SMOKE TEST")
    print("=" * 70)

    # 1. Hardware baseline
    gpu = get_gpu_vram()
    print(f"\n[Hardware Baseline]")
    print(f"  GPU: {gpu['name']}")
    print(f"  VRAM: {gpu['used_mb']:.1f} MB used / {gpu['total_mb']:.1f} MB total ({gpu['util_pct']}% util)")

    # 2. Check Ollama server
    host = os.getenv("OLLAMA_HOST", DEFAULT_OLLAMA_HOST)
    print(f"\n[Ollama Runtime Probing]")
    print(f"  Endpoint: {host}")
    try:
        with urllib.request.urlopen(f"{host}/api/tags", timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            models = [m.get("name", "") for m in data.get("models", [])]
            print(f"  Server: ONLINE (Available models: {models})")
    except Exception as e:
        print(f"  Server Error: Could not connect to {host} ({e})")
        print("  Please ensure 'ollama serve' is running.")
        return False

    # Choose model
    target_model = os.getenv("OLLAMA_MODEL", DEFAULT_MODEL_NAME)
    if models and not any(target_model in m for m in models):
        # Fall back to first available installed model
        target_model = models[0]
    print(f"  Target Model: {target_model}")

    # 3. Initialize real LocalLLM
    temp_db = "test_smoke_companion.db"
    if os.path.exists(temp_db):
        os.remove(temp_db)
    init_db(temp_db)

    llm = LocalLLM(model_name=target_model, host=host, mock_mode=False)
    load_start = time.time()
    ready = llm.load_model()
    load_duration = time.time() - load_start
    print(f"  Model Load Probe: {'SUCCESS' if ready else 'FAILED'} in {load_duration:.3f}s")
    if not ready:
        print(f"  Notice: Model {target_model} is still downloading or unavailable.")
        return False

    # 4. Interactive Live Conversation Benchmark
    test_queries = [
        "Hi Mia! I am currently studying computer science and learning Go.",
        "Can you explain what quantum entanglement is in simple terms?",
        "What was I studying again?",
        "Have you heard of sonder?",
        "What is the difference between TCP and UDP?",
    ]

    engine = DialogueEngine(db_path=temp_db, use_llm=True, llm=llm)

    print("\n[Executing Live Generative Conversations & Benchmarks]")
    benchmarks = []

    for i, q in enumerate(test_queries, 1):
        print(f"\n--- Turn {i} ---")
        print(f"User: {q}")
        
        # Measure TTFT and generation
        t0 = time.time()
        first_token_time = None
        tokens = []

        try:
            gen = llm.generate_reply_stream(q, db_path=temp_db)
            for tok in gen:
                if first_token_time is None:
                    first_token_time = time.time() - t0
                tokens.append(tok)
            total_duration = time.time() - t0
            reply = "".join(tokens).strip()
        except Exception as e:
            # Fallback to sync call
            t0 = time.time()
            reply = llm.generate_reply(q, db_path=temp_db)
            total_duration = time.time() - t0
            first_token_time = total_duration

        token_count = max(1, len(reply.split()))
        tps = token_count / total_duration if total_duration > 0 else 0.0

        # Log interaction in DB
        engine.process_message(q, persist=True)

        # GPU metrics after turn
        turn_gpu = get_gpu_vram()

        print(f"Mia: {reply}")
        print(f"  [Metrics] Total: {total_duration:.2f}s | TTFT: {first_token_time*1000:.1f}ms | TPS: ~{tps:.1f} words/s | VRAM: {turn_gpu['used_mb']:.1f} MB")

        benchmarks.append({
            "turn": i,
            "query": q,
            "total_sec": total_duration,
            "ttft_ms": (first_token_time or 0.0) * 1000,
            "tps": tps,
            "vram_mb": turn_gpu["used_mb"],
        })

    # 5. Verify conversation history and facts
    facts = get_memory_facts(db_path=temp_db)
    history = get_conversation_context(limit=10, db_path=temp_db)
    print(f"\n[Persistence Verification]")
    print(f"  Saved Facts Count: {len(facts)}")
    for f in facts:
        print(f"    - {f['key']}: {f['value']}")
    print(f"  Stored Multi-Turn Context Messages: {len(history)}")

    # 6. Overall Performance Summary
    avg_total = sum(b["total_sec"] for b in benchmarks) / len(benchmarks)
    avg_ttft = sum(b["ttft_ms"] for b in benchmarks) / len(benchmarks)
    avg_tps = sum(b["tps"] for b in benchmarks) / len(benchmarks)
    max_vram = max(b["vram_mb"] for b in benchmarks)

    print("\n" + "=" * 70)
    print("  HARDWARE BENCHMARK SUMMARY")
    print("=" * 70)
    print(f"  Model:                {target_model}")
    print(f"  GPU Hardware:         {gpu['name']}")
    print(f"  Peak VRAM Usage:      {max_vram:.1f} MB / {gpu['total_mb']:.1f} MB")
    print(f"  Average Latency:      {avg_total:.2f} s")
    print(f"  Avg Time To First Tok:{avg_ttft:.1f} ms")
    print(f"  Avg Generation Speed: ~{avg_tps:.1f} words/s")
    print("=" * 70)

    # Cleanup temp db
    if os.path.exists(temp_db):
        os.remove(temp_db)

    return True


if __name__ == "__main__":
    success = run_smoke_test()
    sys.exit(0 if success else 1)
