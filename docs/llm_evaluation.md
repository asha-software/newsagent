# Design Documentation: LangSmith Evaluation System

The LangSmith evaluation system is designed to assess the performance of various AI agents (e.g., Claim Decomposer, Reasoning Agent, Verdict Agent) in the Newsagent project. It uses LangSmith's evaluation framework to compare agent outputs against reference outputs and evaluate their coherence, accuracy, and logical consistency.

---

## Overview

The evaluation system is implemented as a set of Python scripts located in the `tests/langsmith` directory. These scripts:
1. Load datasets of test cases (claims, evidence, expected outputs).
2. Invoke the corresponding AI agent for each test case.
3. Compare the agent's outputs with reference outputs using custom evaluators.
4. Log the results to LangSmith for tracking and analysis.

---

## Directory Structure
```sh
tests/langsmith/ ├── prompts/ # Prompt templates for LLM-based evaluations │ ├── reasoning_coherence_prompt.txt │ └── verdict_coherence_prompt.txt ├── test_data/ # Test datasets for agents │ ├── research_agent_web_search_usage.json │ ├── reasoning_agent_statements.json │ └── verdict_agent_evaluation.json ├── setup_langsmith_dataset.py # Script to create LangSmith datasets ├── ls_claim_decomposer.py # Evaluation script for Claim Decomposer ├── ls_reasoning_agent.py # Evaluation script for Reasoning Agent └── ls_verdict_agent.py # Evaluation script for Verdict Agent
```