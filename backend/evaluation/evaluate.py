from app.graph.workflow import run_workflow
CASES=[
 ("P-1001","LOW"),("P-1002","LOW"),("P-1003","HIGH")
]

def main():
    results=[]
    for pid,expected in CASES:
        r=run_workflow("eval","eval",f"Classify promotion {pid}")
        actual=r["classification"]["risk_band"] if r.get("classification") else "NONE"
        results.append((pid,expected,actual,expected==actual))
    print("promotion_id expected actual correct")
    for row in results: print(*row)
    print(f"accuracy={sum(x[3] for x in results)/len(results):.2%}")
if __name__=="__main__": main()
