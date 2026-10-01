class MetricService:

    def __init__(self):
        self.total_llm_calls = 0      # Total LLM call attempts
        self.llm_errors = 0               # Total failed LLM attempts
        self.concurrent_llm_calls = 0   # Currently running LLM calls
        self.max_concurrent_llm_calls = 0 # Highest concurrency observed

    def call_started(self):
        self.total_llm_calls += 1
        self.concurrent_llm_calls += 1

# Observe the highest concurrency reached
        self.max_concurrent_llm_calls = max(
            self.max_concurrent_llm_calls,
            self.concurrent_llm_calls
        )

    def call_finished(self):
 # One LLM call has finished
        self.concurrent_llm_calls -= 1

    def record_error(self):
 # Record a failed LLM attempt
        self.llm_errors += 1

    def get_metrics(self):
        return {
        "llm_calls_total": self.total_llm_calls,
        "llm_errors_total": self.llm_errors,
        "max_concurrent_llm_calls": self.max_concurrent_llm_calls
    }


# Create one shared metrics object for the whole application
metrics = MetricService()