
import re

def test_matching():
    ignore_words = {"the", "a", "an", "is", "are", "was", "were", "to", "for", "in", "on", "at", "by", "with", "from", "blocked", "resolved", "fixed", "no", "longer", "issue"}
    
    # Blocker reason in DB
    blocker_reason = "Waiting for Akshita to start her work."
    # Resolution text from AI
    res_text = "Akshita has started her work."
    
    res_words = set(re.findall(r'\w+', res_text.lower())) - ignore_words
    eb_words = set(re.findall(r'\w+', blocker_reason.lower())) - ignore_words
    
    print(f"Resolution Words: {res_words}")
    print(f"Blocker Words: {eb_words}")
    
    intersection = eb_words.intersection(res_words)
    print(f"Intersection: {intersection}")
    
    if intersection:
        print("✅ MATCH FOUND")
    else:
        print("❌ NO MATCH")

if __name__ == "__main__":
    test_matching()
