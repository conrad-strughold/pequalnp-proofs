"""Versioned deterministic checkers for administrator-defined data tasks."""
import json,re
from decimal import Decimal,InvalidOperation
def number(x):
    if not isinstance(x,str) or len(x)>80 or not re.fullmatch(r"-?\d{1,30}(?:\.\d{1,30})?",x):
        raise ValueError("Expected bounded decimal string")
    return Decimal(x)
def config(kind, spec):
    if kind!="numeric-v1" or not isinstance(spec,dict) or set(spec)!={"values","operation","tolerance"}:
        raise ValueError("Unsupported verifier or invalid specification")
    if not isinstance(spec["values"],list) or not 1<=len(spec["values"])<=100:
        raise ValueError("Expected 1 to 100 values")
    vals=[number(x) for x in spec["values"]]
    if spec["operation"] not in ("sum","min","max","count"): raise ValueError("Unsupported operation")
    tol=number(spec["tolerance"])
    if tol<0: raise ValueError("Tolerance must be nonnegative")
    return vals,tol
def verify(kind,spec,evidence):
    from decimal import localcontext
    vals,tol=config(kind,spec)
    with localcontext() as ctx:
        ctx.prec=80
        expected={"sum":lambda:sum(vals),"min":lambda:min(vals),"max":lambda:max(vals),"count":lambda:Decimal(len(vals))}[spec["operation"]]()
        try:
            answer=json.loads(evidence)
            if not isinstance(answer,dict) or set(answer)!={"answer"}: raise ValueError("Expected answer object")
            actual=number(answer["answer"])
            passed=abs(actual-expected)<=tol
            return {"pass":passed,"expected":str(expected),"actual":str(actual),"scope":"Arithmetic on operator-provided values only"}
        except (ValueError,TypeError,InvalidOperation):
            return {"pass":False,"scope":"Invalid answer format"}
