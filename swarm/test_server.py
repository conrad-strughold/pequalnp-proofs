import unittest, tempfile, threading, json, time
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from concurrent.futures import ThreadPoolExecutor
import server
class Lifecycle(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        server.DB=str(Path(self.tmp.name)/"test.sqlite")
        server.ADMIN="admin-test"; server.INVITE="invite-test"; server.init()
        self.http=server.ThreadingHTTPServer(("127.0.0.1",0),server.Handler)
        self.thread=threading.Thread(target=self.http.serve_forever,daemon=True); self.thread.start()
        self.base="http://127.0.0.1:"+str(self.http.server_port)
    def tearDown(self):
        self.http.shutdown(); self.http.server_close(); self.thread.join(); self.tmp.cleanup()
    def call(self,path,data=None,token="",expected=200):
        req=Request(self.base+"/api/"+path,data=None if data is None else json.dumps(data).encode(),headers={"Content-Type":"application/json","Authorization":"Bearer "+token})
        try:
            with urlopen(req,timeout=5) as res: status=res.status; value=json.load(res)
        except HTTPError as err: status=err.code; value=json.load(err)
        self.assertEqual(status,expected,value); return value
    def agent(self,name):
        return self.call("register",{"name":name,"kind":"agent","invite":"invite-test"},expected=201)["token"]
    def project(self):
        return self.call("admin/project",dict(title="Test question",description="Test scope",criteria="Evidence"),server.ADMIN)["id"]
    def task(self,p,parent=None):
        return self.call("admin/task",dict(project=p,title="Task",description="Work",parent=parent),server.ADMIN)["id"]
    def test_full_lifecycle(self):
        p=self.project(); first=self.task(p); child=self.task(p,first); a=self.agent("A"); b=self.agent("B")
        lease=self.call("claim",{"project":p},a)["lease"]
        self.assertIsNone(self.call("claim",{"project":p},b)["task"])
        self.call("beat",{"lease":lease},b,410)
        self.call("beat",{"lease":lease},a)
        result=self.call("submit",dict(lease=lease,summary="Finding",evidence="Method"),a,201)["id"]
        self.call("admin/review",dict(result=result,verdict="rejected",review="Insufficient"),server.ADMIN)
        claim=self.call("claim",{"project":p},b); self.assertEqual(claim["task"]["id"],first)
        result=self.call("submit",dict(lease=claim["lease"],summary="Better",evidence="Reproduced"),b,201)["id"]
        self.call("admin/review",dict(result=result,verdict="accepted",review="Checked"),server.ADMIN)
        self.assertEqual(self.call("claim",{"project":p},a)["task"]["id"],child)
        state=self.call("state"); self.assertEqual(len(state["results"]),2)
        self.assertNotIn("token_hash",state["agents"][0]); self.assertNotIn("lease",state["tasks"][0])
    def test_auth_and_expiry(self):
        self.call("register",dict(name="X",kind="agent"),expected=403)
        self.call("admin/project",dict(title="X"),expected=401)
        p=self.project(); self.task(p); a=self.agent("A"); b=self.agent("B")
        lease=self.call("claim",{"project":p},a)["lease"]
        with server.connect() as c: c.execute("UPDATE tasks SET expires=?",(time.time()-1,))
        self.call("beat",{"lease":lease},a,410)
        claim=self.call("claim",{"project":p},b)
        self.call("release",dict(lease=claim["lease"],reason="Blocked"),b)
        self.assertIsNotNone(self.call("claim",{"project":p},a)["task"])
    def test_concurrent_claim(self):
        p=self.project(); self.task(p); tokens=[self.agent(str(i)) for i in range(6)]
        with ThreadPoolExecutor(max_workers=6) as pool:
            claims=list(pool.map(lambda token:self.call("claim",{"project":p},token),tokens))
        self.assertEqual(sum(c["task"] is not None for c in claims),1)
if __name__=="__main__": unittest.main()
