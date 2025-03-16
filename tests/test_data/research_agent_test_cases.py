"""Test cases for research agent tool usage tests"""

DETAIL_MESSAGE = "\nExpected {expected_tools} to be used, but agent used {tools_used}."

"""
NOTE: Currently setting `expected_tools` to list so that later if we want to test for
tool call sequence, we can.
"""
TOOL_USAGE_TEST_CASES = [
    {
        "claim": "12 multiplied by 10 equals 120",
        "expected_tools": ["multiply"],
        "description": "Calculator tool should be used for mathematical claims." + DETAIL_MESSAGE
    },
    {
        "claim": "Albert Einstein developed the theory of relativity",
        "expected_tools": ["query"],
        "description": "Wikipedia tool should be used for historical claims." + DETAIL_MESSAGE
    },
    {
        "claim": "The capital of France is Berlin",
        "expected_tools": ["query"],
        "description": "Wikipedia tool should be used for geographical claims." + DETAIL_MESSAGE
    },
    # Add more test cases here
]
