"""Deterministic planning and structural validation. No scientific truth claims."""
def propose_tasks(project, existing):
    titles={t["title"]:t for t in existing}
    stages=[
        ("Define scope and measurable outcomes","Specify assumptions, success metrics and exclusions.",None),
        ("Map existing evidence","Survey primary sources, competing explanations and gaps.",None),
        ("Design reproducible investigation","Specify methods, baseline, controls, inputs and falsification criteria.","Define scope and measurable outcomes"),
        ("Test the proposed method","Conduct an authorized, safe investigation or analyze public data; record inputs and observations.","Design reproducible investigation"),
        ("Independent replication","Reproduce or challenge the preceding finding with independent evidence.","Test the proposed method"),
        ("Synthesize verified findings","Summarize supported claims, uncertainty and unresolved questions.","Independent replication"),
    ]
    proposals=[]
    for title,description,parent in stages:
        if title in titles: continue
        if parent and (parent not in titles or titles[parent]["status"]!="complete"): continue
        proposals.append({"title":title,"description":description+"\nProject scope: "+project["description"][:2000]+"\nAcceptance criteria: "+project["criteria"][:2000],"parent":titles[parent]["id"] if parent else None})
    return proposals
def check_evidence(summary,evidence):
    issues=[]
    if not isinstance(summary,str) or len(summary.strip())<5: issues.append("Summary too short")
    if not isinstance(evidence,str) or len(evidence.strip())<6: issues.append("Evidence too short")
    return {"pass":not issues,"issues":issues,"scope":"structural only; independent human review required"}
