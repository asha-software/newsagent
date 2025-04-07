# LangSmith Evaluation Design Document

## Overview

This document outlines the design and implementation of LLM evaluation using LangSmith within the NewsAgent fact-checking application. LangSmith provides tools for tracing, monitoring, and evaluating LLM-powered applications, which is critical for ensuring our fact-checking capabilities remain accurate and reliable.

## Objectives

1. Evaluate fact-checking accuracy against known-truth datasets
2. Monitor tool usage patterns and effectiveness
3. Analyze agent reasoning paths
4. Identify and address hallucination risks
5. Benchmark agent performance against baseline metrics

## Architecture

### Components

1. **Evaluation Runners**: Orchestrate evaluation pipelines
2. **Evaluators**: Custom functions that assess specific aspects of agent performance
3. **Datasets**: Curated collections of claims with known truth values
4. **Metrics Collection**: Systems to aggregate and visualize performance data
5. **Feedback Loop**: Process for incorporating evaluation results into agent improvements

### Integration Points

```
                                ┌───────────────┐
                                │   LangSmith   │
                                │   Platform    │
                                └───────┬───────┘
                                        │
                                        ▼
┌───────────────┐              ┌────────────────┐             ┌───────────────┐
│  Test Claims  │───────────▶  │ Research Agent │───────────▶ │  Evaluation   │
│   Dataset     │              │    Workflow    │             │   Metrics     │
└───────────────┘              └────────────────┘             └───────────────┘
                                        │
                                        ▼
                                ┌───────────────┐
                                │ Tool Execution│
                                │    Traces     │
                                └───────────────┘
```

## Evaluation Metrics

### 1. Accuracy Metrics

- **Factual Correctness**: Measures if the agent's conclusion matches ground truth
- **Evidence Quality**: Evaluates relevance and reliability of evidence collected
- **Source Diversity**: Assesses variety of information sources consulted

### 2. Process Metrics

- **Tool Selection Accuracy**: Measures if appropriate tools were selected for the claim type
- **Query Formulation**: Evaluates effectiveness of queries sent to tools
- **Evidence Integration**: Assesses how well evidence is synthesized into conclusions

### 3. Efficiency Metrics

- **Reasoning Steps**: Number of steps to reach conclusion
- **Tool Usage Efficiency**: Measures unnecessary or redundant tool calls
- **Response Time**: Time taken to complete fact-checking process

## Implementation

### Evaluation Dataset Structure

```python
EVALUATION_DATASETS = {
    "political_claims": {
        "claims": [
            {
                "id": "pol-001",
                "claim": "The President signed Bill X into law on June 1, 2023",
                "ground_truth": True,
                "difficulty": "easy",
                "expected_tools": ["query", "date_verification"]
            },
            # Additional claims...
        ],
        "metadata": {
            "description": "Political fact claims dataset",
            "version": "1.0",
            "date_created": "2023-07-15"
        }
    },
    "scientific_claims": {
        # Similar structure...
    }
}
```

### Custom Evaluators

```python
from langsmith.evaluation import EvaluationResult, RunEvaluator

class FactualCorrectnessEvaluator(RunEvaluator):
    """Evaluates if agent's conclusion matches ground truth."""

    def evaluate_run(self, run, example=None):
        ground_truth = example.get("ground_truth")
        conclusion = self._extract_conclusion(run)

        score = self._calculate_agreement_score(conclusion, ground_truth)

        return EvaluationResult(
            key="factual_correctness",
            score=score,
            comment=f"Ground truth: {ground_truth}, Conclusion: {conclusion}"
        )

    def _extract_conclusion(self, run):
        # Extract conclusion from run outputs
        # Implementation details...

    def _calculate_agreement_score(self, conclusion, ground_truth):
        # Calculate agreement score
        # Implementation details...
```

### Evaluation Workflow

```python
from langsmith import Client, evaluation as eval_module
import pandas as pd

def run_evaluation_pipeline(dataset_name, agent):
    """Run full evaluation pipeline on specified dataset."""
    # Initialize LangSmith client
    client = Client()

    # Load dataset
    dataset = client.read_dataset(dataset_name)

    # Create evaluation run
    evaluation_run = client.create_run_evaluation(
        dataset_name=dataset_name,
        evaluators=[
            FactualCorrectnessEvaluator(),
            ToolSelectionEvaluator(),
            EvidenceQualityEvaluator()
        ]
    )

    # Run agent on all examples in dataset
    results = []
    for example in dataset.examples:
        result = agent.invoke({"claim": example["claim"]})
        results.append(result)

    # Process results and store metrics
    metrics_df = pd.DataFrame([
        {
            "claim_id": example["id"],
            "factual_correctness": eval_result.evaluators["factual_correctness"].score,
            "tool_selection": eval_result.evaluators["tool_selection"].score,
            "evidence_quality": eval_result.evaluators["evidence_quality"].score
        }
        for example, eval_result in zip(dataset.examples, evaluation_run.results)
    ])

    return metrics_df
```

## LangSmith Configuration

### Project Setup

1. Create a dedicated LangSmith project for evaluation:

```python
from langsmith import Client

client = Client()
project = client.create_project(
    "newsagent-evaluation",
    description="Evaluation runs for NewsAgent fact-checking"
)
```

2. Configure environment for tracing:

```python
# In .env or equivalent configuration
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=<your-langsmith-api-key>
LANGCHAIN_PROJECT=newsagent-evaluation
```

### Automated Testing Integration

The evaluation system integrates with our pytest testing framework:

```python
import pytest
from langsmith.evaluation import evaluate_run_against_dataset

@pytest.mark.parametrize("dataset_name", ["political_claims", "scientific_claims"])
def test_agent_accuracy(dataset_name):
    """Test agent accuracy against benchmark datasets."""
    results = evaluate_run_against_dataset(
        dataset_name=dataset_name,
        llm_or_chain_factory=agent,
        input_key="claim",
        evaluators=[FactualCorrectnessEvaluator()]
    )

    # Assert minimum accuracy threshold
    accuracy = results["factual_correctness"].mean()
    assert accuracy >= 0.8, f"Accuracy below threshold: {accuracy}"
```

## Dashboard and Monitoring

LangSmith's built-in dashboard will be configured with:

1. **Custom leaderboards** for tracking agent performance across versions
2. **Evaluation trace views** showing detailed reasoning paths
3. **Failure analysis views** for identifying systematic error patterns
4. **Dataset management interface** for curating evaluation claims

## Future Enhancements

1. **Human feedback integration**: Incorporate human evaluator assessments
2. **Adversarial testing**: Create challenge datasets designed to trigger hallucinations
3. **Continuous evaluation**: Automate evaluation on PR/merge into main branch
4. **Regression testing**: Flag when performance decreases on established benchmarks
5. **Multi-agent evaluation**: Compare performance across different agent architectures

## Conclusion

This LangSmith evaluation design provides a comprehensive framework for assessing and improving the NewsAgent fact-checking system. By implementing structured evaluation processes, we can systematically identify strengths and weaknesses in our agent's reasoning, evidence collection, and fact verification capabilities.
