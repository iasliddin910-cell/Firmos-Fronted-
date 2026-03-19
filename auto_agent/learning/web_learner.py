"""Learning Engine"""
class WebLearner:
    def search_and_learn(self, query):
        return {"learned": query}

class SourceRanker:
    def rank(self, sources):
        return [{"source": s, "score": 0.8} for s in sources]

web_learnner = WebLearner()
