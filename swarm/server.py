"""OpenSwarm Research: single-node reference server, Python 3.11+."""
import os, json, sqlite3, secrets, hashlib, time, hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from contextlib import closing

ROOT=Path(__file__).parent
DB=os.environ.get("SWARM_DB",str(ROOT/"swarm.sqlite"))
ADMIN=os.environ.get("SWARM_ADMIN_TOKEN","")
TTL=900
def connect():
    c=sqlite3.connect(DB,timeout=10)
    c.row_factory=sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    return c
def init():
    with closing(connect()) as c, c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY,title TEXT NOT NULL,description TEXT NOT NULL,criteria TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY,project TEXT REFERENCES projects(id),title TEXT NOT NULL,description TEXT NOT NULL,parent TEXT REFERENCES tasks(id),status TEXT NOT NULL DEFAULT 'open',agent TEXT,lease TEXT,expires REAL);
        CREATE TABLE IF NOT EXISTS agents(id TEXT PRIMARY KEY,name TEXT NOT NULL,kind TEXT NOT NULL,token_hash TEXT NOT NULL,seen REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS results(id TEXT PRIMARY KEY,task TEXT REFERENCES tasks(id),agent TEXT REFERENCES agents(id),summary TEXT NOT NULL,evidence TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'pending',review TEXT,created REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,kind TEXT NOT NULL,detail TEXT NOT NULL,created REAL NOT NULL);
        """)
def uid(): return secrets.token_hex(12)
def digest(s): return hashlib.sha256(s.encode()).hexdigest()
def event(c,k,d): c.execute("INSERT INTO events(kind,detail,created) VALUES(?,?,?)",(k,d,time.time()))
def rows(c,q,args=()): return [dict(r) for r in c.execute(q,args)]
def required(d,k,maxlen=8000):
    v=d.get(k)
    if not isinstance(v,str) or not v.strip() or len(v)>maxlen: raise ValueError("Invalid "+k)
    return v.strip()
def expire(c):
    c.execute("UPDATE tasks SET status='open',agent=NULL,lease=NULL,expires=NULL WHERE status='leased' AND expires<=?",(time.time(),))
class Handler(BaseHTTPRequestHandler):
    def send_json(self,d,status=200):
        b=json.dumps(d).encode(); self.send_response(status); self.send_header("Content-Type","application/json"); self.send_header("Cache-Control","no-store"); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        p=urlsplit(self.path).path
        if p in ("/","/join.txt"):
            f=ROOT/("index.html" if p=="/" else "join.txt")
            b=f.read_bytes(); self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8" if p=="/" else "text/plain; charset=utf-8"); self.send_header("X-Content-Type-Options","nosniff"); self.end_headers(); self.wfile.write(b); return
        if p!="/api/state": return self.send_json({"error":"not found"},404)
        with closing(connect()) as c,c:
            expire(c)
            self.send_json(dict(projects=rows(c,"SELECT * FROM projects"),tasks=rows(c,"SELECT id,project,title,description,parent,status,agent,expires FROM tasks"),agents=rows(c,"SELECT id,name,kind,seen FROM agents"),results=rows(c,"SELECT * FROM results ORDER BY created DESC"),events=rows(c,"SELECT * FROM events ORDER BY id DESC LIMIT 100")))
    def do_POST(self):
        try:
            n=int(self.headers.get("Content-Length","0"))
            if not 0<n<=65536: raise ValueError("Invalid body length")
            d=json.loads(self.rfile.read(n))
            if not isinstance(d,dict): raise ValueError("Object required")
            p=urlsplit(self.path).path
            token=self.headers.get("Authorization","").removeprefix("Bearer ")
            with closing(connect()) as c,c:
                c.execute("BEGIN IMMEDIATE"); expire(c)
                if p=="/api/register":
                    name=required(d,"name",80); kind=required(d,"kind",20)
                    if kind not in ("human","agent"): raise ValueError("Invalid kind")
                    a,t=uid(),secrets.token_urlsafe(32)
                    c.execute("INSERT INTO agents VALUES(?,?,?,?,?)",(a,name,kind,digest(t),time.time())); event(c,"join",name)
                    out={"id":a,"token":t}
                elif p.startswith("/api/admin/"):
                    if not ADMIN or not hmac.compare_digest(token,ADMIN): return self.send_json({"error":"unauthorized"},401)
                    if p.endswith("/project"):
                        i=uid(); c.execute("INSERT INTO projects VALUES(?,?,?,?)",(i,required(d,"title",120),required(d,"description"),required(d,"criteria"))); out={"id":i}; event(c,"project",i)
                    elif p.endswith("/task"):
                        i=uid(); project=required(d,"project",40); parent=d.get("parent")
                        if parent and not c.execute("SELECT 1 FROM tasks WHERE id=? AND project=?",(parent,project)).fetchone(): raise ValueError("Invalid parent")
                        c.execute("INSERT INTO tasks(id,project,title,description,parent) VALUES(?,?,?,?,?)",(i,project,required(d,"title",120),required(d,"description"),parent)); out={"id":i}; event(c,"task",i)
                    elif p.endswith("/review"):
                        i=required(d,"result",40); verdict=d.get("verdict"); review=required(d,"review")
                        if verdict not in ("accepted","rejected"): raise ValueError("Invalid verdict")
                        r=c.execute("SELECT * FROM results WHERE id=? AND status='pending'",(i,)).fetchone()
                        if not r: raise ValueError("No pending result")
                        c.execute("UPDATE results SET status=?,review=? WHERE id=?",(verdict,review,i))
                        c.execute("UPDATE tasks SET status=?,agent=NULL,lease=NULL,expires=NULL WHERE id=?",("complete" if verdict=="accepted" else "open",r["task"])); event(c,verdict,i); out={"status":verdict}
                    else: return self.send_json({"error":"not found"},404)
                else:
                    a=c.execute("SELECT id FROM agents WHERE token_hash=?",(digest(token),)).fetchone()
                    if not a: return self.send_json({"error":"unauthorized"},401)
                    a=a["id"]; c.execute("UPDATE agents SET seen=? WHERE id=?",(time.time(),a))
                    if p=="/api/claim":
                        if c.execute("SELECT 1 FROM tasks WHERE agent=? AND status='leased'",(a,)).fetchone(): raise ValueError("Already holding a lease")
                        project=required(d,"project",40)
                        task=c.execute("SELECT t.* FROM tasks t LEFT JOIN tasks parent ON t.parent=parent.id WHERE t.project=? AND t.status='open' AND (t.parent IS NULL OR parent.status='complete') ORDER BY t.rowid LIMIT 1",(project,)).fetchone()
                        if not task: out={"task":None}
                        else:
                            lease=uid(); expires=time.time()+TTL
                            c.execute("UPDATE tasks SET status='leased',agent=?,lease=?,expires=? WHERE id=?",(a,lease,expires,task["id"]))
                            out={"task":dict(task),"lease":lease,"expires":expires}; event(c,"claim",task["id"])
                    elif p in ("/api/beat","/api/release","/api/submit"):
                        lease=required(d,"lease",40)
                        t=c.execute("SELECT * FROM tasks WHERE lease=? AND agent=? AND status='leased'",(lease,a)).fetchone()
                        if not t: return self.send_json({"error":"lease expired or invalid"},410)
                        if p.endswith("/beat"):
                            expiry=time.time()+TTL; c.execute("UPDATE tasks SET expires=? WHERE id=?",(expiry,t["id"])); out={"expires":expiry}
                        elif p.endswith("/release"):
                            reason=required(d,"reason",1000); c.execute("UPDATE tasks SET status='open',agent=NULL,lease=NULL,expires=NULL WHERE id=?",(t["id"],)); event(c,"release",t["id"]+": "+reason); out={"status":"open"}
                        else:
                            i=uid(); c.execute("INSERT INTO results(id,task,agent,summary,evidence,created) VALUES(?,?,?,?,?,?)",(i,t["id"],a,required(d,"summary"),required(d,"evidence",30000),time.time())); c.execute("UPDATE tasks SET status='review',lease=NULL,expires=NULL WHERE id=?",(t["id"],)); event(c,"submit",i); out={"id":i,"status":"pending"}
                    else: return self.send_json({"error":"not found"},404)
            self.send_json(out,201 if p in ("/api/register","/api/submit") else 200)
        except (ValueError,TypeError,sqlite3.IntegrityError) as e: self.send_json({"error":str(e)},400)
if __name__=="__main__":
    init()
    ThreadingHTTPServer((os.environ.get("SWARM_HOST","127.0.0.1"),int(os.environ.get("PORT","8000"))),Handler).serve_forever()
