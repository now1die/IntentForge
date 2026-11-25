# Demonstrate Phase 12

1. Start the backend and frontend using the [setup guide](phase11_5_codespaces_setup.md). Run `python -m scripts.doctor`.
2. Open **Phase 12 demo examples**. Load **Correct program**, then select **Analyze**. Try **Compiler diagnostic** to see source diagnostics.
3. Load **Sentinel collision and manual repair**. In **Intention**, select **Phase 12 semantic state** and **Supplied input/output examples**. Use entry function `demo` and the supplied JSON under **Demo expectations**.
4. Review the separate initialization, sentinel and presence facts. Open the proposed diff. The editor still shows the original comparison. Use **Apply Reviewed Intention Repair** only after reviewing it.
5. To see the confirmed mismatch, reload the faulty demo. With a private worker running, copy the interactive vectors, enable candidate comparison, and select Phase 12 in **Interactive behavioral verification**.
6. Load **Abstention without a contract** and choose Code only. Inspect the physical extent and unknown index instead of a candidate.

These are authored teaching examples. The upstream adaptations are documented in the benchmark dataset. With the worker unavailable, compiler and static evidence remain usable.
