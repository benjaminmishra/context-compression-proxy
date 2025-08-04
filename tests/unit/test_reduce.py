from proxy.qr_retriever import reduce, MAX_TOKENS


def test_reduce_truncates_context():
    query = "Hi"
    context = "one " * (MAX_TOKENS + 10)
    reduced = reduce(query, context)
    assert len(reduced.split()) == MAX_TOKENS
