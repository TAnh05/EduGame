# Memory diagnostic checklist

Record GPU model and total memory, PyTorch/Transformers versions, dtype, image size, number of strips, `max_num`, peak `torch.cuda.max_memory_allocated()` and `max_memory_reserved()`, plus latency. Reset peak statistics immediately before a controlled run. Test the exact OOM fallback only with a safe reproducible input and never loop retries indefinitely.
