from ai.intention_context import Example
from ai.intention_engine import analyze_intention

PREFIX = """int f(int n,int x,int y){int a[2];a[0]=x;a[1]=y;int result=a[0];
 for(int i=1;i<n;i++){result+=a[i];}return result;}"""
COUNT = """int f(int x,int y){int a[2];a[0]=x;a[1]=y;int changes=0;
 for(int i=0;i<2;i++){a[i]+=1;changes++;}return changes;}"""


def categories(source, examples, **profile):
    result = analyze_intention(source, phase6_entry="f",
                               phase6_examples=tuple(Example(tuple(args), value) for args, value in examples),
                               **profile)
    return {item.proposal.category for item in result.candidates}


def test_empty_guard_needs_disagreement_and_supplied_empty_result():
    examples = [([0, 9, 4], -8), ([1, 2, 8], 2), ([2, 3, 4], 7)]
    assert "EMPTY_ENTRY_RESULT" in categories(PREFIX, examples, phase13=True)
    assert "EMPTY_ENTRY_RESULT" not in categories(PREFIX, examples, phase12=True)
    assert "EMPTY_ENTRY_RESULT" not in categories(PREFIX, examples[1:], phase13=True)


def test_endpoint_projection_requires_distinguishing_output():
    examples = [([3, 9], 10), ([-3, -1], 0), ([1, 1], 2)]
    assert "AGGREGATE_RESULT_PROJECTION" in categories(COUNT, examples, phase13=True)
    assert "AGGREGATE_RESULT_PROJECTION" not in categories(COUNT, [(x, 2) for x, _ in examples], phase13=True)
