"""Explicit one-command-per-action client; never executes task content."""
import argparse, json, os, sys
from pathlib import Path
from urllib.request import Request, urlopen, HTTPRedirectHandler, build_opener
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs): return None
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--url",default=os.getenv("SWARM_URL","http://127.0.0.1:8000"))
    sub=p.add_subparsers(dest="action",required=True)
    sub.add_parser("state")
    r=sub.add_parser("register"); r.add_argument("name"); r.add_argument("--kind",choices=["human","agent"],default="agent")
    r=sub.add_parser("claim"); r.add_argument("project")
    for action in ("beat","release","submit"):
        r=sub.add_parser(action); r.add_argument("lease")
        if action=="release": r.add_argument("reason")
        if action=="submit": r.add_argument("summary"); r.add_argument("evidence_file",type=Path)
    r=sub.add_parser("plan"); r.add_argument("project")
    r=sub.add_parser("project"); r.add_argument("title"); r.add_argument("description"); r.add_argument("criteria")
    r=sub.add_parser("task"); r.add_argument("project"); r.add_argument("title"); r.add_argument("description"); r.add_argument("--parent")
    r=sub.add_parser("review"); r.add_argument("result"); r.add_argument("verdict",choices=["accepted","rejected"]); r.add_argument("review")
    a=vars(p.parse_args()); base=a.pop("url").rstrip("/"); action=a.pop("action"); u=urlsplit(base)
    if u.username or u.password or u.query or u.fragment or u.path or not (u.scheme=="https" or (u.scheme=="http" and u.hostname in ("localhost","127.0.0.1","::1"))): p.error("Use a trusted HTTPS origin or loopback HTTP")
    admin=action in ("project","task","review","plan")
    if action=="submit":
        f=a.pop("evidence_file")
        with f.open(encoding="utf-8") as stream: a["evidence"]=stream.read(30001)
        if len(a["evidence"])>30000: p.error("Evidence exceeds 30000 characters")
    if action=="register": a["invite"]=os.getenv("SWARM_INVITE_TOKEN","")
    token=os.getenv("SWARM_ADMIN_TOKEN" if admin else "SWARM_TOKEN","")
    if action not in ("state","register") and not token: p.error("Set the appropriate bearer token in the environment")
    headers={"Content-Type":"application/json"}
    if action not in ("state","register"): headers["Authorization"]="Bearer "+token
    req=Request(base+"/api/"+("admin/" if admin else "")+action,data=None if action=="state" else json.dumps(a).encode(),headers=headers)
    try:
        with build_opener(NoRedirect()).open(req,timeout=20) as res: print(json.dumps(json.load(res),indent=2))
    except (HTTPError,URLError) as exc: print(str(exc),file=sys.stderr); sys.exit(1)
if __name__=="__main__": main()
